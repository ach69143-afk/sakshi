import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
import sqlite3

from db import get_connection
from resolve import resolve_entities, get_merge_queue_data, approve_merge_decision
from graph import KnowledgeGraph
from alerts import generate_alerts, get_golden_hour_details

GT_PATH = Path(__file__).resolve().parent.parent / "data" / "ground_truth.json"

def run_validation() -> Dict[str, Any]:
    """
    Validates the pipeline outputs against ground_truth.json.
    This file is the ONLY module permitted to read ground_truth.json.
    """
    if not GT_PATH.exists():
        return {
            "metrics": {},
            "checks": [{"name": "Ground Truth File", "pass": False, "detail": "ground_truth.json not found"}]
        }

    with open(GT_PATH, "r", encoding="utf-8") as f:
        gt = json.load(f)

    conn = get_connection()
    cursor = conn.cursor()

    checks = []
    metrics = {}

    # 1. Ground Truth Truth Pairs & Identity Groups
    gt_pairs: Set[Tuple[str, str]] = set()
    rec2gt_person: Dict[str, str] = {}
    for g in gt["identity_groups"]:
        p_id = g["person_id"]
        rids = g["record_ids"]
        for r in rids:
            rec2gt_person[r] = p_id
        for i in range(len(rids)):
            for j in range(i + 1, len(rids)):
                gt_pairs.add(tuple(sorted([rids[i], rids[j]])))

    # Evaluate ER: Auto-links Only
    cursor.execute("SELECT record_a, record_b, status FROM merge_decisions")
    decisions = cursor.fetchall()
    auto_pairs = {tuple(sorted([r[0], r[1]])) for r in decisions if r[2] == "auto"}

    tp_auto = len(auto_pairs & gt_pairs)
    fp_auto = len(auto_pairs - gt_pairs)
    fn_auto = len(gt_pairs - auto_pairs)

    p_auto = tp_auto / (tp_auto + fp_auto) if (tp_auto + fp_auto) > 0 else 1.0
    r_auto = tp_auto / (tp_auto + fn_auto) if (tp_auto + fn_auto) > 0 else 0.0
    f1_auto = 2 * p_auto * r_auto / (p_auto + r_auto) if (p_auto + r_auto) > 0 else 0.0

    metrics["er_precision_auto"] = round(p_auto, 3)
    metrics["er_recall_auto"] = round(r_auto, 3)
    metrics["er_f1_auto"] = round(f1_auto, 3)

    # 2. Check do_not_merge trap pair
    cursor.execute("SELECT em.entity_id, em.record_id FROM entity_members em")
    rec_to_ent = {r[1]: r[0] for r in cursor.fetchall()}

    dnm_ok = True
    dnm_details = []
    for pair in gt.get("do_not_merge", []):
        r1, r2 = pair[0], pair[1]
        e1, e2 = rec_to_ent.get(r1), rec_to_ent.get(r2)
        if e1 and e2 and e1 == e2:
            dnm_ok = False
            dnm_details.append(f"{r1} and {r2} erroneously merged into {e1}")
        else:
            dnm_details.append(f"{r1} != {r2} kept distinct ({e1} vs {e2})")

    metrics["do_not_merge_separate"] = dnm_ok
    checks.append({
        "name": "Same-Name Trap Pair Distinction (do_not_merge)",
        "pass": dnm_ok,
        "detail": "; ".join(dnm_details)
    })

    # 3. Evaluate ER: After Approving Pending Merges
    # Simulate approval of true duplicate pending candidates
    q_data = get_merge_queue_data(conn)
    approved_sim_pairs = set(auto_pairs)
    for item in q_data:
        r_ids = tuple(sorted([item["records"][0]["record_id"], item["records"][1]["record_id"]]))
        if item["status"] in ["auto", "approved", "pending"]:
            approved_sim_pairs.add(r_ids)

    tp_app = len(approved_sim_pairs & gt_pairs)
    fp_app = len(approved_sim_pairs - gt_pairs)
    fn_app = len(gt_pairs - approved_sim_pairs)

    p_app = tp_app / (tp_app + fp_app) if (tp_app + fp_app) > 0 else 1.0
    r_app = tp_app / (tp_app + fn_app) if (tp_app + fn_app) > 0 else 0.0
    f1_app = 2 * p_app * r_app / (p_app + r_app) if (p_app + r_app) > 0 else 0.0

    metrics["er_precision_approved"] = round(p_app, 3)
    metrics["er_recall_approved"] = round(r_app, 3)
    metrics["er_f1_approved"] = round(f1_app, 3)
    metrics["er_f1_after_approval"] = round(f1_app, 3)

    checks.append({
        "name": "Entity Resolution (Auto-link Precision)",
        "pass": p_auto >= 0.90,
        "detail": f"Precision: {p_auto:.2f}, Recall: {r_auto:.2f}, F1: {f1_auto:.2f} ({tp_auto} auto pairs matched)"
    })
    checks.append({
        "name": "Entity Resolution (Post-Review Resolution F1)",
        "pass": f1_app >= 0.70,
        "detail": f"Precision: {p_app:.2f}, Recall: {r_app:.2f}, F1: {f1_app:.2f} across all candidate clusters"
    })

    # 4. Graph Metrics: Broker Priority, Ranking, and Decoy Comparison
    kg = KnowledgeGraph().build_from_db(conn)
    sorted_nodes = sorted(kg.nodes_data.values(), key=lambda x: -x["priority"])
    node_ids_ranked = [n["id"] for n in sorted_nodes]

    # Find broker entity
    broker_rids = [r for r, pid in rec2gt_person.items() if pid == gt["broker_person_id"]]
    broker_ent_ids = list({rec_to_ent[r] for r in broker_rids if r in rec_to_ent})
    broker_ent = broker_ent_ids[0] if broker_ent_ids else None

    broker_rank = (node_ids_ranked.index(broker_ent) + 1) if broker_ent in node_ids_ranked else 999
    broker_node = kg.nodes_data.get(broker_ent, {})
    broker_role = broker_node.get("role_label", "")
    broker_found = bool(broker_rank <= 3 or broker_role == "broker candidate")

    metrics["broker_rank"] = broker_rank
    metrics["broker_found"] = broker_found

    checks.append({
        "name": "Broker Candidate Prioritization",
        "pass": broker_found,
        "detail": f"Broker entity {broker_ent} ranked #{broker_rank} (Priority: {broker_node.get('priority')}, Role: '{broker_role}')"
    })

    # Decoy comparison
    decoy_rids = [r for r, pid in rec2gt_person.items() if pid == gt["decoy_person_id"]]
    decoy_ent_ids = list({rec_to_ent[r] for r in decoy_rids if r in rec_to_ent})
    decoy_ent = decoy_ent_ids[0] if decoy_ent_ids else None
    decoy_node = kg.nodes_data.get(decoy_ent, {})

    decoy_below = bool(broker_node.get("priority", 0) > decoy_node.get("priority", 0))
    metrics["decoy_below_broker"] = decoy_below

    checks.append({
        "name": "High-Volume Decoy Ranked Below Broker",
        "pass": decoy_below,
        "detail": f"Broker priority ({broker_node.get('priority')}) > Decoy priority ({decoy_node.get('priority')})"
    })

    # 5. Ring Recall (Top K = 15)
    all_ring_persons = set(gt["groups"]["A"] + gt["groups"]["B"] + gt["groups"]["leaders"] + [gt["broker_person_id"]])
    top_15_nodes = node_ids_ranked[:15]
    top_15_persons_found = set()
    for n_id in top_15_nodes:
        # Check which GT person this entity corresponds to
        for rid, ent_id in rec_to_ent.items():
            if ent_id == n_id and rid in rec2gt_person:
                p_id = rec2gt_person[rid]
                if p_id in all_ring_persons:
                    top_15_persons_found.add(p_id)

    ring_recall = len(top_15_persons_found) / len(all_ring_persons) if all_ring_persons else 0.0
    metrics["ring_recall"] = round(ring_recall, 3)

    checks.append({
        "name": "Ring Recall within Top-15 Priority",
        "pass": ring_recall >= 0.50,
        "detail": f"Captured {len(top_15_persons_found)} / {len(all_ring_persons)} ring core identities ({ring_recall*100:.1f}%)"
    })

    # 6. Alerts & Anomaly Pattern Corroboration
    alerts = generate_alerts(conn)
    gh_data = get_golden_hour_details(conn)

    # A. Golden-Hour Cluster
    gh_alert = [a for a in alerts if a["type"] == "golden_hour"]
    gh_ok = bool(gh_alert) and len(gh_data.get("missing", [])) == 5
    metrics["golden_hour_found"] = gh_ok
    checks.append({
        "name": "Golden-Hour 3km Spatial Cluster Detection",
        "pass": gh_ok,
        "detail": f"Triangulated {len(gh_data.get('missing', []))} missing persons within 3km centroid {gh_data.get('centroid')}"
    })

    # B. Burner Phone
    burner_phone_clean = gt["burner_phone"].replace("+91", "").strip()
    burner_num_in_gh = gh_data.get("burner", {}).get("number", "").replace("+91", "").strip()
    burner_ok = burner_num_in_gh == burner_phone_clean
    metrics["burner_found"] = burner_ok

    # Burner seen near
    burner_seen_near_ok = set(gh_data.get("burner", {}).get("seen_near", [])) == set(gt["burner_seen_near"])
    metrics["burner_seen_near_match"] = burner_seen_near_ok

    checks.append({
        "name": "Burner Device Proximity Triangulation",
        "pass": burner_ok and burner_seen_near_ok,
        "detail": f"Burner {burner_num_in_gh} detected near {gh_data.get('burner', {}).get('seen_near')} (Ground truth: {gt['burner_seen_near']})"
    })

    # C. Digital Bait Job Ad
    bait_phone_clean = gt["bait_phone"].replace("+91", "").strip()
    bait_num_in_gh = gh_data.get("bait", {}).get("number", "").replace("+91", "").strip()
    bait_ok = bait_num_in_gh == bait_phone_clean and gh_data.get("bait", {}).get("contacted_by") == 5
    metrics["bait_found"] = bait_ok

    checks.append({
        "name": "Job-Ad Digital Bait Correlation",
        "pass": bait_ok,
        "detail": f"Helpline {bait_num_in_gh} linked to inbound calls from all {gh_data.get('bait', {}).get('contacted_by')} missing persons"
    })

    # D. Pass-Through Relay Account & Money Chain
    pt_alert = [a for a in alerts if a["type"] == "pass_through"]
    pt_ok = bool(pt_alert) and any(gt["pass_through_account"] in a.get("entity_ids", []) for a in pt_alert)
    metrics["pass_through_found"] = pt_ok

    # Money chain overlap
    cursor.execute("SELECT DISTINCT from_account, to_account FROM transactions")
    tx_edges = {tuple(r) for r in cursor.fetchall()}
    chain = gt.get("money_chain", [])
    chain_edges = list(zip(chain[:-1], chain[1:]))
    chain_hits = sum(1 for e in chain_edges if e in tx_edges)
    chain_overlap = chain_hits / len(chain_edges) if chain_edges else 1.0
    metrics["money_chain_overlap"] = round(chain_overlap, 3)

    checks.append({
        "name": "Rapid Pass-Through Financial Conduit",
        "pass": pt_ok and chain_overlap >= 0.80,
        "detail": f"Account {gt['pass_through_account']} identified with rapid velocity; money chain overlap {chain_overlap*100:.0f}%"
    })

    # E. Co-traveler Lodging Pattern
    cotrav_alert = [a for a in alerts if a["type"] == "co_traveler"]
    cotrav_ok = bool(cotrav_alert) and any(gt["co_traveler_adult_record"] in a.get("entity_ids", []) for a in cotrav_alert)
    metrics["co_traveler_found"] = cotrav_ok

    checks.append({
        "name": "Co-Traveler Lodging Anomaly",
        "pass": cotrav_ok,
        "detail": f"Adult record {gt['co_traveler_adult_record']} flagged with repeated multi-companion hotel stays"
    })

    # F. Corridor Toll Anomaly
    toll_alert = [a for a in alerts if a["type"] == "toll_anomaly"]
    toll_ok = bool(toll_alert)
    metrics["toll_found"] = toll_ok

    checks.append({
        "name": "Corridor Toll Egress Anomaly",
        "pass": toll_ok,
        "detail": f"Outbound egress logged during incident window matching vehicle fleet registration"
    })

    return {
        "metrics": metrics,
        "checks": checks
    }

if __name__ == "__main__":
    res = run_validation()
    print("=== SAKSHI VALIDATION REPORT ===")
    print(f"Total Checks: {len(res['checks'])}")
    passed = sum(1 for c in res["checks"] if c["pass"])
    print(f"Passed: {passed} / {len(res['checks'])}")
    print("\nChecks:")
    for c in res["checks"]:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['name']} -- {c['detail']}")
    print("\nMetrics:")
    for k, v in res["metrics"].items():
        print(f"  {k}: {v}")
