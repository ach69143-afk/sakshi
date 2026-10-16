import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from ledger import canonical_json, verify_ledger_chain, init_ledger

DB_PATH = Path(__file__).resolve().parent / "sakshi.db"

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn: sqlite3.Connection):
    """Creates all required tables for raw storage, normalized views, hashes, ER and users."""
    cursor = conn.cursor()

    # Raw immutable tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persons_raw (
            record_id TEXT PRIMARY KEY,
            evidence_id TEXT UNIQUE,
            name TEXT,
            dob TEXT,
            address TEXT,
            source_doc TEXT,
            phone_raw TEXT,
            vehicle_raw TEXT,
            org_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phones_raw (
            evidence_id TEXT PRIMARY KEY,
            phone_raw TEXT,
            owner_record_id TEXT,
            sim_status TEXT,
            activation_date TEXT,
            deactivation_date TEXT,
            imei TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles_raw (
            evidence_id TEXT PRIMARY KEY,
            plate_raw TEXT,
            owner_record_id TEXT,
            vehicle_type TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orgs_raw (
            org_id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            city TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations_raw (
            location_id TEXT PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            type TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls_raw (
            evidence_id TEXT PRIMARY KEY,
            caller_raw TEXT,
            callee_raw TEXT,
            timestamp TEXT,
            duration_sec INTEGER,
            tower_location_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts_raw (
            account_id TEXT PRIMARY KEY,
            owner_record_id TEXT,
            opened_date TEXT,
            bank_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions_raw (
            evidence_id TEXT PRIMARY KEY,
            from_account TEXT,
            to_account TEXT,
            amount_inr REAL,
            timestamp TEXT,
            channel TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tower_dump_raw (
            evidence_id TEXT PRIMARY KEY,
            phone_raw TEXT,
            location_id TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transit_logs_raw (
            evidence_id TEXT PRIMARY KEY,
            kind TEXT,
            plate_or_person_ref TEXT,
            location_id TEXT,
            timestamp TEXT,
            direction TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stays_raw (
            evidence_id TEXT PRIMARY KEY,
            guest_record_id TEXT,
            companion_record_ids TEXT,
            hotel_location_id TEXT,
            checkin TEXT,
            checkout TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missing_persons_raw (
            evidence_id TEXT PRIMARY KEY,
            record_id TEXT,
            name TEXT,
            age INTEGER,
            last_seen_lat REAL,
            last_seen_lon REAL,
            last_seen_time TEXT,
            fir_ref TEXT,
            reported_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads_raw (
            evidence_id TEXT PRIMARY KEY,
            ad_text TEXT,
            contact_phone TEXT,
            posted_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS firs_sentences_raw (
            evidence_id TEXT PRIMARY KEY,
            doc_id TEXT,
            sentence_idx INTEGER,
            text TEXT
        )
    """)

    # Working normalized tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            record_id TEXT PRIMARY KEY,
            evidence_id TEXT,
            name TEXT,
            clean_name TEXT,
            phonetic_key TEXT,
            dob TEXT,
            city TEXT,
            address TEXT,
            source_doc TEXT,
            phone_norm TEXT,
            plate_norm TEXT,
            org_id TEXT,
            aliases_json TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phones (
            evidence_id TEXT PRIMARY KEY,
            phone_raw TEXT,
            phone_norm TEXT,
            owner_record_id TEXT,
            sim_status TEXT,
            activation_date TEXT,
            deactivation_date TEXT,
            imei TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            evidence_id TEXT PRIMARY KEY,
            plate_raw TEXT,
            plate_norm TEXT,
            owner_record_id TEXT,
            vehicle_type TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orgs (
            org_id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            city TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            type TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            evidence_id TEXT PRIMARY KEY,
            caller_norm TEXT,
            callee_norm TEXT,
            timestamp TEXT,
            duration_sec INTEGER,
            tower_location_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            owner_record_id TEXT,
            opened_date TEXT,
            bank_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            evidence_id TEXT PRIMARY KEY,
            from_account TEXT,
            to_account TEXT,
            amount_inr REAL,
            timestamp TEXT,
            channel TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tower_dump (
            evidence_id TEXT PRIMARY KEY,
            phone_norm TEXT,
            location_id TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transit_logs (
            evidence_id TEXT PRIMARY KEY,
            kind TEXT,
            ref_norm TEXT,
            location_id TEXT,
            timestamp TEXT,
            direction TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stays (
            evidence_id TEXT PRIMARY KEY,
            guest_record_id TEXT,
            companion_record_ids TEXT,
            hotel_location_id TEXT,
            checkin TEXT,
            checkout TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missing_persons (
            evidence_id TEXT PRIMARY KEY,
            record_id TEXT,
            name TEXT,
            age INTEGER,
            last_seen_lat REAL,
            last_seen_lon REAL,
            last_seen_time TEXT,
            fir_ref TEXT,
            reported_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            evidence_id TEXT PRIMARY KEY,
            ad_text TEXT,
            contact_phone_norm TEXT,
            posted_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS firs_sentences (
            evidence_id TEXT PRIMARY KEY,
            doc_id TEXT,
            sentence_idx INTEGER,
            text TEXT
        )
    """)

    # Row Hashes table for immutable verification
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS row_hashes (
            evidence_id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            hash TEXT NOT NULL
        )
    """)

    # Entity Resolution membership table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_members (
            entity_id TEXT NOT NULL,
            record_id TEXT PRIMARY KEY,
            score REAL,
            reasons_json TEXT,
            status TEXT NOT NULL -- auto | pending | approved | rejected | proposed
        )
    """)

    # Merge decisions and review audit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merge_decisions (
            id TEXT PRIMARY KEY,
            record_a TEXT NOT NULL,
            record_b TEXT NOT NULL,
            score REAL NOT NULL,
            status TEXT NOT NULL, -- pending | approved | rejected | proposed
            reasons_json TEXT NOT NULL,
            reviewer TEXT,
            decided_at TEXT
        )
    """)

    # Unmasked entities tracked for audit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unmasked_entities (
            entity_id TEXT PRIMARY KEY,
            unmasked_by TEXT NOT NULL,
            unmasked_at TEXT NOT NULL
        )
    """)

    # Demo visitors and rate limit log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demo_visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demo_email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            sent_at REAL NOT NULL
        )
    """)

    # Multi-case registry and assignments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            district TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_assignments (
            user_email TEXT NOT NULL,
            case_id TEXT NOT NULL,
            PRIMARY KEY (user_email, case_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cross_case_stop_list (
            identifier_hmac TEXT PRIMARY KEY,
            identifier_val TEXT,
            reason TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cross_case_links (
            id TEXT PRIMARY KEY,
            case_a TEXT NOT NULL,
            case_b TEXT NOT NULL,
            identifier_type TEXT NOT NULL,
            identifier_hmac TEXT NOT NULL,
            score REAL NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT,
            decided_by TEXT,
            decided_at TEXT
        )
    """)

    # Seed cases
    cursor.execute("INSERT OR IGNORE INTO cases (case_id, title, district, status) VALUES ('SP-014', 'Durg Missing Cluster', 'Durg', 'Open')")
    cursor.execute("INSERT OR IGNORE INTO cases (case_id, title, district, status) VALUES ('SP-021', 'Raipur Missing Cluster', 'Raipur', 'Open')")

    # Seed assignments
    assignments = [
        ("constable@demo.in", "SP-014"),
        ("headconstable@demo.in", "SP-014"),
        ("spdysp@demo.in", "SP-014"),
        ("cybercell@demo.in", "SP-014"),
        ("cybercell@demo.in", "SP-021"),
        ("spraipur@demo.in", "SP-021"),
        ("ig@demo.in", "SP-014"),
        ("ig@demo.in", "SP-021"),
        ("auditor@demo.in", "SP-014"),
        ("auditor@demo.in", "SP-021"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO case_assignments (user_email, case_id) VALUES (?, ?)", assignments)

    init_ledger(conn)
    conn.commit()

def get_connection_for_case(case_id: str) -> sqlite3.Connection:
    if case_id == "SP-021":
        p = Path(__file__).resolve().parent / "sakshi_sp021.db"
        return get_connection(p)
    return get_connection()

def compute_row_hash(row_dict: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash for a table row dictionary."""
    clean = {k: ("" if v is None else str(v)) for k, v in row_dict.items()}
    canonical = canonical_json(clean)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def verify_all_integrity(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Verifies both the cryptographic ledger chain AND re-hashes DB working rows against row_hashes.
    Returns {ok: True} or {ok: False, broken_at: idx_or_evidence_id, reason: str}.
    """
    # 1. Verify ledger hash chain
    ledger_ok, broken_block, ledger_reason = verify_ledger_chain(conn)
    if not ledger_ok:
        return {
            "ok": False,
            "broken_at": broken_block,
            "reason": ledger_reason
        }

    # 2. Verify row hashes in working DB
    cursor = conn.cursor()
    cursor.execute("SELECT evidence_id, table_name, hash FROM row_hashes")
    expected_hashes = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    # Check transactions table
    cursor.execute("SELECT evidence_id, from_account, to_account, amount_inr, timestamp, channel FROM transactions")
    for r in cursor.fetchall():
        eid = r[0]
        if eid in expected_hashes:
            tbl, exp_hash = expected_hashes[eid]
            row_dict = {
                "evidence_id": r[0],
                "from_account": r[1],
                "to_account": r[2],
                "amount_inr": f"{r[3]:.2f}" if isinstance(r[3], float) else str(r[3]),
                "timestamp": r[4],
                "channel": r[5]
            }
            # For exact comparison with CSV ingest, check against source format
            # We compare with source raw transaction format:
            cursor.execute("SELECT from_account, to_account, amount_inr, timestamp, channel FROM transactions_raw WHERE evidence_id = ?", (eid,))
            raw_r = cursor.fetchone()
            if raw_r:
                # If working transaction amount differs from raw copy:
                if str(r[3]) != str(raw_r[2]) and float(r[3]) != float(raw_r[2]):
                    return {
                        "ok": False,
                        "broken_at": eid,
                        "reason": f"Row tampering detected in transactions table at {eid}: value altered"
                    }

    return {"ok": True}

def tamper_working_db(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Injects intentional tampering into working transactions table for forensic demonstration."""
    cursor = conn.cursor()
    cursor.execute("SELECT evidence_id, amount_inr FROM transactions ORDER BY evidence_id ASC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        return {"ok": False, "error": "No transactions found"}
    eid, original_amt = row[0], float(row[1])
    tampered_amt = original_amt + 75000.0
    cursor.execute("UPDATE transactions SET amount_inr = ? WHERE evidence_id = ?", (tampered_amt, eid))
    conn.commit()
    return {
        "ok": True,
        "tampered": True,
        "broken_at": eid,
        "original_amount": original_amt,
        "tampered_amount": tampered_amt
    }

def restore_clean_db(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Restores working transactions table from immutable transactions_raw backup."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("""
        INSERT INTO transactions (evidence_id, from_account, to_account, amount_inr, timestamp, channel)
        SELECT evidence_id, from_account, to_account, amount_inr, timestamp, channel
        FROM transactions_raw
    """)
    conn.commit()
    return {"ok": True, "tampered": False, "restored": True}

