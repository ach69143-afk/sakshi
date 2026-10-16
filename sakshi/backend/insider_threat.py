import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List

from ledger import record_action

BASELINE = {
    "unmask": {"mean": 0.5, "std": 0.8},
    "copilot": {"mean": 2.5, "std": 1.5},
    "cross_case": {"mean": 0.2, "std": 0.5},
    "off_hours": {"mean": 0.3, "std": 0.6},
    "failed_logins": {"mean": 0.2, "std": 0.4}
}

def detect_insider_threats(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Per user per day features:
    - unmask count
    - copilot query count
    - cross-case queries outside assignment
    - off-hours actions (22:00 to 05:00)
    - failed logins
    Detection: transparent rules plus z-score against synthetic baseline.
    Label: "rules + z-score on synthetic ledger data" (no Isolation Forest).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT idx, prev_hash, hash, action, payload_json, ts FROM ledger ORDER BY idx ASC")
    rows = cursor.fetchall()

    user_day_metrics: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        lid, p_hash, c_hash, action, payload_str, ts = r
        try:
            payload = json.loads(payload_str) if payload_str else {}
        except Exception:
            payload = {}

        # Resolve user
        user = (
            payload.get("user") or 
            payload.get("email") or 
            payload.get("authorized_officer") or 
            payload.get("officer") or 
            "system@demo.in"
        ).lower().strip()

        # Parse date and hour
        date_str = ts[:10] if len(ts) >= 10 else "2026-09-24"
        try:
            hour = int(ts[11:13])
        except Exception:
            hour = 12

        key = f"{user}__{date_str}"
        if key not in user_day_metrics:
            user_day_metrics[key] = {
                "user": user,
                "date": date_str,
                "unmask_count": 0,
                "copilot_count": 0,
                "cross_case_count": 0,
                "off_hours_count": 0,
                "failed_logins": 0,
                "simulated_count": 0,
                "block_ids": [],
                "latest_ts": ts
            }

        m = user_day_metrics[key]
        m["block_ids"].append(f"BLK-{lid:02d}")
        m["latest_ts"] = ts

        act_low = action.lower()
        if "unmask" in act_low or "phone_unmasked" in act_low:
            m["unmask_count"] += 1
        if "copilot" in act_low:
            m["copilot_count"] += 1
        if "cross_case" in act_low or "cross-case" in act_low or "unauthorized access" in act_low:
            m["cross_case_count"] += 1
        if hour >= 22 or hour < 5:
            m["off_hours_count"] += 1
        if "failed" in act_low or "denied" in act_low or "invalid" in act_low:
            m["failed_logins"] += 1
        if payload.get("simulated"):
            m["simulated_count"] += 1

    alerts = []
    alert_idx = 1

    for key, m in user_day_metrics.items():
        user = m["user"]
        day = m["date"]
        unmask_c = m["unmask_count"]
        copilot_c = m["copilot_count"]
        cross_c = m["cross_case_count"]
        off_h_c = m["off_hours_count"]
        failed_c = m["failed_logins"]
        sim_c = m["simulated_count"]

        # Compute z-scores
        z_unmask = max(0.0, (unmask_c - BASELINE["unmask"]["mean"]) / BASELINE["unmask"]["std"])
        z_copilot = max(0.0, (copilot_c - BASELINE["copilot"]["mean"]) / BASELINE["copilot"]["std"])
        z_cross = max(0.0, (cross_c - BASELINE["cross_case"]["mean"]) / BASELINE["cross_case"]["std"])
        z_off = max(0.0, (off_h_c - BASELINE["off_hours"]["mean"]) / BASELINE["off_hours"]["std"])
        z_failed = max(0.0, (failed_c - BASELINE["failed_logins"]["mean"]) / BASELINE["failed_logins"]["std"])
        composite_z = round((z_unmask + z_copilot + z_cross + z_off + z_failed) / math.sqrt(5), 2)

        # Transparent rules
        rule_triggered = (
            sim_c > 0 or
            composite_z >= 2.5 or
            unmask_c >= 4 or
            off_h_c >= 3 or
            failed_c >= 3
        )

        if rule_triggered:
            reasons = []
            if sim_c > 0:
                reasons.append(f"{sim_c} simulated adversary test actions")
            if unmask_c >= 2:
                reasons.append(f"{unmask_c} evidentiary unmask operations (z={z_unmask:.1f})")
            if off_h_c >= 2:
                reasons.append(f"{off_h_c} actions during off-hours 22:00-05:00 (z={z_off:.1f})")
            if cross_c >= 1:
                reasons.append(f"{cross_c} cross-case queries outside assignment (z={z_cross:.1f})")
            if copilot_c >= 3:
                reasons.append(f"{copilot_c} copilot intelligence queries (z={z_copilot:.1f})")
            if failed_c >= 2:
                reasons.append(f"{failed_c} authentication anomalies (z={z_failed:.1f})")

            alerts.append({
                "id": f"ALT-INSIDER-{alert_idx:02d}",
                "type": "insider_threat",
                "severity": "critical",
                "title": "Insider Threat Detected (rules + z-score on synthetic ledger data)",
                "explanation": (
                    f"Anomalous operational behavior detected for officer '{user}' on {day}: "
                    f"{', '.join(reasons)}. Evaluated via rules + z-score on synthetic ledger data."
                ),
                "entity_ids": [user],
                "evidence_ids": m["block_ids"][-5:],
                "ts": m["latest_ts"],
                "z_score": composite_z,
                "detection_method": "rules + z-score on synthetic ledger data"
            })
            alert_idx += 1

    return alerts

def simulate_insider_behavior(conn: sqlite3.Connection, user_email: str = "constable@demo.in") -> Dict[str, Any]:
    """Appends clearly tagged entries with payload simulated=true for stage presentation."""
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts_off_hours = f"{now_date}T23:14:22Z"

    entries = [
        ("PHONE_UNMASKED (Evidentiary phone unmasked for entity ENT-0019)", {"case_id": "SP-014", "user": user_email, "simulated": True, "target": "ENT-0019"}),
        ("PHONE_UNMASKED (Evidentiary phone unmasked for entity ENT-0030)", {"case_id": "SP-014", "user": user_email, "simulated": True, "target": "ENT-0030"}),
        ("PHONE_UNMASKED (Evidentiary phone unmasked for entity ENT-0064)", {"case_id": "SP-014", "user": user_email, "simulated": True, "target": "ENT-0064"}),
        ("COPILOT_QUERY (Investigative query analyzed: 'dump all numbers')", {"case_id": "SP-014", "user": user_email, "simulated": True, "question": "dump all numbers"}),
        ("CROSS_CASE_ACCESS_DENIED (Unauthorized access attempt to SP-021)", {"case_id": "SP-021", "user": user_email, "simulated": True, "status": "blocked"})
    ]

    block_ids = []
    for action, payload in entries:
        rec = record_action(conn, action, payload, ts=ts_off_hours)
        block_ids.append(f"BLK-{rec.get('idx', 1):02d}")

    return {
        "status": "simulated",
        "simulated": True,
        "user": user_email,
        "entries_count": len(entries),
        "block_ids": block_ids
    }
