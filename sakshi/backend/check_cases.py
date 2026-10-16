import os
import sys
from fastapi.testclient import TestClient

# Ensure backend dir is on path
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from main import app
from auth import create_jwt_token
from db import get_connection

def run_tests():
    client = TestClient(app)
    results = {}

    # 1. Constable gets 403 on SP-021
    try:
        c_token = create_jwt_token("constable@demo.in", "constable", "Constable Verma")
        resp = client.get("/api/summary", headers={"Authorization": f"Bearer {c_token}", "X-Case-Id": "SP-021"})
        if resp.status_code == 403:
            results["constable gets 403 on SP-021"] = "PASS"
        else:
            results["constable gets 403 on SP-021"] = f"FAIL (status {resp.status_code})"
    except Exception as e:
        results["constable gets 403 on SP-021"] = f"FAIL ({e})"

    # 2. Blind match leaks no identifiers
    try:
        resp = client.get("/api/cross-case/links", headers={"Authorization": f"Bearer {c_token}"})
        data = resp.json()
        links = data.get("links", [])
        leaked = False
        allowed_blind_keys = {"id", "blind", "message", "can_request_access"}
        forbidden_substrings = ["97378", "87710", "ACC0029", "81850", "phone", "account"]

        for l in links:
            if not l.get("blind"):
                leaked = True
                break
            # Check keys
            if set(l.keys()) - allowed_blind_keys:
                leaked = True
                break
            # Check values
            for v in l.values():
                for sub in forbidden_substrings:
                    if sub in str(v):
                        leaked = True
                        break

        if len(links) > 0 and not leaked:
            results["blind match leaks no identifiers"] = "PASS"
        else:
            results["blind match leaks no identifiers"] = f"FAIL (links={len(links)}, leaked={leaked})"
    except Exception as e:
        results["blind match leaks no identifiers"] = f"FAIL ({e})"

    # 3. IG sees the planted overlaps
    try:
        ig_token = create_jwt_token("ig@demo.in", "ig", "Inspector General Sharma")
        resp = client.get("/api/cross-case/links", headers={"Authorization": f"Bearer {ig_token}"})
        data = resp.json()
        ig_links = data.get("links", [])
        
        # Verify 3 planted active overlaps: ad phone / bait, pass-through account ACC0029, broker phone
        has_phone = any(l.get("identifier_type") == "phone" for l in ig_links)
        has_account = any(l.get("identifier_type") == "account" for l in ig_links)
        
        if len(ig_links) >= 3 and has_phone and has_account:
            results["ig sees the planted overlaps"] = "PASS"
        else:
            results["ig sees the planted overlaps"] = f"FAIL (links={len(ig_links)}, has_phone={has_phone}, has_account={has_account})"
    except Exception as e:
        results["ig sees the planted overlaps"] = f"FAIL ({e})"

    # 4. Decoy appears only under suppressed
    try:
        suppressed = data.get("suppressed", [])
        decoy_in_suppressed = any(s.get("identifier") == "8185067165" or s.get("reason") == "common identifier" for s in suppressed)
        decoy_in_active = any("8185067165" in str(l) for l in ig_links)
        
        if decoy_in_suppressed and not decoy_in_active:
            results["the decoy appears only under suppressed"] = "PASS"
        else:
            results["the decoy appears only under suppressed"] = f"FAIL (in_suppressed={decoy_in_suppressed}, in_active={decoy_in_active})"
    except Exception as e:
        results["the decoy appears only under suppressed"] = f"FAIL ({e})"

    # 5. sp_dysp without access to both cases cannot approve
    try:
        sp_token = create_jwt_token("sp@demo.in", "sp_dysp", "SP Rajesh Kumar")
        # Get one link id from main db
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM cross_case_links WHERE case_a = 'SP-014' AND case_b = 'SP-021' LIMIT 1")
        row = cur.fetchone()
        if not row:
            results["sp_dysp without access to both cases cannot approve"] = "FAIL (no cross-case link found)"
        else:
            link_id = row[0]
            resp = client.post(
                f"/api/cross-case/links/{link_id}/decision",
                json={"decision": "approve"},
                headers={"Authorization": f"Bearer {sp_token}"}
            )
            if resp.status_code == 403:
                results["sp_dysp without access to both cases cannot approve"] = "PASS"
            else:
                results["sp_dysp without access to both cases cannot approve"] = f"FAIL (status {resp.status_code})"
    except Exception as e:
        results["sp_dysp without access to both cases cannot approve"] = f"FAIL ({e})"

    # 6. SP-014 summary counts unchanged (63 entities, 400 calls, 150 transactions)
    try:
        resp = client.get("/api/summary", headers={"Authorization": f"Bearer {sp_token}", "X-Case-Id": "SP-014"})
        s_data = resp.json()
        ents = s_data.get("entities")
        calls = s_data.get("calls")
        txns = s_data.get("transactions")

        if ents == 63 and calls == 400 and txns == 150:
            results["SP-014 summary counts unchanged (63 entities, 400 calls, 150 transactions)"] = "PASS"
        else:
            results["SP-014 summary counts unchanged (63 entities, 400 calls, 150 transactions)"] = f"FAIL (ents={ents}, calls={calls}, txns={txns})"
    except Exception as e:
        results["SP-014 summary counts unchanged (63 entities, 400 calls, 150 transactions)"] = f"FAIL ({e})"

    # Output table
    all_pass = True
    print("\n--- SAKSHI CHECK CASES RESULTS ---")
    for check_name, status in results.items():
        print(f"[{status}] {check_name}")
        if not status.startswith("PASS"):
            all_pass = False

    return all_pass

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
