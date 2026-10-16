import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
import sqlite3

GENESIS_PREV_HASH = "0" * 64

def canonical_json(data: Any) -> str:
    """Produces deterministic canonical JSON string without whitespace and with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def compute_hash(prev_hash: str, ts: str, action: str, payload_json: str) -> str:
    content = f"{prev_hash}{ts}{action}{payload_json}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()

def init_ledger(conn: sqlite3.Connection):
    """Initializes ledger table and inserts genesis block if empty."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            idx INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM ledger")
    count = cursor.fetchone()[0]
    if count == 0:
        ts = "2026-09-01T08:00:00Z"
        action = "GENESIS (Chain of custody initialized)"
        payload_json = canonical_json({"system": "SAKSHI", "version": "2.0", "status": "active"})
        h = compute_hash(GENESIS_PREV_HASH, ts, action, payload_json)
        cursor.execute("""
            INSERT INTO ledger (idx, ts, action, payload_json, prev_hash, hash)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (ts, action, payload_json, GENESIS_PREV_HASH, h))
        conn.commit()

def record_action(conn: sqlite3.Connection, action: str, payload: Dict[str, Any], ts: Optional[str] = None) -> Dict[str, Any]:
    """Appends an immutable audit entry to the cryptographic ledger chain."""
    init_ledger(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT idx, hash FROM ledger ORDER BY idx DESC LIMIT 1")
    row = cursor.fetchone()
    prev_idx, prev_hash = row[0], row[1]
    new_idx = prev_idx + 1

    if not ts:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload_str = canonical_json(payload)
    new_hash = compute_hash(prev_hash, ts, action, payload_str)

    cursor.execute("""
        INSERT INTO ledger (idx, ts, action, payload_json, prev_hash, hash)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (new_idx, ts, action, payload_str, prev_hash, new_hash))
    conn.commit()

    return {
        "idx": new_idx,
        "ts": ts,
        "action": action,
        "hash": new_hash,
        "prev_hash": prev_hash
    }

def verify_ledger_chain(conn: sqlite3.Connection) -> Tuple[bool, Optional[Any], Optional[str]]:
    """Verifies internal cryptographic integrity of the ledger blocks."""
    init_ledger(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT idx, ts, action, payload_json, prev_hash, hash FROM ledger ORDER BY idx ASC")
    rows = cursor.fetchall()

    if not rows:
        return False, 0, "Empty ledger"

    # Genesis check
    first = rows[0]
    if first[4] != GENESIS_PREV_HASH:
        return False, first[0], "Genesis block has invalid previous hash"
    recalc_first = compute_hash(first[4], first[1], first[2], first[3])
    if recalc_first != first[5]:
        return False, first[0], f"Genesis block hash mismatch (computed {recalc_first} != stored {first[5]})"

    prev_hash = first[5]
    for row in rows[1:]:
        idx, ts, action, payload_str, p_hash, stored_hash = row
        if p_hash != prev_hash:
            return False, idx, f"Chain link broken at block #{idx}: prev_hash does not match previous block hash"
        recalc = compute_hash(p_hash, ts, action, payload_str)
        if recalc != stored_hash:
            return False, idx, f"Hash corruption at block #{idx}: payload or header modified"
        prev_hash = stored_hash

    return True, None, None

def get_ledger_state(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Retrieves full ledger chain and overall integrity state."""
    init_ledger(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT idx, ts, action, payload_json, prev_hash, hash FROM ledger ORDER BY idx ASC")
    rows = cursor.fetchall()

    entries = []
    head_hash = rows[-1][5] if rows else ""

    ok, broken_at, reason = verify_ledger_chain(conn)

    for row in rows:
        idx, ts, action, payload_json, prev_hash, h = row
        entry = {
            "idx": idx,
            "ts": ts,
            "action": action,
            "hash": h,
            "prev_hash": prev_hash,
        }
        if not ok and idx == broken_at:
            entry["tampered"] = True
        entries.append(entry)

    return {
        "head_hash": head_hash,
        "status": "intact" if ok else "tampered",
        "is_tampered": not ok,
        "broken_at": broken_at,
        "entries": entries
    }
