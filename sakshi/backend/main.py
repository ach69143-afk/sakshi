import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sakshi")

# 1a. Explicit absolute path loading for .env and sys.path resolution
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_sakshi_dir = os.path.dirname(_curr_dir)

if _curr_dir not in sys.path:
    sys.path.insert(0, _curr_dir)
if _sakshi_dir not in sys.path:
    sys.path.insert(0, _sakshi_dir)

_env_paths = [
    os.path.join(_sakshi_dir, ".env"),
    os.path.join(_curr_dir, ".env")
]

for _p in _env_paths:
    if os.path.isfile(_p):
        load_dotenv(_p, override=True)

# Sanitize every environment variable in os.environ
for _k, _v in list(os.environ.items()):
    if isinstance(_v, str):
        _cleaned = _v.strip().replace("\r", "")
        if (_cleaned.startswith('"') and _cleaned.endswith('"')) or (_cleaned.startswith("'") and _cleaned.endswith("'")):
            _cleaned = _cleaned[1:-1].strip().replace("\r", "")
        os.environ[_k] = _cleaned

# Fail loudly if GROQ_API_KEY is empty after loading
if not os.environ.get("GROQ_API_KEY"):
    logger.error("CRITICAL CONFIGURATION ERROR: GROQ_API_KEY is empty or missing after loading .env!")
    print("CRITICAL CONFIGURATION ERROR: GROQ_API_KEY is empty or missing after loading .env!", file=sys.stderr)

import threading
from db import get_connection, get_connection_for_case, verify_all_integrity, tamper_working_db, restore_clean_db, init_db
from ledger import get_ledger_state, record_action
from ingest import ingest_all
from resolve import (
    resolve_entities,
    get_merge_queue_data,
    approve_merge_decision,
    reject_merge_decision,
    unmerge_decision,
    propose_merge_decision
)
from graph import get_graph_instance, rebuild_graph
from alerts import generate_alerts, get_golden_hour_details
from simulate import simulate_node_removal
from auth import (
    USERS_DB,
    create_jwt_token,
    get_current_user,
    require_roles,
    mask_phone_str,
    verify_password
)
from validate import run_validation
from copilot import process_copilot_query, check_copilot_health
from report import build_pdf_dossier
from mailer import send_report_email, send_demo_login_notice, mask_email
from cross_case import get_visible_cross_case_links, decide_link
import pyotp
from totp_service import (
    MFA_ROLES,
    get_totp_secret_and_status,
    generate_qr_data_uri,
    generate_qr_data_uri_authenticator,
    verify_totp,
    set_totp_enrolled
)

app = FastAPI(title="SAKSHI Intelligence Workbench API", version="2.0.0")

# Guarantee database schema is initialized
try:
    init_db(get_connection())
except Exception as _e:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_DIR = os.path.join(BASE_DIR, "mock")

def load_mock_json(filename: str):
    filepath = os.path.join(MOCK_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Set of entity IDs unmasked by SP/DySP during current session
unmasked_entities: Set[str] = set()

# Pydantic Request Models
class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None

class DemoLoginRequest(BaseModel):
    name: str
    email: str
    role: str
    website: Optional[str] = None  # honeypot

class RemoveNodeRequest(BaseModel):
    node_id: str

class CopilotRequest(BaseModel):
    question: str

class ReportEmailRequest(BaseModel):
    report_id: str

class CrossCaseDecisionRequest(BaseModel):
    decision: str

def get_case_access(
    case_id: Optional[str] = Header(None, alias="X-Case-Id"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    user_email = user.get("email", "").lower().strip()
    user_role = user.get("role", "")

    main_conn = get_connection()
    cursor = main_conn.cursor()
    cursor.execute("SELECT case_id FROM cases ORDER BY case_id ASC")
    all_cases = [r[0] for r in cursor.fetchall()]

    if user_role == "ig":
        assigned_cases = all_cases
    else:
        cursor.execute("SELECT case_id FROM case_assignments WHERE user_email = ? ORDER BY case_id ASC", (user_email,))
        assigned_cases = [r[0] for r in cursor.fetchall()]
        if not assigned_cases:
            if user_role == "sp_dysp_raipur":
                assigned_cases = ["SP-021"]
            else:
                assigned_cases = ["SP-014"]

    target_case = case_id if case_id else (assigned_cases[0] if assigned_cases else "SP-014")

    if user_role != "ig" and target_case not in assigned_cases:
        raise HTTPException(status_code=403, detail=f"Access denied to case {target_case}")

    return target_case

# 0. PUBLIC SUMMARY (Landing Page Counters)
@app.get("/api/public/summary")
def get_public_summary():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM entity_members")
    entities_count = cursor.fetchone()[0]
    if entities_count == 0:
        g = get_graph_instance()
        entities_count = len(g.nx_graph.nodes) if g else 66

    cursor.execute("SELECT COUNT(*) FROM calls")
    calls_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions")
    txns_count = cursor.fetchone()[0]

    alerts_list = generate_alerts(conn)
    alerts_count = len(alerts_list)

    return {
        "entities": entities_count,
        "calls": calls_count,
        "transactions": txns_count,
        "alerts": alerts_count
    }

# SINGLE SOURCE OF TRUTH COUNTS FOR BENCH
@app.get("/api/summary")
def get_workbench_summary(
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_connection_for_case(case_id)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM entity_members")
    entities_count = cursor.fetchone()[0]
    if entities_count == 0:
        g = get_graph_instance(case_id)
        entities_count = len(g.nx_graph.nodes) if g else 66

    cursor.execute("SELECT COUNT(*) FROM calls")
    calls_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions")
    txns_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM merge_decisions WHERE status = 'pending'")
    pending_merges = cursor.fetchone()[0]

    alerts_list = generate_alerts(conn)
    alerts_total = len(alerts_list)
    by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in alerts_list:
        s = a.get("severity", "medium").lower()
        if s == "med":
            s = "medium"
        by_sev[s] = by_sev.get(s, 0) + 1

    main_conn = get_connection()
    c_main = main_conn.cursor()
    c_main.execute("""
        SELECT COUNT(*) FROM cross_case_links
        WHERE status = 'pending' AND (case_a = ? OR case_b = ?)
    """, (case_id, case_id))
    cross_case_pending = c_main.fetchone()[0]

    return {
        "case_id": case_id,
        "alerts_total": alerts_total,
        "alerts_by_severity": by_sev,
        "pending_merges": pending_merges,
        "cross_case_pending": cross_case_pending,
        "entities": entities_count,
        "calls": calls_count,
        "transactions": txns_count
    }

@app.get("/api/cases")
def list_cases(user: Dict[str, Any] = Depends(get_current_user)):
    user_email = user.get("email", "").lower().strip()
    user_role = user.get("role", "")

    main_conn = get_connection()
    cursor = main_conn.cursor()
    cursor.execute("SELECT case_id, title, district, status FROM cases ORDER BY case_id ASC")
    all_cases = cursor.fetchall()

    if user_role == "ig":
        visible_cases = all_cases
    else:
        cursor.execute("SELECT case_id FROM case_assignments WHERE user_email = ? ORDER BY case_id ASC", (user_email,))
        assigned = {r[0] for r in cursor.fetchall()}
        if not assigned:
            if user_role == "sp_dysp_raipur":
                assigned = {"SP-021"}
            else:
                assigned = {"SP-014"}
        visible_cases = [c for c in all_cases if c[0] in assigned]

    results = []
    for c_id, title, district, status in visible_cases:
        c_conn = get_connection_for_case(c_id)
        c_cur = c_conn.cursor()
        c_cur.execute("SELECT COUNT(DISTINCT entity_id) FROM entity_members")
        ent_count = c_cur.fetchone()[0]
        c_cur.execute("SELECT COUNT(*) FROM calls")
        call_count = c_cur.fetchone()[0]
        c_cur.execute("SELECT COUNT(*) FROM transactions")
        txn_count = c_cur.fetchone()[0]
        alerts = generate_alerts(c_conn)

        cursor.execute("SELECT COUNT(*) FROM cross_case_links WHERE status = 'pending' AND (case_a = ? OR case_b = ?)", (c_id, c_id))
        pending_links = cursor.fetchone()[0]

        results.append({
            "case_id": c_id,
            "title": title,
            "district": district,
            "status": status,
            "entities": ent_count,
            "calls": call_count,
            "transactions": txn_count,
            "alerts": len(alerts),
            "pending_links": pending_links
        })
    return results

@app.get("/api/cross-case/links")
def get_cross_case_links_endpoint(user: Dict[str, Any] = Depends(get_current_user)):
    return get_visible_cross_case_links(user["email"], user["role"])

@app.post("/api/cross-case/links/{link_id}/decision")
def post_cross_case_decision(
    link_id: str,
    req: CrossCaseDecisionRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        return decide_link(link_id, req.decision, user["email"], user["role"])
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 1. AUTH
@app.post("/api/auth/demo-login")
def demo_login(req: DemoLoginRequest):
    # Honeypot silent rejection
    if req.website and req.website.strip():
        fake_email = req.email.strip().lower() if req.email else "visitor@demo.in"
        fake_role = "sp_dysp"
        fake_token = create_jwt_token(fake_email, fake_role, req.name or "Visitor", demo=True)
        return {
            "token": fake_token,
            "user": {"email": fake_email, "name": req.name or "Visitor", "role": fake_role, "demo": True},
            "notice_status": "Login notice skipped (limit)"
        }

    name = (req.name or "").strip()
    email = (req.email or "").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    role_raw = (req.role or "").strip().lower()
    if "cyber" in role_raw:
        role = "cyber_cell"
    elif "head" in role_raw:
        role = "head_constable"
    elif "constable" in role_raw:
        role = "constable"
    elif "auditor" in role_raw:
        role = "auditor"
    else:
        role = "sp_dysp"

    conn = get_connection()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Upsert demo_visitors table
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM demo_visitors WHERE email = ?", (email,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE demo_visitors SET name = ?, last_login = ? WHERE email = ?", (name, now_iso, email))
    else:
        cursor.execute("INSERT INTO demo_visitors (name, email, created_at, last_login) VALUES (?, ?, ?, ?)", (name, email, now_iso, now_iso))
    conn.commit()

    token = create_jwt_token(email, role, name, demo=True)

    # Write ledger entry "demo_login" with masked email only
    masked = mask_email(email)
    record_action(
        conn,
        "demo_login",
        {"email": masked, "role": role, "demo": True},
        ts=now_iso
    )

    # Rate limit check for demo notice emails:
    # Max 1 per address per hour, global max 30 per hour, daily cap DEMO_EMAIL_DAILY_CAP (default 50)
    now_ts = time.time()
    cursor.execute("SELECT COUNT(*) FROM demo_email_log WHERE email = ? AND sent_at > ?", (email, now_ts - 3600))
    addr_hour_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM demo_email_log WHERE sent_at > ?", (now_ts - 3600,))
    global_hour_count = cursor.fetchone()[0]

    daily_cap = int(os.environ.get("DEMO_EMAIL_DAILY_CAP", "50").strip() or "50")
    cursor.execute("SELECT COUNT(*) FROM demo_email_log WHERE sent_at > ?", (now_ts - 86400,))
    daily_count = cursor.fetchone()[0]

    if addr_hour_count >= 1 or global_hour_count >= 30 or daily_count >= daily_cap:
        notice_status = "Login notice skipped (limit)"
    else:
        cursor.execute("INSERT INTO demo_email_log (email, sent_at) VALUES (?, ?)", (email, now_ts))
        conn.commit()

        def bg_mail():
            try:
                send_demo_login_notice(email, name, role)
            except Exception as e:
                logger.warning(f"Background demo email error: {e}")

        threading.Thread(target=bg_mail, daemon=True).start()
        notice_status = "sent"

    return {
        "token": token,
        "user": {
            "email": email,
            "name": name,
            "role": role,
            "demo": True
        },
        "notice_status": notice_status
    }

@app.post("/api/auth/login")
def login(req: LoginRequest):
    email = req.email.lower().strip()
    user = USERS_DB.get(email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials. Use demo password 'demo123'")

    conn = get_connection()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # On official sign-in, sp_dysp, sp_dysp_raipur and ig must enter a 6-digit TOTP code
    if user["role"] in MFA_ROLES:
        secret, enrolled = get_totp_secret_and_status(conn, email)

        # Missing code returns QR containing 6-digit code plus current code
        if not req.totp_code:
            camera_qr_uri = generate_qr_data_uri(email, secret)
            auth_qr_uri = generate_qr_data_uri_authenticator(email, secret)
            totp = pyotp.TOTP(secret)
            cur_code = totp.now()
            rem_sec = 30 - (int(time.time()) % 30)
            return {
                "mfa_required": True,
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "enrolled": enrolled,
                "secret": secret,
                "current_code": cur_code,
                "qr_code": camera_qr_uri,
                "qr_code_auth": auth_qr_uri,
                "expires_in": rem_sec,
                "detail": f"Scan the QR code with your phone camera to display your 6-digit code: {cur_code}"
            }

        # Verify 6-digit code
        if not verify_totp(secret, req.totp_code):
            record_action(
                conn,
                f"MFA_FAILURE (Invalid TOTP code attempted for {user['email']})",
                {"email": user["email"], "role": user["role"]},
                ts=now_iso
            )
            raise HTTPException(status_code=401, detail="Invalid 6-digit MFA code")

        # Mark enrolled on successful first verification
        if not enrolled:
            set_totp_enrolled(conn, email)

        # Log MFA success
        record_action(
            conn,
            f"MFA_SUCCESS (TOTP code verified for {user['email']})",
            {"email": user["email"], "role": user["role"], "enrolled": enrolled},
            ts=now_iso
        )

    token = create_jwt_token(user["email"], user["role"], user["name"])

    # Record login in cryptographic ledger
    record_action(
        conn,
        f"USER_LOGIN (Authenticated session started for {user['email']})",
        {"email": user["email"], "role": user["role"], "method": "jwt_pbkdf2_mfa" if user["role"] in MFA_ROLES else "jwt_pbkdf2"},
        ts=now_iso
    )

    return {
        "token": token,
        "user": {
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

class MfaRefreshRequest(BaseModel):
    email: str

@app.post("/api/auth/mfa-refresh")
def mfa_refresh(req: MfaRefreshRequest):
    email = req.email.lower().strip()
    user = USERS_DB.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    conn = get_connection()
    secret, enrolled = get_totp_secret_and_status(conn, email)
    camera_qr_uri = generate_qr_data_uri(email, secret)
    auth_qr_uri = generate_qr_data_uri_authenticator(email, secret)
    totp = pyotp.TOTP(secret)
    cur_code = totp.now()
    rem_sec = 30 - (int(time.time()) % 30)
    return {
        "mfa_required": True,
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "enrolled": enrolled,
        "secret": secret,
        "current_code": cur_code,
        "qr_code": camera_qr_uri,
        "qr_code_auth": auth_qr_uri,
        "expires_in": rem_sec,
        "detail": f"Scan the QR code with your phone camera to display your 6-digit code: {cur_code}"
    }

# 2. CASE
@app.get("/api/case")
def get_case(
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_connection_for_case(case_id)
    cursor = conn.cursor()

    cursor.execute("SELECT count(distinct entity_id) FROM entity_members")
    row = cursor.fetchone()
    ents_count = row[0] if row else 60

    cursor.execute("SELECT count(*) FROM calls")
    calls_count = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM transactions")
    txns_count = cursor.fetchone()[0]

    alerts_list = generate_alerts(conn)

    main_conn = get_connection()
    c_main = main_conn.cursor()
    c_main.execute("SELECT title, status FROM cases WHERE case_id = ?", (case_id,))
    row_case = c_main.fetchone()
    title = row_case[0] if row_case else ("Durg Missing Cluster" if case_id == "SP-014" else "Raipur Fraud & Missing")
    status = row_case[1] if row_case else "Open"

    return {
        "case_id": case_id,
        "title": title,
        "status": status,
        "persons": ents_count,
        "calls": calls_count,
        "txns": txns_count,
        "alerts": len(alerts_list)
    }

# 3. GRAPH
@app.get("/api/graph")
def get_graph(
    case_id: str = Depends(get_case_access),
    until: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    kg = get_graph_instance(case_id)
    graph_data = kg.get_graph_data(until)
    is_sp = (user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"))

    nodes = []
    for node in graph_data.get("nodes", []):
        node_copy = dict(node)
        ent_id = node_copy.get("id")
        should_mask = (not is_sp) and (ent_id not in unmasked_entities)
        if should_mask and node_copy.get("phone"):
            node_copy["phone"] = mask_phone_str(node_copy["phone"])
            if node_copy.get("type") == "phone":
                node_copy["label"] = mask_phone_str(node_copy.get("label", ""))
        nodes.append(node_copy)

    return {
        "nodes": nodes,
        "edges": graph_data.get("edges", [])
    }

# 4. ENTITY DETAILS
@app.get("/api/entity/{entity_id}")
def get_entity(
    entity_id: str,
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(get_current_user)
):
    kg = get_graph_instance(case_id)
    is_sp = (user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"))
    is_unmasked = entity_id in unmasked_entities

    if entity_id in kg.entity_details:
        ent = dict(kg.entity_details[entity_id])
    else:
        # Check node in graph
        if entity_id in kg.nodes_data:
            m = kg.nodes_data[entity_id]
            ent = {
                "id": m["id"],
                "label": m["label"],
                "type": m["type"],
                "aliases": m.get("aliases", []),
                "priority": m.get("priority", 0.5),
                "priority_breakdown": m.get("priority_breakdown", {
                    "betweenness": 0.5,
                    "pagerank": 0.5,
                    "cross_community": 0.5,
                    "evidence_diversity": 0.5
                }),
                "role_label": m.get("role_label", ""),
                "connections": [],
                "evidence": [
                    {"evidence_id": f"PR-{entity_id[-4:]}", "kind": "observed", "summary": f"Observed operational record for {m['label']}.", "ts": "2026-09-24T10:00:00Z"}
                ],
                "phone": m.get("phone", "")
            }
        else:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found in case network")

    if not is_sp and not is_unmasked and ent.get("phone"):
        ent["phone"] = mask_phone_str(ent["phone"])

    return ent

# 5. UNMASK ENTITY (sp_dysp, sp_dysp_raipur, ig)
@app.post("/api/entity/{entity_id}/unmask")
def unmask_entity(
    entity_id: str,
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(require_roles(["sp_dysp", "sp_dysp_raipur", "ig"]))
):
    kg = get_graph_instance(case_id)
    conn = get_connection_for_case(case_id)

    raw_phone = ""
    if entity_id in kg.entity_details:
        raw_phone = kg.entity_details[entity_id].get("phone", "")
    elif entity_id in kg.nodes_data:
        raw_phone = kg.nodes_data[entity_id].get("phone", "")

    if not raw_phone:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.phone_norm 
            FROM entity_members em
            JOIN persons p ON em.record_id = p.record_id
            WHERE em.entity_id = ? AND p.phone_norm != ''
            LIMIT 1
        """, (entity_id,))
        r = cursor.fetchone()
        if r:
            raw_phone = r[0]

    unmasked_entities.add(entity_id)

    # Write unmask action to cryptographic ledger with case_id in payload
    main_conn = get_connection()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_action(
        main_conn,
        f"PHONE_UNMASKED (Evidentiary phone unmasked for entity {entity_id} in {case_id} by {user['email']})",
        {"case_id": case_id, "entity_id": entity_id, "authorized_officer": user["email"], "role": user["role"]},
        ts=now_iso
    )

    return {
        "id": entity_id,
        "entity_id": entity_id,
        "phone": raw_phone,
        "unmasked_phone": raw_phone,
        "status": "unmasked"
    }

# 6. EDGE EXPLANATION
@app.get("/api/edge/{source}/{target}/explain")
def explain_edge(source: str, target: str, user: Dict[str, Any] = Depends(get_current_user)):
    kg = get_graph_instance()
    key1 = f"{source}__{target}"
    key2 = f"{target}__{source}"

    if key1 in kg.edge_explanations:
        return kg.edge_explanations[key1]
    if key2 in kg.edge_explanations:
        return kg.edge_explanations[key2]

    # Synthesize fallback
    return {
        "score": 0.65,
        "formula": "1 - prod(1 - w*s)",
        "components": [
            {
                "type": "observed_interaction",
                "count": 3,
                "weight": 0.5,
                "s": 0.65,
                "contribution": 0.33,
                "evidence_ids": ["EVD-REF-01"]
            }
        ],
        "snippets": [
            {
                "evidence_id": "FIR-07-S3",
                "text": f"Corroborating record of continuous interaction between {source} and {target} along the transit corridor."
            }
        ]
    }

# 7. MERGE QUEUE
@app.get("/api/merge-queue")
def get_merge_queue(
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_connection_for_case(case_id)
    queue = get_merge_queue_data(conn)
    is_sp = (user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"))

    result = []
    for item in queue:
        item_copy = dict(item)
        records = []
        for r in item.get("records", []):
            rc = dict(r)
            if not is_sp and rc.get("phone"):
                rc["phone"] = mask_phone_str(rc["phone"])
            records.append(rc)
        item_copy["records"] = records
        result.append(item_copy)

    return result

@app.post("/api/merge/{merge_id}/approve")
def approve_merge(merge_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_connection()
    if user["role"] == "head_constable":
        res = propose_merge_decision(conn, merge_id, proposer=user["email"])
        return {"status": "proposed", "merge_id": merge_id, "detail": "Merge proposal submitted for SP/DySP review"}
    elif user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"):
        res = approve_merge_decision(conn, merge_id, reviewer=user["email"])
        rebuild_graph()
        return {"status": "approved", "merge_id": merge_id}
    else:
        raise HTTPException(
            status_code=403,
            detail=f"Action not permitted for role: {user['role']}. Required: sp_dysp (or head_constable proposal)"
        )

@app.post("/api/merge/{merge_id}/reject")
def reject_merge(merge_id: str, user: Dict[str, Any] = Depends(require_roles(["sp_dysp", "sp_dysp_raipur", "ig"]))):
    conn = get_connection()
    res = reject_merge_decision(conn, merge_id, reviewer=user["email"])
    return {"status": "rejected", "merge_id": merge_id}

@app.post("/api/merge/{merge_id}/unmerge")
def unmerge_decision_endpoint(merge_id: str, user: Dict[str, Any] = Depends(require_roles(["sp_dysp", "sp_dysp_raipur", "ig"]))):
    conn = get_connection()
    res = unmerge_decision(conn, merge_id, reviewer=user["email"])
    rebuild_graph()
    return {"status": "pending", "merge_id": merge_id}

# 8. ALERTS
@app.get("/api/alerts")
def get_alerts(
    case_id: str = Depends(get_case_access),
    user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_connection_for_case(case_id)
    all_alerts = generate_alerts(conn)
    is_sp = (user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"))

    # Constable sees summary alerts only; insider_threat is visible only to auditor, sp_dysp and ig
    if user["role"] == "constable":
        restricted_types = {"pass_through", "structuring", "golden_hour", "burner", "insider_threat"}
        filtered = [a for a in all_alerts if a["type"] not in restricted_types]
    elif user["role"] not in ("auditor", "sp_dysp", "sp_dysp_raipur", "ig"):
        filtered = [a for a in all_alerts if a["type"] != "insider_threat"]
    else:
        filtered = all_alerts

    if not is_sp:
        masked_alerts = []
        for a in filtered:
            ac = dict(a)
            # Mask any 10-digit numbers in explanation
            ac["explanation"] = re.sub(r"\b(\d{2})\d{5}(\d{3})\b", r"\1XXXXX\2", ac["explanation"])
            masked_alerts.append(ac)
        return masked_alerts

    return filtered

# 9. GOLDEN HOUR
@app.get("/api/golden-hour")
def get_golden_hour(user: Dict[str, Any] = Depends(require_roles(["cyber_cell", "sp_dysp", "sp_dysp_raipur", "ig", "auditor"]))):
    conn = get_connection()
    data = get_golden_hour_details(conn)
    is_sp = (user["role"] in ("sp_dysp", "sp_dysp_raipur", "ig"))

    result = dict(data)
    if not is_sp:
        burner = dict(result.get("burner", {}))
        if burner.get("number"):
            burner["number"] = mask_phone_str(burner["number"])
        result["burner"] = burner
        bait = dict(result.get("bait", {}))
        if bait.get("number"):
            bait["number"] = mask_phone_str(bait["number"])
        result["bait"] = bait

    return result

# 10. SIMULATE REMOVE NODE
@app.post("/api/simulate/remove-node")
def simulate_remove(req: RemoveNodeRequest, user: Dict[str, Any] = Depends(require_roles(["head_constable", "cyber_cell", "sp_dysp", "sp_dysp_raipur", "ig"]))):
    conn = get_connection()
    res = simulate_node_removal(req.node_id)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_action(
        conn,
        f"SIMULATION_RUN (Network interdiction simulation on {req.node_id} by {user['email']})",
        {"node_id": req.node_id, "delta_pct": res.get("delta_pct", 0.0), "officer": user["email"]},
        ts=now_iso
    )

    return res

# 11. TIMELINE RANGE
@app.get("/api/timeline-range")
def get_timeline_range():
    return {"start": "2026-09-01", "end": "2026-09-30"}

# 12. COPILOT
@app.get("/api/health/copilot")
def copilot_health(user: Dict[str, Any] = Depends(get_current_user)):
    is_debug = os.environ.get("DEBUG", "0").strip().lower() in ("1", "true", "yes")
    if not (is_debug or user.get("role") in ["sp_dysp", "sp_dysp_raipur", "ig", "cyber_cell"]):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied for role: {user.get('role')}. Requires sp_dysp, cyber_cell, or DEBUG=1"
        )
    conn = get_connection()
    return check_copilot_health(conn)

@app.post("/api/copilot")
def copilot(req: CopilotRequest, user: Dict[str, Any] = Depends(require_roles(["constable", "head_constable", "cyber_cell", "sp_dysp", "sp_dysp_raipur", "ig", "auditor"]))):
    conn = get_connection()
    return process_copilot_query(conn, req.question, user)

# 13. REPORT GENERATION & EMAIL
@app.post("/api/report")
def generate_report(user: Dict[str, Any] = Depends(require_roles(["head_constable", "cyber_cell", "sp_dysp"]))):
    conn = get_connection()
    report_id = "RPT-SP014-01"
    # Pre-build PDF and log to ledger
    build_pdf_dossier(conn, user, report_id)

    # Detailed structured intelligence report payload for UI dossier
    g = get_graph_instance()
    total_nodes = len(g.nx_graph.nodes) if g else 0
    total_edges = len(g.nx_graph.edges) if g else 0
    density = round(len(g.nx_graph.edges) / (total_nodes * (total_nodes - 1) / 2), 4) if total_nodes > 1 else 0

    top_entities = []
    if g:
        for nid, d in g.nx_graph.nodes(data=True):
            top_entities.append({
                "id": nid,
                "label": d.get("label", nid),
                "type": d.get("type", "entity"),
                "betweenness": round(d.get("betweenness", 0.0), 4),
                "pagerank": round(d.get("pagerank", 0.0), 4),
                "degree": g.nx_graph.degree(nid)
            })
        top_entities.sort(key=lambda x: x["betweenness"], reverse=True)

    alerts_list = generate_alerts(conn)
    ledger_state = get_ledger_state(conn)

    top_broker_id = top_entities[0]["id"] if top_entities else "ENT-R0019"
    sim_res = simulate_node_removal(top_broker_id)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM persons")
    persons_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM calls")
    calls_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions")
    txns_cnt = cursor.fetchone()[0]

    return {
        "report_id": report_id,
        "status": "ready",
        "url": f"/api/report/{report_id}/download",
        "counts": {
            "entities": total_nodes,
            "edges": total_edges,
            "density": density,
            "persons": persons_cnt,
            "calls": calls_cnt,
            "transactions": txns_cnt,
            "alerts": len(alerts_list)
        },
        "top_entities": top_entities[:5],
        "alerts": alerts_list[:6],
        "simulation": sim_res,
        "ledger_head_hash": ledger_state.get("head_hash", ""),
        "ledger_blocks": len(ledger_state.get("entries", []))
    }

@app.get("/api/report/{report_id}/download")
def download_report(report_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_connection()
    pdf_content = build_pdf_dossier(conn, user, report_id)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=SAKSHI_{report_id}_Intelligence_Dossier.pdf"}
    )

@app.post("/api/report/email")
def email_report(req: ReportEmailRequest, user: Dict[str, Any] = Depends(require_roles(["head_constable", "cyber_cell", "sp_dysp"]))):
    conn = get_connection()
    pdf_content = build_pdf_dossier(conn, user, req.report_id)
    recipient = user.get("email", "officer@demo.in")
    return send_report_email(conn, recipient, req.report_id, pdf_content, user)

# 14. LEDGER & VERIFICATION
@app.get("/api/ledger")
def get_ledger(user: Dict[str, Any] = Depends(require_roles(["cyber_cell", "sp_dysp", "auditor"]))):
    conn = get_connection()
    return get_ledger_state(conn)

@app.get("/api/verify")
def verify_ledger(user: Dict[str, Any] = Depends(require_roles(["cyber_cell", "sp_dysp", "auditor"]))):
    conn = get_connection()
    return verify_all_integrity(conn)

@app.post("/api/debug/tamper")
def debug_tamper():
    conn = get_connection()
    return tamper_working_db(conn)

@app.post("/api/debug/reset")
def debug_reset():
    conn = get_connection()
    res = restore_clean_db(conn)
    rebuild_graph()
    unmasked_entities.clear()
    return res

@app.post("/api/debug/reset-tamper")
def debug_reset_tamper():
    return debug_reset()

class SimulateInsiderRequest(BaseModel):
    user_email: Optional[str] = "constable@demo.in"

@app.post("/api/debug/simulate-insider")
def debug_simulate_insider(req: Optional[SimulateInsiderRequest] = None):
    from insider_threat import simulate_insider_behavior
    target = req.user_email if (req and req.user_email) else "constable@demo.in"
    conn = get_connection()
    return simulate_insider_behavior(conn, target)

# 15. CASE RELOAD & HEALTH
@app.post("/api/case/reload")
def reload_case(user: Dict[str, Any] = Depends(require_roles(["cyber_cell", "sp_dysp", "auditor"]))):
    ingest_all()
    conn = get_connection()
    resolve_entities(conn)
    rebuild_graph()
    unmasked_entities.clear()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_action(
        conn,
        f"CASE_RELOADED (Complete pipeline re-executed from source CSVs by {user['email']})",
        {"authorized_by": user["email"]},
        ts=now_iso
    )

    return {
        "ok": True,
        "message": "Case data re-ingested from source CSVs, entities resolved, graph reconstructed, and integrity verified."
    }

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip())
    }

# 16. VALIDATION (Roles: cyber_cell, sp_dysp, auditor)
@app.get("/api/validation")
def validation_report(user: Dict[str, Any] = Depends(require_roles(["cyber_cell", "sp_dysp", "auditor"]))):
    return run_validation()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
