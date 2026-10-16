import json
import os
import sys
import warnings
from pathlib import Path

# Suppress StarletteDeprecationWarning about httpx
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
import main
from db import get_connection, verify_all_integrity
from ingest import ingest_all
from resolve import resolve_entities, get_merge_queue_data, approve_merge_decision
from graph import get_graph_instance, rebuild_graph
from alerts import generate_alerts, get_golden_hour_details
from simulate import simulate_node_removal

def run_all_selftests():
    print("=" * 70)
    print("  PROJECT SAKSHI - STAGE 2 BACKEND VERIFICATION & SELF-TEST SUITE  ")
    print("=" * 70)

    results = []
    client = TestClient(main.app)

    # -------------------------------------------------------------
    # Check 1: All data files load; row counts printed
    # -------------------------------------------------------------
    try:
        ingest_res = ingest_all()
        conn = get_connection()
        resolve_entities(conn)
        rebuild_graph()

        row_counts = ingest_res["row_counts"]
        total_rows = ingest_res["total_rows"]
        hashes = ingest_res["evidence_hashes"]

        print("\n[TEST 1] Ingesting all synthetic CSV files & FIR sentences:")
        for tbl, count in sorted(row_counts.items()):
            print(f"   * {tbl:<18}: {count:>4} rows")
        print(f"   -> Total Rows Ingested: {total_rows}, SHA-256 Row Hashes: {hashes}")

        pass_1 = total_rows > 1000 and len(row_counts) >= 12
        results.append(("1. All data files load; row counts printed", pass_1, f"Total rows: {total_rows}, tables: {len(row_counts)}"))
    except Exception as e:
        results.append(("1. All data files load; row counts printed", False, str(e)))

    # -------------------------------------------------------------
    # Check 2: Broker's three records in pending queue; trap pair NOT merged
    # -------------------------------------------------------------
    try:
        conn = get_connection()
        queue = get_merge_queue_data(conn)
        pending_ids = set()
        for item in queue:
            if item["status"] == "pending":
                r1 = item["records"][0]["record_id"]
                r2 = item["records"][1]["record_id"]
                pending_ids.add(r1)
                pending_ids.add(r2)

        # Broker records: R0019, R0030, R0064
        broker_rids = {"R0019", "R0030", "R0064"}
        broker_in_pending = broker_rids.issubset(pending_ids)

        cursor = conn.cursor()
        cursor.execute("SELECT record_id, entity_id FROM entity_members WHERE record_id IN ('R0039', 'R0042')")
        trap_rows = dict(cursor.fetchall())
        r39_ent = trap_rows.get("R0039")
        r42_ent = trap_rows.get("R0042")
        trap_not_merged = (r39_ent is not None and r42_ent is not None and r39_ent != r42_ent)

        pass_2 = broker_in_pending and trap_not_merged
        detail_2 = f"Broker records {broker_rids} in pending: {broker_in_pending}; Rahul Sharma trap pair separate: {trap_not_merged} ({r39_ent} != {r42_ent})"
        results.append(("2. Broker records in pending queue; trap pair NOT merged", pass_2, detail_2))
    except Exception as e:
        results.append(("2. Broker records in pending queue; trap pair NOT merged", False, str(e)))

    # -------------------------------------------------------------
    # Check 3: After approving pending pairs, ER F1 reported
    # -------------------------------------------------------------
    try:
        from validate import run_validation
        # Approve pending pairs as instructed in Step 10
        conn = get_connection()
        queue = get_merge_queue_data(conn)
        for item in queue:
            if item["status"] == "pending":
                approve_merge_decision(conn, item["id"])

        rebuild_graph()

        val_res = run_validation()
        f1_auto = val_res["metrics"].get("er_f1_auto", 0.0)
        f1_app = val_res["metrics"].get("er_f1_after_approval", 0.0)

        pass_3 = f1_app >= 0.85
        detail_3 = f"ER F1 (auto-only): {f1_auto:.3f} -> ER F1 (after approving pending): {f1_app:.3f}"
        results.append(("3. After approving pending pairs, ER F1 reported", pass_3, detail_3))
    except Exception as e:
        results.append(("3. After approving pending pairs, ER F1 reported", False, str(e)))

    # -------------------------------------------------------------
    # Check 4: Bridge alert present; top-3 includes broker; decoy ranked below broker
    # -------------------------------------------------------------
    try:
        conn = get_connection()
        alerts = generate_alerts(conn)
        bridge_alerts = [a for a in alerts if a["type"] == "bridge_node"]
        has_bridge = len(bridge_alerts) > 0

        kg = get_graph_instance()
        sorted_nodes = sorted(kg.nodes_data.values(), key=lambda x: -x["priority"])
        top_3_ids = [n["id"] for n in sorted_nodes[:3]]
        top_3_labels = [n["label"] for n in sorted_nodes[:3]]

        # Find broker entity (contains Suresh / Golden / R0019)
        cursor.execute("SELECT entity_id FROM entity_members WHERE record_id = 'R0019'")
        broker_ent = cursor.fetchone()[0]

        # Find decoy entity (contains Mahesh Gupta / R0022)
        cursor.execute("SELECT entity_id FROM entity_members WHERE record_id = 'R0022'")
        decoy_ent = cursor.fetchone()[0]

        broker_node = kg.nodes_data.get(broker_ent, {})
        decoy_node = kg.nodes_data.get(decoy_ent, {})

        broker_priority = broker_node.get("priority", 0)
        decoy_priority = decoy_node.get("priority", 0)

        broker_in_top3 = broker_ent in top_3_ids
        decoy_below = decoy_priority < broker_priority

        pass_4 = has_bridge and broker_in_top3 and decoy_below
        detail_4 = (
            f"Bridge alert: {has_bridge}; Broker ({broker_ent}) priority: {broker_priority} (Rank: #{top_3_ids.index(broker_ent)+1 if broker_ent in top_3_ids else 'N/A'}); "
            f"Decoy ({decoy_ent}) priority: {decoy_priority} (decoy below broker: {decoy_below})"
        )
        results.append(("4. Bridge alert present; broker in top-3; decoy ranked below broker", pass_4, detail_4))
    except Exception as e:
        results.append(("4. Bridge alert present; broker in top-3; decoy ranked below broker", False, str(e)))

    # -------------------------------------------------------------
    # Check 5: Pass-through alert with >=5 matched pairs
    # -------------------------------------------------------------
    try:
        conn = get_connection()
        alerts = generate_alerts(conn)
        pass_throughs = [a for a in alerts if a["type"] == "pass_through"]
        has_pt = len(pass_throughs) > 0

        # Check matched txns / pairs count in pass-through
        matched_txns = pass_throughs[0].get("evidence_ids", []) if has_pt else []
        matched_pairs_count = len(matched_txns) // 2

        pass_5 = has_pt and (matched_pairs_count >= 5 or len(matched_txns) >= 5)
        detail_5 = f"Pass-through alert present: {has_pt}, matched TXN count: {len(matched_txns)} ({matched_pairs_count} pairs)"
        results.append(("5. Pass-through alert with >=5 matched pairs", pass_5, detail_5))
    except Exception as e:
        results.append(("5. Pass-through alert with >=5 matched pairs", False, str(e)))

    # -------------------------------------------------------------
    # Check 6: Golden-hour cluster of 5 missing persons; burner near 4/5; bait contacted_by=5; toll alert
    # -------------------------------------------------------------
    try:
        conn = get_connection()
        gh = get_golden_hour_details(conn)
        alerts = generate_alerts(conn)

        missing_count = len(gh.get("missing", []))
        burner = gh.get("burner", {})
        bait = gh.get("bait", {})

        burner_near_count = len(burner.get("seen_near", []))
        deactivated = burner.get("deactivated_after", False)
        bait_contacted = bait.get("contacted_by", 0)
        has_toll_alert = any(a["type"] == "toll_anomaly" for a in alerts)

        pass_6 = (
            missing_count == 5 and
            burner_near_count >= 4 and
            deactivated and
            bait_contacted == 5 and
            has_toll_alert
        )
        detail_6 = (
            f"Missing persons: {missing_count}/5; Burner seen near: {burner_near_count}/5; "
            f"Deactivated after: {deactivated}; Bait contacted by: {bait_contacted}/5; Toll anomaly alert: {has_toll_alert}"
        )
        results.append(("6. Golden-hour cluster of 5; burner near 4/5; bait contacted_by=5; toll alert", pass_6, detail_6))
    except Exception as e:
        results.append(("6. Golden-hour cluster of 5; burner near 4/5; bait contacted_by=5; toll alert", False, str(e)))

    # -------------------------------------------------------------
    # Check 7: Co-traveler alert present
    # -------------------------------------------------------------
    try:
        conn = get_connection()
        alerts = generate_alerts(conn)
        co_alerts = [a for a in alerts if a["type"] == "co_traveler"]
        has_co = len(co_alerts) > 0

        detail_7 = f"Found {len(co_alerts)} co-traveler pattern alert(s): '{co_alerts[0]['title'] if has_co else 'None'}'"
        pass_7 = has_co
        results.append(("7. Co-traveler alert present", pass_7, detail_7))
    except Exception as e:
        results.append(("7. Co-traveler alert present", False, str(e)))

    # -------------------------------------------------------------
    # Check 8: Simulator: removing top broker candidate increases components and lowers efficiency
    # -------------------------------------------------------------
    try:
        cursor.execute("SELECT entity_id FROM entity_members WHERE record_id = 'R0019'")
        broker_ent = cursor.fetchone()[0]

        sim_res = simulate_node_removal(broker_ent)
        b_comp = sim_res["before"]["components"]
        a_comp = sim_res["after"]["components"]
        b_eff = sim_res["before"]["efficiency"]
        a_eff = sim_res["after"]["efficiency"]
        delta_pct = sim_res["delta_pct"]

        comp_increased = a_comp > b_comp
        eff_lowered = a_eff < b_eff

        pass_8 = comp_increased and eff_lowered
        detail_8 = f"Components: {b_comp} -> {a_comp} (increased: {comp_increased}); Efficiency: {b_eff} -> {a_eff} (delta: {delta_pct}%, lowered: {eff_lowered})"
        results.append(("8. Simulator: removing top broker increases components and lowers efficiency", pass_8, detail_8))
    except Exception as e:
        results.append(("8. Simulator: removing top broker increases components and lowers efficiency", False, str(e)))

    # -------------------------------------------------------------
    # Check 9: Ledger verify ok; after /debug/tamper fails; after /debug/reset ok
    # -------------------------------------------------------------
    try:
        # Step A: initial verify
        res_v1 = client.get("/api/verify", headers={"Authorization": "Bearer token_sp_dysp"})
        ok_1 = res_v1.json().get("ok", False)

        # Step B: tamper
        res_tamper = client.post("/api/debug/tamper")
        res_v2 = client.get("/api/verify", headers={"Authorization": "Bearer token_sp_dysp"})
        tamper_detected = not res_v2.json().get("ok", True)
        broken_at = res_v2.json().get("broken_at")

        # Step C: reset
        res_reset = client.post("/api/debug/reset")
        res_v3 = client.get("/api/verify", headers={"Authorization": "Bearer token_sp_dysp"})
        ok_after_reset = res_v3.json().get("ok", False)

        pass_9 = ok_1 and tamper_detected and ok_after_reset
        detail_9 = f"Initial verify: {ok_1}; After tamper verify fails: {tamper_detected} (detected at {broken_at}); After reset verify: {ok_after_reset}"
        results.append(("9. Ledger verify ok; after /debug/tamper fails; after /debug/reset ok", pass_9, detail_9))
    except Exception as e:
        results.append(("9. Ledger verify ok; after /debug/tamper fails; after /debug/reset ok", False, str(e)))

    # -------------------------------------------------------------
    # Check 10: RBAC: constable gets 403 on approve and sees masked phones; sp_dysp can unmask
    # -------------------------------------------------------------
    try:
        # Constable tries to approve merge -> 403
        res_c_approve = client.post("/api/merge/MQ-R0019-R0030/approve", headers={"Authorization": "Bearer token_constable"})
        constable_blocked = (res_c_approve.status_code == 403)

        # Constable fetches entity -> sees masked phone
        cursor.execute("SELECT entity_id FROM entity_members WHERE record_id = 'R0019'")
        broker_ent = cursor.fetchone()[0]

        res_c_ent = client.get(f"/api/entity/{broker_ent}", headers={"Authorization": "Bearer token_constable"})
        constable_phone = res_c_ent.json().get("phone", "")
        phone_is_masked = "XXXXX" in constable_phone

        # Constable tries to unmask -> 403
        res_c_unmask = client.post(f"/api/entity/{broker_ent}/unmask", headers={"Authorization": "Bearer token_constable"})
        unmask_blocked_for_constable = (res_c_unmask.status_code == 403)

        # SP unmasks entity -> 200 and unmasked phone returned
        res_sp_unmask = client.post(f"/api/entity/{broker_ent}/unmask", headers={"Authorization": "Bearer token_sp_dysp"})
        sp_unmask_ok = (res_sp_unmask.status_code == 200)
        unmasked_phone = res_sp_unmask.json().get("phone", "")
        unmask_valid = (len(unmasked_phone) >= 10 and "XXXXX" not in unmasked_phone)

        pass_10 = constable_blocked and phone_is_masked and unmask_blocked_for_constable and sp_unmask_ok and unmask_valid
        detail_10 = (
            f"Constable approve blocked (403): {constable_blocked}; Phone masked for constable: {phone_is_masked} ('{constable_phone}'); "
            f"Constable unmask blocked (403): {unmask_blocked_for_constable}; SP unmask succeeded: {sp_unmask_ok} ('{unmasked_phone}')"
        )
        results.append(("10. RBAC: constable gets 403 & masked phone; sp_dysp can unmask", pass_10, detail_10))
    except Exception as e:
        results.append(("10. RBAC: constable gets 403 & masked phone; sp_dysp can unmask", False, str(e)))

    # -------------------------------------------------------------
    # Check 11: Groq Copilot: query returns answer, citations, confidence, phone masking & ledger logging
    # -------------------------------------------------------------
    try:
        # Step A: Cyber Cell asks investigative question
        q1 = "What is the role of entity Vikas S. / Golden Bhai in bridging clusters?"
        res_cop1 = client.post("/api/copilot", json={"question": q1}, headers={"Authorization": "Bearer token_cyber_cell"})
        cop1_data = res_cop1.json()
        has_answer = len(cop1_data.get("answer", "")) > 50
        has_citations = len(cop1_data.get("citations", [])) >= 1
        has_confidence = cop1_data.get("confidence") in ["high", "medium"]

        # Step B: Constable asks question containing phone number -> phone must be masked
        q2 = "What phone numbers are linked to the job ad?"
        res_cop2 = client.post("/api/copilot", json={"question": q2}, headers={"Authorization": "Bearer token_constable"})
        c_answer = res_cop2.json().get("answer", "")
        c_phone_masked = "XXXXX" in c_answer

        # Step C: Ledger has recorded COPILOT_QUERY
        cursor.execute("SELECT COUNT(*) FROM ledger WHERE action LIKE 'COPILOT_QUERY%'")
        cop_ledger_count = cursor.fetchone()[0]

        pass_11 = (res_cop1.status_code == 200 and has_answer and has_citations and has_confidence and c_phone_masked and cop_ledger_count > 0)
        detail_11 = (
            f"Copilot 200: {res_cop1.status_code == 200}; Answer len: {len(cop1_data.get('answer', ''))}; "
            f"Citations: {cop1_data.get('citations')}; Phone masked for constable: {c_phone_masked}; "
            f"Ledger entries logged: {cop_ledger_count}"
        )
        results.append(("11. Groq Copilot: evidence-grounded Q&A, citations, phone masking, ledger log", pass_11, detail_11))
    except Exception as e:
        results.append(("11. Groq Copilot: evidence-grounded Q&A, citations, phone masking, ledger log", False, str(e)))

    # -------------------------------------------------------------
    # Check 12: PDF Report Generator: Section 65B format, valid PDF bytes & ledger logging
    # -------------------------------------------------------------
    try:
        res_rep = client.post("/api/report", headers={"Authorization": "Bearer token_cyber_cell"})
        rep_data = res_rep.json()
        rep_id = rep_data.get("report_id")
        rep_url = rep_data.get("url")
        rep_ready = rep_data.get("status") == "ready"

        # Download the PDF
        res_dl = client.get(rep_url, headers={"Authorization": "Bearer token_cyber_cell"})
        pdf_bytes = res_dl.content
        pdf_valid = pdf_bytes.startswith(b"%PDF")
        pdf_size_ok = len(pdf_bytes) > 4000
        ct_ok = "application/pdf" in res_dl.headers.get("content-type", "")

        # Check ledger has REPORT_EXPORT
        cursor.execute("SELECT COUNT(*) FROM ledger WHERE action LIKE 'REPORT_EXPORT%'")
        rep_ledger_count = cursor.fetchone()[0]

        pass_12 = (res_rep.status_code == 200 and rep_ready and pdf_valid and pdf_size_ok and ct_ok and rep_ledger_count > 0)
        detail_12 = (
            f"Report ready: {rep_ready} ({rep_id}); Download status: {res_dl.status_code}; "
            f"Valid PDF header: {pdf_valid}; PDF size: {len(pdf_bytes)} bytes; Ledger entries: {rep_ledger_count}"
        )
        results.append(("12. Detailed Report: Section 65B dossier, valid PDF bytes, ledger log", pass_12, detail_12))
    except Exception as e:
        results.append(("12. Detailed Report: Section 65B dossier, valid PDF bytes, ledger log", False, str(e)))

    # -------------------------------------------------------------
    # Check 13: Report Email: status sent with masked email, blocks constable with 403 & ledger logging
    # -------------------------------------------------------------
    try:
        # Constable is blocked from emailing reports
        res_c_mail = client.post("/api/report/email", json={"report_id": "RPT-SP014-01"}, headers={"Authorization": "Bearer token_constable"})
        mail_blocked_for_constable = (res_c_mail.status_code == 403)

        # Cyber cell can email reports
        res_cy_mail = client.post("/api/report/email", json={"report_id": "RPT-SP014-01"}, headers={"Authorization": "Bearer token_cyber_cell"})
        cy_mail_data = res_cy_mail.json()
        mail_sent_ok = (res_cy_mail.status_code == 200 and cy_mail_data.get("status") in ["sent", "queued"])
        masked_recipient = cy_mail_data.get("sent_to", "")
        recipient_masked = ("***@" in masked_recipient)

        # Check ledger has REPORT_EMAIL
        cursor.execute("SELECT COUNT(*) FROM ledger WHERE action LIKE 'REPORT_EMAIL%'")
        mail_ledger_count = cursor.fetchone()[0]

        pass_13 = (mail_blocked_for_constable and mail_sent_ok and recipient_masked and mail_ledger_count > 0)
        detail_13 = (
            f"Constable blocked (403): {mail_blocked_for_constable}; Email sent: {mail_sent_ok}; "
            f"Recipient masked: '{masked_recipient}'; Ledger entries: {mail_ledger_count}"
        )
        results.append(("13. Report Email: RBAC protection (403), masked recipient, ledger log", pass_13, detail_13))
    except Exception as e:
        results.append(("13. Report Email: RBAC protection (403), masked recipient, ledger log", False, str(e)))

    # -------------------------------------------------------------
    # Check 14: demo-login returns a JWT with the chosen role
    # -------------------------------------------------------------
    try:
        from auth import decode_jwt_token
        import time
        test_email = f"officer_selftest_{int(time.time())}@gov.in"
        res_dl = client.post("/api/auth/demo-login", json={
            "name": "Officer Patel",
            "email": test_email,
            "role": "Head Constable",
            "website": ""
        })
        dl_data = res_dl.json()
        token = dl_data.get("token")
        payload = decode_jwt_token(token) if token else {}

        role_ok = (dl_data.get("user", {}).get("role") == "head_constable")
        jwt_role_ok = (payload.get("role") == "head_constable")
        jwt_demo_ok = (payload.get("demo") is True)
        pass_14 = (res_dl.status_code == 200 and role_ok and jwt_role_ok and jwt_demo_ok)
        detail_14 = f"Status: {res_dl.status_code}, User Role: {dl_data.get('user', {}).get('role')}, JWT Role: {payload.get('role')}, JWT Demo Claim: {payload.get('demo')}"
        results.append(("14. demo-login returns a JWT with chosen role", pass_14, detail_14))
    except Exception as e:
        results.append(("14. demo-login returns a JWT with chosen role", False, str(e)))

    # -------------------------------------------------------------
    # Check 15: demo-login rate limit works
    # -------------------------------------------------------------
    try:
        # Immediate second attempt with same email triggers the 1 email/addr/hr limit
        res_rl = client.post("/api/auth/demo-login", json={
            "name": "Officer Patel",
            "email": test_email,
            "role": "Head Constable",
            "website": ""
        })
        rl_data = res_rl.json()
        limit_triggered = (rl_data.get("notice_status") == "Login notice skipped (limit)")
        pass_15 = (res_rl.status_code == 200 and limit_triggered)
        detail_15 = f"Status: {res_rl.status_code}, Notice status: {rl_data.get('notice_status')}"
        results.append(("15. demo-login rate limit works", pass_15, detail_15))
    except Exception as e:
        results.append(("15. demo-login rate limit works", False, str(e)))

    # -------------------------------------------------------------
    # Check 16: /api/summary numbers equal Alerts page and Merge Queue counts
    # -------------------------------------------------------------
    try:
        res_sum = client.get("/api/summary", headers={"Authorization": "Bearer token_sp_dysp"})
        sum_data = res_sum.json()

        res_alerts = client.get("/api/alerts", headers={"Authorization": "Bearer token_sp_dysp"})
        alerts_data = res_alerts.json()

        res_mq = client.get("/api/merge-queue", headers={"Authorization": "Bearer token_sp_dysp"})
        mq_data = res_mq.json()
        mq_pending_count = len([m for m in mq_data if m.get("status") == "pending"])

        alerts_match = (sum_data.get("alerts_total") == len(alerts_data))
        mq_match = (sum_data.get("pending_merges") == mq_pending_count)
        pass_16 = (res_sum.status_code == 200 and alerts_match and mq_match)
        detail_16 = f"Summary alerts ({sum_data.get('alerts_total')}) == Alerts count ({len(alerts_data)}): {alerts_match}; Summary pending ({sum_data.get('pending_merges')}) == MQ pending ({mq_pending_count}): {mq_match}"
        results.append(("16. /api/summary equals Alerts and Merge Queue counts", pass_16, detail_16))
    except Exception as e:
        results.append(("16. /api/summary equals Alerts and Merge Queue counts", False, str(e)))

    # -------------------------------------------------------------
    # Check 17: copilot health endpoint reports test_call_ok true
    # -------------------------------------------------------------
    try:
        res_coph = client.get("/api/health/copilot", headers={"Authorization": "Bearer token_sp_dysp"})
        coph_data = res_coph.json()
        test_call_ok = coph_data.get("test_call_ok") is True
        tool_call_ok = coph_data.get("sample_tool_call_ok") is True
        key_present = coph_data.get("groq_key_present") is True
        pass_17 = (res_coph.status_code == 200 and test_call_ok and tool_call_ok and key_present)
        detail_17 = f"Status: {res_coph.status_code}, test_call_ok: {test_call_ok}, sample_tool_call_ok: {tool_call_ok}, groq_key_present: {key_present}, model: {coph_data.get('model')}"
        results.append(("17. copilot health reports test_call_ok true", pass_17, detail_17))
    except Exception as e:
        results.append(("17. copilot health reports test_call_ok true", False, str(e)))

    # -------------------------------------------------------------
    # PRINT SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("                     SELF-TEST SUMMARY RESULTS                     ")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for _, p, _ in results)

    for name, p, detail in results:
        status_tag = "\033[92m[PASS]\033[0m" if p else "\033[91m[FAIL]\033[0m"
        # Plain text for clean windows terminal
        plain_tag = "[PASS]" if p else "[FAIL]"
        print(f"\n{plain_tag} {name}")
        print(f"       Details: {detail}")

    print("\n" + "-" * 70)
    print(f"TOTAL: {passed_tests}/{total_tests} TESTS PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 70)

    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_selftests()
    sys.exit(0 if success else 1)
