import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Set, Optional
import sqlite3
from rapidfuzz import fuzz

from db import get_connection
from ledger import record_action

AUTO_THRESHOLD = 0.85
PENDING_THRESHOLD = 0.55

class UnionFind:
    def __init__(self, elements):
        self.parent = {x: x for x in elements}
        self.rank = {x: 0 for x in elements}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1

def compute_pair_score(p1: Dict[str, Any], p2: Dict[str, Any], contacts_map: Dict[str, Set[str]]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Computes explainable match score between two person records.
    Returns (score, reasons_list).
    """
    reasons = []
    score = 0.0

    # 1. Strong Anchor: Exact normalized phone or plate match
    ph_match = bool(p1["phone_norm"] and p2["phone_norm"] and p1["phone_norm"] == p2["phone_norm"])
    pl_match = bool(p1["plate_norm"] and p2["plate_norm"] and p1["plate_norm"] == p2["plate_norm"])
    if ph_match or pl_match:
        score += 0.9
        matched_str = p1["phone_norm"] if ph_match else p1["plate_norm"]
        reasons.append({
            "factor": f"Exact {'cellular phone' if ph_match else 'vehicle plate'} anchor match ({matched_str})",
            "value": 0.9
        })

    # 2. Name similarity & phonetic / alias compatibility (up to +0.4)
    n1 = p1["clean_name"].lower().strip()
    n2 = p2["clean_name"].lower().strip()
    aliases1 = json.loads(p1.get("aliases_json") or "[]")
    aliases2 = json.loads(p2.get("aliases_json") or "[]")

    base_ratio = fuzz.token_sort_ratio(n1, n2) / 100.0

    toks1 = [t for t in re.split(r"[\s\.]+", n1) if t]
    toks2 = [t for t in re.split(r"[\s\.]+", n2) if t]

    if toks1 and toks2:
        # Check first name prefix, e.g. "suresh" vs "sureshchandra"
        f1, f2 = toks1[0], toks2[0]
        if (f1.startswith(f2) or f2.startswith(f1)) and min(len(f1), len(f2)) >= 4:
            base_ratio = max(base_ratio, 0.88)
        
        # Check initial expansion, e.g. "D. K." vs "Dinesh Kumar"
        if len(toks1) == len(toks2):
            if all(t1.startswith(t2) or t2.startswith(t1) for t1, t2 in zip(toks1, toks2)):
                base_ratio = max(base_ratio, 0.90)

        # Single initial with shared surname, e.g. "K. Mishra" vs "Karan Mishra" or "A. Sonwani" vs "Ashok Sonwani"
        if len(toks1) >= 2 and len(toks2) >= 2:
            s1, s2 = toks1[-1], toks2[-1]
            if s1 == s2 or fuzz.token_sort_ratio(s1, s2) >= 80:
                if toks1[0][0] == toks2[0][0]:
                    base_ratio = max(base_ratio, 0.88)

    # Check aliases
    for a in aliases1:
        if a.lower() in n2 or fuzz.token_sort_ratio(a.lower(), n2) > 80:
            base_ratio = max(base_ratio, 0.85)
    for a in aliases2:
        if a.lower() in n1 or fuzz.token_sort_ratio(a.lower(), n1) > 80:
            base_ratio = max(base_ratio, 0.85)

    # If neither phone nor plate matches and name similarity is too low (< 0.50), reject as distinct personas
    if not (ph_match or pl_match) and base_ratio < 0.50:
        return 0.0, []

    name_contrib = round(min(0.4, base_ratio * 0.4), 3)
    if name_contrib >= 0.15:
        score += name_contrib
        reasons.append({
            "factor": "Name phonetics, alias match & token overlap",
            "value": round(base_ratio, 2)
        })

    # 3. Shared Organization (+0.3)
    if p1["org_id"] and p2["org_id"] and p1["org_id"] == p2["org_id"]:
        score += 0.3
        reasons.append({
            "factor": f"Shared registered organization ({p1['org_id']})",
            "value": 0.3
        })

    # 4. Shared Address (+0.2)
    if p1["address"] and p2["address"]:
        a1, a2 = p1["address"].lower(), p2["address"].lower()
        addr_sim = fuzz.token_set_ratio(a1, a2) / 100.0
        if addr_sim >= 0.50:
            addr_contrib = round(min(0.2, addr_sim * 0.2), 3)
            score += addr_contrib
            reasons.append({
                "factor": "Shared residential / locality address footprint",
                "value": round(addr_sim, 2)
            })

    # 5. Shared Neighbors / Contacts (Jaccard, up to +0.3)
    c1 = contacts_map.get(p1["phone_norm"], set())
    c2 = contacts_map.get(p2["phone_norm"], set())
    if c1 and c2:
        u = c1 | c2
        if u and (c1 & c2):
            jaccard = len(c1 & c2) / len(u)
            contact_contrib = round(min(0.3, jaccard * 0.5 + 0.1), 3)
            score += contact_contrib
            reasons.append({
                "factor": "Shared cellular contact neighbors (Jaccard co-calls)",
                "value": round(jaccard, 2)
            })

    # 6. Negative Penalties: Conflicting DOB (-0.5) or Discrepant City (-0.5)
    if p1["dob"] and p2["dob"]:
        if p1["dob"] == p2["dob"]:
            score += 0.20
            reasons.append({
                "factor": "Identical birthdate verification",
                "value": 0.20
            })
        else:
            score -= 0.50
            reasons.append({
                "factor": "Conflicting date of birth discrepancy",
                "value": -0.50
            })

    if p1["city"] and p2["city"] and p1["city"] != p2["city"]:
        score -= 0.50
        reasons.append({
            "factor": "Discrepant municipal registration city",
            "value": -0.50
        })

    final_score = min(1.0, max(0.0, round(score, 3)))
    return final_score, reasons

def get_candidate_pairs(persons: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """Blocks records into candidate pairs using phonetic keys, anchors, orgs, and prefixes."""
    candidates = set()
    n = len(persons)

    for i in range(n):
        for j in range(i + 1, n):
            p1, p2 = persons[i], persons[j]
            match = False

            # Same non-empty phone or plate
            if p1["phone_norm"] and p1["phone_norm"] == p2["phone_norm"]:
                match = True
            elif p1["plate_norm"] and p1["plate_norm"] == p2["plate_norm"]:
                match = True
            # Same non-empty phonetic key
            elif p1["phonetic_key"] and p1["phonetic_key"] == p2["phonetic_key"]:
                match = True
            # Same organization
            elif p1["org_id"] and p1["org_id"] == p2["org_id"]:
                match = True
            # Same DOB
            elif p1["dob"] and p1["dob"] == p2["dob"]:
                match = True
            else:
                n1 = p1["clean_name"].lower().split()
                n2 = p2["clean_name"].lower().split()
                if n1 and n2:
                    # First name prefix match
                    if (n1[0].startswith(n2[0]) or n2[0].startswith(n1[0])) and min(len(n1[0]), len(n2[0])) >= 4:
                        match = True
                    # Initial + same surname (e.g. K. Mishra and Karan Mishra, A. Sonwani and Ashok Sonwani)
                    elif len(n1) >= 2 and len(n2) >= 2 and n1[0][0] == n2[0][0]:
                        s1, s2 = n1[-1], n2[-1]
                        if s1 == s2 or fuzz.token_sort_ratio(s1, s2) >= 80:
                            match = True

            if match:
                pair = tuple(sorted([p1["record_id"], p2["record_id"]]))
                candidates.add(pair)

    return candidates

def resolve_entities(conn: sqlite3.Connection, auto_thresh: float = AUTO_THRESHOLD, pending_thresh: float = PENDING_THRESHOLD) -> Dict[str, Any]:
    """
    Executes entity resolution over persons table.
    Populates merge_decisions and entity_members tables.
    Returns summary statistics.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM persons")
    persons = [dict(r) for r in cursor.fetchall()]
    persons_map = {p["record_id"]: p for p in persons}

    # Build contacts map
    cursor.execute("SELECT caller_norm, callee_norm FROM calls")
    contacts_map = {}
    for row in cursor.fetchall():
        c, d = row[0], row[1]
        if c:
            contacts_map.setdefault(c, set()).add(d)
        if d:
            contacts_map.setdefault(d, set()).add(c)

    # Fetch existing decisions to preserve approved/rejected/proposed states
    cursor.execute("SELECT id, status, reviewer FROM merge_decisions")
    existing_decisions = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}

    candidates = get_candidate_pairs(persons)

    auto_pairs = []
    pending_pairs = []

    for rid1, rid2 in candidates:
        p1, p2 = persons_map[rid1], persons_map[rid2]
        score, reasons = compute_pair_score(p1, p2, contacts_map)
        merge_id = f"MQ-{rid1}-{rid2}"

        if score >= pending_thresh:
            existing_status = existing_decisions.get(merge_id, (None, None))[0]
            if existing_status:
                current_status = existing_status
            else:
                current_status = "auto" if score >= auto_thresh else "pending"

            reasons_json = json.dumps(reasons)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            cursor.execute("""
                INSERT OR REPLACE INTO merge_decisions (id, record_a, record_b, score, status, reasons_json, reviewer, decided_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (merge_id, rid1, rid2, score, current_status, reasons_json, None, now_iso))

            if current_status in ["auto", "approved"]:
                auto_pairs.append((rid1, rid2, score, reasons))
            elif current_status in ["pending", "proposed"]:
                pending_pairs.append((merge_id, rid1, rid2, score, reasons))

    # Build active clusters via Union-Find using ONLY auto and approved links
    uf = UnionFind(list(persons_map.keys()))
    for rid1, rid2, _, _ in auto_pairs:
        uf.union(rid1, rid2)

    # Create entity mapping: entity_id is root record_id or formatted ENT-xxxx
    root_to_members = {}
    for rid in persons_map.keys():
        root = uf.find(rid)
        root_to_members.setdefault(root, []).append(rid)

    # Clear and rewrite entity_members
    cursor.execute("DELETE FROM entity_members")
    for root, members in root_to_members.items():
        ent_id = f"ENT-{root}"
        for member_id in members:
            cursor.execute("""
                SELECT score, reasons_json, status FROM merge_decisions 
                WHERE (record_a = ? OR record_b = ?) AND status IN ('auto', 'approved')
                ORDER BY score DESC LIMIT 1
            """, (member_id, member_id))
            dec_row = cursor.fetchone()
            if dec_row:
                m_score, m_reasons, m_status = dec_row[0], dec_row[1], dec_row[2]
            else:
                m_score, m_reasons, m_status = 1.0, json.dumps([{"factor": "Single source record", "value": 1.0}]), "auto"

            cursor.execute("""
                INSERT INTO entity_members (entity_id, record_id, score, reasons_json, status)
                VALUES (?, ?, ?, ?, ?)
            """, (ent_id, member_id, m_score, m_reasons, m_status))

    conn.commit()

    return {
        "total_records": len(persons),
        "total_entities": len(root_to_members),
        "auto_merged_pairs": len(auto_pairs),
        "pending_pairs": len(pending_pairs)
    }

def get_merge_queue_data(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Retrieves pending merge candidates formatted exactly as required by Stage 1 frontend."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT md.id, md.record_a, md.record_b, md.score, md.status, md.reasons_json
        FROM merge_decisions md
        ORDER BY md.score DESC
    """)
    rows = cursor.fetchall()

    cursor.execute("SELECT * FROM persons")
    persons = {r["record_id"]: dict(r) for r in cursor.fetchall()}

    queue = []
    for r in rows:
        m_id, ra, rb, score, status, reasons_json = r[0], r[1], r[2], r[3], r[4], r[5]
        p1 = persons.get(ra, {})
        p2 = persons.get(rb, {})

        rec1 = {
            "record_id": ra,
            "name": p1.get("name", ra),
            "phone": p1.get("phone_norm", ""),
            "plate": p1.get("plate_norm", ""),
            "source": f"{p1.get('source_doc', 'Source')} (Address: {p1.get('address', 'N/A')})"
        }
        rec2 = {
            "record_id": rb,
            "name": p2.get("name", rb),
            "phone": p2.get("phone_norm", ""),
            "plate": p2.get("plate_norm", ""),
            "source": f"{p2.get('source_doc', 'Source')} (Address: {p2.get('address', 'N/A')})"
        }

        clamped_score = min(1.0, max(0.0, score))
        queue.append({
            "id": m_id,
            "score": round(clamped_score, 2),
            "status": status,
            "records": [rec1, rec2],
            "reasons": json.loads(reasons_json)
        })

    return queue

def approve_merge_decision(conn: sqlite3.Connection, merge_id: str, reviewer: str = "sp_dysp") -> Dict[str, Any]:
    """Approves a merge candidate and writes the decision to the cryptographic ledger."""
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
        UPDATE merge_decisions 
        SET status = 'approved', reviewer = ?, decided_at = ?
        WHERE id = ?
    """, (reviewer, now_iso, merge_id))
    conn.commit()

    resolve_entities(conn)

    record_action(
        conn,
        f"MERGE_APPROVED (Candidate {merge_id} authorized by {reviewer})",
        {"merge_id": merge_id, "reviewer": reviewer, "action": "approve"},
        ts=now_iso
    )

    return {"status": "approved", "merge_id": merge_id}

def reject_merge_decision(conn: sqlite3.Connection, merge_id: str, reviewer: str = "sp_dysp") -> Dict[str, Any]:
    """Rejects a merge candidate and writes the decision to the cryptographic ledger."""
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
        UPDATE merge_decisions 
        SET status = 'rejected', reviewer = ?, decided_at = ?
        WHERE id = ?
    """, (reviewer, now_iso, merge_id))
    conn.commit()

    resolve_entities(conn)

    record_action(
        conn,
        f"MERGE_REJECTED (Candidate {merge_id} dismissed by {reviewer})",
        {"merge_id": merge_id, "reviewer": reviewer, "action": "reject"},
        ts=now_iso
    )

    return {"status": "rejected", "merge_id": merge_id}

def unmerge_decision(conn: sqlite3.Connection, merge_id: str, reviewer: str = "sp_dysp") -> Dict[str, Any]:
    """Unmerges an approved candidate back to pending review."""
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
        UPDATE merge_decisions 
        SET status = 'pending', reviewer = ?, decided_at = ?
        WHERE id = ?
    """, (reviewer, now_iso, merge_id))
    conn.commit()

    resolve_entities(conn)

    record_action(
        conn,
        f"MERGE_UNMERGED (Candidate {merge_id} rolled back by {reviewer})",
        {"merge_id": merge_id, "reviewer": reviewer, "action": "unmerge"},
        ts=now_iso
    )

    return {"status": "pending", "merge_id": merge_id}

def propose_merge_decision(conn: sqlite3.Connection, merge_id: str, proposer: str = "head_constable") -> Dict[str, Any]:
    """Head Constable or non-SP proposes a merge candidate for SP review."""
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
        UPDATE merge_decisions 
        SET status = 'proposed', reviewer = ?, decided_at = ?
        WHERE id = ?
    """, (proposer, now_iso, merge_id))
    conn.commit()

    record_action(
        conn,
        f"MERGE_PROPOSED (Candidate {merge_id} submitted for review by {proposer})",
        {"merge_id": merge_id, "proposer": proposer, "status": "proposed"},
        ts=now_iso
    )

    return {"status": "proposed", "merge_id": merge_id}

if __name__ == "__main__":
    conn = get_connection()
    res = resolve_entities(conn)
    print("Entity resolution completed:")
    print(res)
    q = get_merge_queue_data(conn)
    print(f"Total merge decisions: {len(q)}")
    for item in q:
        if item["status"] == "pending":
            print(f"  PENDING: {item['id']} score={item['score']}, records={[r['name'] for r in item['records']]}")
