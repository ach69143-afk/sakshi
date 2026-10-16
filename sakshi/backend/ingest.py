import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional
import sqlite3

from db import get_connection, init_db, compute_row_hash, DB_PATH
from ledger import record_action

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def norm_phone(s: Optional[str]) -> str:
    """Normalizes any phone string to the trailing 10 digits."""
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    return digits[-10:] if len(digits) >= 10 else digits

def norm_plate(s: Optional[str]) -> str:
    """Normalizes vehicle plate numbers to uppercase alphanumeric without spaces or hyphens."""
    if not s:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

def parse_name_and_aliases(raw_name: str) -> Tuple[str, List[str]]:
    """Splits honorifics, aliases, and parenthetical nicknames from person names."""
    if not raw_name:
        return "", []
    
    s = raw_name.strip()
    aliases = []

    # Check for ('alias') or (alias)
    paren_match = re.search(r"['\"]?\(?['\"]?alias\s+([^)'\"]+)['\"]?\)?['\"]?", s, re.IGNORECASE)
    if paren_match:
        aliases.append(paren_match.group(1).strip())
        s = s[:paren_match.start()] + s[paren_match.end():]
    
    # Check for "alias <name>"
    if " alias " in s.lower():
        parts = re.split(r"\s+alias\s+", s, flags=re.IGNORECASE)
        s = parts[0].strip()
        for p in parts[1:]:
            aliases.append(p.strip())

    # Check for quotes like 'Golden' or "Golden"
    quote_matches = re.findall(r"['\"]([^'\"]+)['\"]", s)
    for qm in quote_matches:
        aliases.append(qm.strip())
    s = re.sub(r"['\"][^'\"]+['\"]", "", s).strip()

    # Strip honorifics
    honorifics = [r"\bshri\b", r"\bshree\b", r"\bsmt\b", r"\bmr\b", r"\bmrs\b", r"\bdr\b", r"\bmohd\b", r"\bmohammad\b", r"\badv\b"]
    for h in honorifics:
        s = re.sub(h, "", s, flags=re.IGNORECASE)
    
    clean = re.sub(r"\s+", " ", s).strip()
    return clean, aliases

def fold_transliteration(s: str) -> str:
    """Applies systematic transliteration folding for Indian names."""
    s = s.lower()
    # Vowel folding
    s = re.sub(r"oo|u+", "u", s)
    s = re.sub(r"ee|i+", "i", s)
    s = re.sub(r"aa|a+", "a", s)
    # Consonant folding
    s = re.sub(r"w", "v", s)
    s = re.sub(r"sh", "s", s)
    s = re.sub(r"ph", "f", s)
    s = re.sub(r"dh", "d", s)
    s = re.sub(r"th", "t", s)
    s = re.sub(r"kh", "k", s)
    s = re.sub(r"bh", "b", s)
    s = re.sub(r"gh", "g", s)
    s = re.sub(r"ch", "c", s)
    # Common suffix / regional variant endings
    s = re.sub(r"rathore|rathod", "rathod", s)
    s = re.sub(r"aggarwal|agrawal|agarwal", "agrawal", s)
    s = re.sub(r"baghel|bagel", "baghel", s)
    s = re.sub(r"sahoo|sahu", "sahu", s)
    s = re.sub(r"varma|verma", "verma", s)
    s = re.sub(r"dewangana|dewangan", "dewangan", s)
    # Remove all non-alpha
    s = re.sub(r"[^a-z]", "", s)
    # Deduplicate consecutive characters
    s = re.sub(r"(.)\1+", r"\1", s)
    return s

def compute_phonetic_key(raw_name: str) -> str:
    """Computes a phonetic blocking key for person records."""
    base, _ = parse_name_and_aliases(raw_name)
    tokens = [t for t in re.split(r"[\s\.]+", base.strip()) if t]
    folded_tokens = [fold_transliteration(t) for t in tokens if len(t) > 1]
    if not folded_tokens and tokens:
        folded_tokens = [fold_transliteration(t) for t in tokens]
    return "_".join(sorted(folded_tokens))

def extract_city(address: Optional[str]) -> str:
    """Extracts common city names from address field."""
    if not address:
        return ""
    addr_lower = address.lower()
    for city in ["bhilai", "durg", "kumhari", "raipur", "nagpur", "rajnandgaon"]:
        if city in addr_lower:
            return city.capitalize()
    return ""

def load_csv_rows(filepath: Path) -> List[Dict[str, str]]:
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def ingest_all(data_dir: Optional[Path] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Ingests all CSV datasets into sakshi.db with raw tables, normalized views, and row hashes."""
    d_dir = data_dir or DATA_DIR
    conn = get_connection(db_path)
    init_db(conn)
    cursor = conn.cursor()

    # Clear existing tables for deterministic reload
    tables_to_clear = [
        "persons_raw", "phones_raw", "vehicles_raw", "orgs_raw", "locations_raw", "calls_raw",
        "accounts_raw", "transactions_raw", "tower_dump_raw", "transit_logs_raw", "stays_raw",
        "missing_persons_raw", "ads_raw", "firs_sentences_raw",
        "persons", "phones", "vehicles", "orgs", "locations", "calls",
        "accounts", "transactions", "tower_dump", "transit_logs", "stays",
        "missing_persons", "ads", "firs_sentences", "row_hashes", "unmasked_entities",
        "entity_members", "merge_decisions"
    ]
    for tbl in tables_to_clear:
        cursor.execute(f"DELETE FROM {tbl}")
    conn.commit()

    file_hashes = {}
    row_counts = {}
    all_row_hashes = []

    # 1. persons_raw
    p_rows = load_csv_rows(d_dir / "persons_raw.csv")
    row_counts["persons_raw"] = len(p_rows)
    for r in p_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "persons_raw", h))
        cursor.execute("""
            INSERT INTO persons_raw (record_id, evidence_id, name, dob, address, source_doc, phone_raw, vehicle_raw, org_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["record_id"], r["evidence_id"], r["name"], r["dob"], r["address"], r["source_doc"], r["phone_raw"], r["vehicle_raw"], r["org_id"]))

        clean_name, aliases = parse_name_and_aliases(r["name"])
        pkey = compute_phonetic_key(r["name"])
        city = extract_city(r["address"])
        cursor.execute("""
            INSERT INTO persons (record_id, evidence_id, name, clean_name, phonetic_key, dob, city, address, source_doc, phone_norm, plate_norm, org_id, aliases_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["record_id"], r["evidence_id"], r["name"], clean_name, pkey, r["dob"], city, r["address"], r["source_doc"], norm_phone(r["phone_raw"]), norm_plate(r["vehicle_raw"]), r["org_id"], json.dumps(aliases)))

    # 2. phones
    ph_rows = load_csv_rows(d_dir / "phones.csv")
    row_counts["phones"] = len(ph_rows)
    for r in ph_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "phones_raw", h))
        cursor.execute("""
            INSERT INTO phones_raw (evidence_id, phone_raw, owner_record_id, sim_status, activation_date, deactivation_date, imei)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["phone_raw"], r["owner_record_id"], r["sim_status"], r["activation_date"], r["deactivation_date"], r["imei"]))
        cursor.execute("""
            INSERT INTO phones (evidence_id, phone_raw, phone_norm, owner_record_id, sim_status, activation_date, deactivation_date, imei)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["phone_raw"], norm_phone(r["phone_raw"]), r["owner_record_id"], r["sim_status"], r["activation_date"], r["deactivation_date"], r["imei"]))

    # 3. vehicles
    v_rows = load_csv_rows(d_dir / "vehicles.csv")
    row_counts["vehicles"] = len(v_rows)
    for r in v_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "vehicles_raw", h))
        cursor.execute("""
            INSERT INTO vehicles_raw (evidence_id, plate_raw, owner_record_id, vehicle_type)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["plate_raw"], r["owner_record_id"], r["vehicle_type"]))
        cursor.execute("""
            INSERT INTO vehicles (evidence_id, plate_raw, plate_norm, owner_record_id, vehicle_type)
            VALUES (?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["plate_raw"], norm_plate(r["plate_raw"]), r["owner_record_id"], r["vehicle_type"]))

    # 4. orgs (no evidence_id -> use org_id)
    org_rows = load_csv_rows(d_dir / "orgs.csv")
    row_counts["orgs"] = len(org_rows)
    for r in org_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["org_id"], "orgs_raw", h))
        cursor.execute("""
            INSERT INTO orgs_raw (org_id, name, type, city)
            VALUES (?, ?, ?, ?)
        """, (r["org_id"], r["name"], r["type"], r["city"]))
        cursor.execute("""
            INSERT INTO orgs (org_id, name, type, city)
            VALUES (?, ?, ?, ?)
        """, (r["org_id"], r["name"], r["type"], r["city"]))

    # 5. locations (no evidence_id -> use location_id)
    loc_rows = load_csv_rows(d_dir / "locations.csv")
    row_counts["locations"] = len(loc_rows)
    for r in loc_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["location_id"], "locations_raw", h))
        cursor.execute("""
            INSERT INTO locations_raw (location_id, name, lat, lon, type)
            VALUES (?, ?, ?, ?, ?)
        """, (r["location_id"], r["name"], float(r["lat"]), float(r["lon"]), r["type"]))
        cursor.execute("""
            INSERT INTO locations (location_id, name, lat, lon, type)
            VALUES (?, ?, ?, ?, ?)
        """, (r["location_id"], r["name"], float(r["lat"]), float(r["lon"]), r["type"]))

    # 6. calls
    call_rows = load_csv_rows(d_dir / "calls.csv")
    row_counts["calls"] = len(call_rows)
    for r in call_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "calls_raw", h))
        cursor.execute("""
            INSERT INTO calls_raw (evidence_id, caller_raw, callee_raw, timestamp, duration_sec, tower_location_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["caller_raw"], r["callee_raw"], r["timestamp"], int(r["duration_sec"]), r["tower_location_id"]))
        cursor.execute("""
            INSERT INTO calls (evidence_id, caller_norm, callee_norm, timestamp, duration_sec, tower_location_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], norm_phone(r["caller_raw"]), norm_phone(r["callee_raw"]), r["timestamp"], int(r["duration_sec"]), r["tower_location_id"]))

    # 7. accounts (no evidence_id -> use account_id)
    acct_rows = load_csv_rows(d_dir / "accounts.csv")
    row_counts["accounts"] = len(acct_rows)
    for r in acct_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["account_id"], "accounts_raw", h))
        cursor.execute("""
            INSERT INTO accounts_raw (account_id, owner_record_id, opened_date, bank_name)
            VALUES (?, ?, ?, ?)
        """, (r["account_id"], r["owner_record_id"], r["opened_date"], r["bank_name"]))
        cursor.execute("""
            INSERT INTO accounts (account_id, owner_record_id, opened_date, bank_name)
            VALUES (?, ?, ?, ?)
        """, (r["account_id"], r["owner_record_id"], r["opened_date"], r["bank_name"]))

    # 8. transactions
    tx_rows = load_csv_rows(d_dir / "transactions.csv")
    row_counts["transactions"] = len(tx_rows)
    for r in tx_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "transactions_raw", h))
        cursor.execute("""
            INSERT INTO transactions_raw (evidence_id, from_account, to_account, amount_inr, timestamp, channel)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["from_account"], r["to_account"], float(r["amount_inr"]), r["timestamp"], r["channel"]))
        cursor.execute("""
            INSERT INTO transactions (evidence_id, from_account, to_account, amount_inr, timestamp, channel)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["from_account"], r["to_account"], float(r["amount_inr"]), r["timestamp"], r["channel"]))

    # 9. tower_dump
    twr_rows = load_csv_rows(d_dir / "tower_dump.csv")
    row_counts["tower_dump"] = len(twr_rows)
    for r in twr_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "tower_dump_raw", h))
        cursor.execute("""
            INSERT INTO tower_dump_raw (evidence_id, phone_raw, location_id, timestamp)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["phone_raw"], r["location_id"], r["timestamp"]))
        cursor.execute("""
            INSERT INTO tower_dump (evidence_id, phone_norm, location_id, timestamp)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], norm_phone(r["phone_raw"]), r["location_id"], r["timestamp"]))

    # 10. transit_logs
    tr_rows = load_csv_rows(d_dir / "transit_logs.csv")
    row_counts["transit_logs"] = len(tr_rows)
    for r in tr_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "transit_logs_raw", h))
        # Toll rows reference a plate; train/bus rows reference a record_id
        ref_norm = norm_plate(r["plate_or_person_ref"]) if r["kind"] == "toll" else r["plate_or_person_ref"]
        cursor.execute("""
            INSERT INTO transit_logs_raw (evidence_id, kind, plate_or_person_ref, location_id, timestamp, direction)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["kind"], r["plate_or_person_ref"], r["location_id"], r["timestamp"], r["direction"]))
        cursor.execute("""
            INSERT INTO transit_logs (evidence_id, kind, ref_norm, location_id, timestamp, direction)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["kind"], ref_norm, r["location_id"], r["timestamp"], r["direction"]))

    # 11. stays
    stay_rows = load_csv_rows(d_dir / "stays.csv")
    row_counts["stays"] = len(stay_rows)
    for r in stay_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "stays_raw", h))
        cursor.execute("""
            INSERT INTO stays_raw (evidence_id, guest_record_id, companion_record_ids, hotel_location_id, checkin, checkout)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["guest_record_id"], r["companion_record_ids"], r["hotel_location_id"], r["checkin"], r["checkout"]))
        cursor.execute("""
            INSERT INTO stays (evidence_id, guest_record_id, companion_record_ids, hotel_location_id, checkin, checkout)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["guest_record_id"], r["companion_record_ids"], r["hotel_location_id"], r["checkin"], r["checkout"]))

    # 12. missing_persons
    mp_rows = load_csv_rows(d_dir / "missing_persons.csv")
    row_counts["missing_persons"] = len(mp_rows)
    for r in mp_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "missing_persons_raw", h))
        cursor.execute("""
            INSERT INTO missing_persons_raw (evidence_id, record_id, name, age, last_seen_lat, last_seen_lon, last_seen_time, fir_ref, reported_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["record_id"], r["name"], int(r["age"]), float(r["last_seen_lat"]), float(r["last_seen_lon"]), r["last_seen_time"], r["fir_ref"], r["reported_time"]))
        cursor.execute("""
            INSERT INTO missing_persons (evidence_id, record_id, name, age, last_seen_lat, last_seen_lon, last_seen_time, fir_ref, reported_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["evidence_id"], r["record_id"], r["name"], int(r["age"]), float(r["last_seen_lat"]), float(r["last_seen_lon"]), r["last_seen_time"], r["fir_ref"], r["reported_time"]))

    # 13. ads
    ad_rows = load_csv_rows(d_dir / "ads.csv")
    row_counts["ads"] = len(ad_rows)
    for r in ad_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "ads_raw", h))
        cursor.execute("""
            INSERT INTO ads_raw (evidence_id, ad_text, contact_phone, posted_time)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["ad_text"], r["contact_phone"], r["posted_time"]))
        cursor.execute("""
            INSERT INTO ads (evidence_id, ad_text, contact_phone_norm, posted_time)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["ad_text"], norm_phone(r["contact_phone"]), r["posted_time"]))

    # 14. firs_sentences
    fir_rows = load_csv_rows(d_dir / "firs_sentences.csv")
    row_counts["firs_sentences"] = len(fir_rows)
    for r in fir_rows:
        h = compute_row_hash(r)
        all_row_hashes.append((r["evidence_id"], "firs_sentences_raw", h))
        cursor.execute("""
            INSERT INTO firs_sentences_raw (evidence_id, doc_id, sentence_idx, text)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["doc_id"], int(r["sentence_idx"]), r["text"]))
        cursor.execute("""
            INSERT INTO firs_sentences (evidence_id, doc_id, sentence_idx, text)
            VALUES (?, ?, ?, ?)
        """, (r["evidence_id"], r["doc_id"], int(r["sentence_idx"]), r["text"]))

    # Insert row hashes
    cursor.executemany("""
        INSERT OR REPLACE INTO row_hashes (evidence_id, table_name, hash)
        VALUES (?, ?, ?)
    """, all_row_hashes)

    conn.commit()

    # Log ingest action to ledger
    total_rows = sum(row_counts.values())
    record_action(
        conn,
        "INGEST (Synthetic dataset loaded into SQLite)",
        {"row_counts": row_counts, "total_rows": total_rows, "evidence_hashes": len(all_row_hashes)},
        ts="2026-09-02T09:15:00Z"
    )

    return {
        "status": "success",
        "row_counts": row_counts,
        "total_rows": total_rows,
        "evidence_hashes": len(all_row_hashes)
    }

if __name__ == "__main__":
    result = ingest_all()
    print("Ingest complete:")
    for k, v in result["row_counts"].items():
        print(f"  {k}: {v}")
    print(f"Total rows: {result['total_rows']}, row hashes: {result['evidence_hashes']}")
