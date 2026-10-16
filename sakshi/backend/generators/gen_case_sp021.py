import os
import csv
import json
import random
import re
from pathlib import Path

def norm_phone(s):
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    return digits[-10:] if len(digits) >= 10 else digits

def generate_sp021():
    random.seed(7)
    base_dir = Path(__file__).resolve().parent.parent.parent
    sp014_dir = base_dir / "data"
    sp021_dir = base_dir / "data" / "case_SP-021"
    sp021_dir.mkdir(parents=True, exist_ok=True)

    # 1. READ OVERLAPS FROM SP-014 (NEVER HARDCODE)
    # 1a. Fake ad contact phone
    planted_ad_phone = ""
    with open(sp014_dir / "ads.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("contact_phone"):
                planted_ad_phone = row["contact_phone"]
                break

    # 1b. Pass-through account number
    planted_account = ""
    with open(sp014_dir / "transactions.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        froms = {}
        tos = {}
        for row in reader:
            fa = row["from_account"]
            ta = row["to_account"]
            froms[fa] = froms.get(fa, 0) + 1
            tos[ta] = tos.get(ta, 0) + 1
        common = set(froms.keys()) & set(tos.keys())
        if common:
            planted_account = sorted(common, key=lambda a: froms[a] + tos[a], reverse=True)[0]
        else:
            planted_account = "ACC0029"

    # 1c. Broker phone returning under new alias name
    planted_broker_phone = ""
    with open(sp014_dir / "persons_raw.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["record_id"] in ("R0019", "R0030", "R0064") and row.get("phone_raw"):
                planted_broker_phone = row["phone_raw"]
                break
    if not planted_broker_phone:
        planted_broker_phone = "+91 87710-93248"

    # 1d. Decoy innocent common number (taxi stand) with high calls
    decoy_phone = ""
    with open(sp014_dir / "persons_raw.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("org_id") == "O05" and row.get("phone_raw"):
                decoy_phone = row["phone_raw"]
                break
    if not decoy_phone:
        decoy_phone = "8185067165"

    # 2. GENERATE SP-021 DATA
    # Locations
    locations = [
        {"location_id": "LOC-RP-01", "name": "Jaistambh Chowk, Raipur", "lat": 21.2379, "lon": 81.6337, "type": "commercial"},
        {"location_id": "LOC-RP-02", "name": "Telibandha Lake, Raipur", "lat": 21.2333, "lon": 81.6617, "type": "transit"},
        {"location_id": "LOC-RP-03", "name": "Pandri Bus Terminal", "lat": 21.2560, "lon": 81.6520, "type": "transport"},
        {"location_id": "LOC-RP-04", "name": "Tatibandh Toll Plaza NH-53", "lat": 21.2588, "lon": 81.5542, "type": "toll"},
        {"location_id": "LOC-RP-05", "name": "Naya Raipur Expressway", "lat": 21.1610, "lon": 81.7870, "type": "highway"},
        {"location_id": "LOC-RP-06", "name": "Devendra Nagar, Raipur", "lat": 21.2520, "lon": 81.6410, "type": "residential"},
        {"location_id": "LOC-RP-07", "name": "Shankar Nagar, Raipur", "lat": 21.2440, "lon": 81.6680, "type": "residential"},
        {"location_id": "LOC-RP-08", "name": "Hotel Green Park Raipur", "lat": 21.2400, "lon": 81.6450, "type": "hotel"},
        {"location_id": "LOC-RP-09", "name": "Raipur Junction Rly Station", "lat": 21.2570, "lon": 81.6290, "type": "transport"},
        {"location_id": "LOC-RP-10", "name": "Mandir Hasaud Junction", "lat": 21.2210, "lon": 81.7580, "type": "transit"}
    ]

    # Orgs
    orgs = [
        {"org_id": "O-RP-01", "name": "Raipur Quick Placement Hub", "type": "agency", "city": "Raipur"},
        {"org_id": "O-RP-02", "name": "Chhattisgarh Express Cabs", "type": "transport", "city": "Raipur"},
        {"org_id": "O-RP-03", "name": "Mahanadi Logistics Pvt Ltd", "type": "logistics", "city": "Raipur"},
        {"org_id": "O-RP-04", "name": "Kanker Roadlines", "type": "transport", "city": "Raipur"},
        {"org_id": "O-RP-05", "name": "Capital Finance Services", "type": "finance", "city": "Raipur"},
        {"org_id": "O-RP-06", "name": "Sai Cyber Cafe Pandri", "type": "shop", "city": "Raipur"}
    ]

    # Missing Persons (4)
    missing_persons = [
        {"evidence_id": "MP-RP-01", "record_id": "R-RP-0001", "name": "Pooja Sahu", "age": 19, "last_seen_lat": 21.2379, "last_seen_lon": 81.6337, "last_seen_time": "2026-09-18T14:30:00", "fir_ref": "FIR-RP-01", "reported_time": "2026-09-19T09:00:00"},
        {"evidence_id": "MP-RP-02", "record_id": "R-RP-0002", "name": "Kavita Netam", "age": 21, "last_seen_lat": 21.2560, "last_seen_lon": 81.6520, "last_seen_time": "2026-09-18T16:00:00", "fir_ref": "FIR-RP-01", "reported_time": "2026-09-19T10:15:00"},
        {"evidence_id": "MP-RP-03", "record_id": "R-RP-0003", "name": "Sarita Markam", "age": 20, "last_seen_lat": 21.2333, "last_seen_lon": 81.6617, "last_seen_time": "2026-09-18T18:45:00", "fir_ref": "FIR-RP-02", "reported_time": "2026-09-19T11:30:00"},
        {"evidence_id": "MP-RP-04", "record_id": "R-RP-0004", "name": "Anita Bhagat", "age": 22, "last_seen_lat": 21.2570, "last_seen_lon": 81.6290, "last_seen_time": "2026-09-18T20:10:00", "fir_ref": "FIR-RP-02", "reported_time": "2026-09-19T14:00:00"}
    ]

    # Persons (35)
    first_names = ["Ramesh", "Sunil", "Amit", "Manoj", "Dinesh", "Karan", "Rajesh", "Pankaj", "Vicky", "Alok", "Gaurav", "Deepak", "Rohit", "Santosh", "Neeraj"]
    last_names = ["Tiwari", "Verma", "Sahu", "Yadav", "Dewangan", "Baghel", "Agrawal", "Shukla", "Pandey", "Mishra", "Patel", "Thakur"]

    persons_raw = []
    phones_raw = []
    accounts_raw = []
    vehicles_raw = []

    # Missing persons records
    for mp in missing_persons:
        rid = mp["record_id"]
        ph = f"+91 {random.randint(70000, 99999)}-{random.randint(10000, 99999)}"
        persons_raw.append({
            "record_id": rid,
            "evidence_id": f"PR-{rid}",
            "name": mp["name"],
            "dob": f"200{random.randint(3, 7)}-0{random.randint(1, 9)}-15",
            "address": "Raipur City",
            "source_doc": mp["fir_ref"],
            "phone_raw": ph,
            "vehicle_raw": "",
            "org_id": ""
        })
        phones_raw.append({
            "evidence_id": f"PH-{rid}",
            "phone_raw": ph,
            "owner_record_id": rid,
            "sim_status": "active",
            "activation_date": "2025-01-10",
            "deactivation_date": "",
            "imei": f"86{random.randint(1000000000000, 9999999999999)}"
        })

    # Planted Broker with new alias
    persons_raw.append({
        "record_id": "R-RP-0005",
        "evidence_id": "PR-R-RP-0005",
        "name": "Ramesh Tiwari alias Bhura",
        "dob": "1985-04-12",
        "address": "Devendra Nagar, Raipur",
        "source_doc": "FIR-RP-01",
        "phone_raw": planted_broker_phone,
        "vehicle_raw": "CG-04-RP-9921",
        "org_id": "O-RP-01"
    })
    phones_raw.append({
        "evidence_id": "PH-R-RP-0005",
        "phone_raw": planted_broker_phone,
        "owner_record_id": "R-RP-0005",
        "sim_status": "active",
        "activation_date": "2026-02-01",
        "deactivation_date": "",
        "imei": "861234567890123"
    })
    vehicles_raw.append({
        "evidence_id": "VH-R-RP-0005",
        "plate_raw": "CG-04-RP-9921",
        "owner_record_id": "R-RP-0005",
        "vehicle_type": "SUV"
    })

    # Decoy Taxi Stand (City Cab Services operator)
    persons_raw.append({
        "record_id": "R-RP-0006",
        "evidence_id": "PR-R-RP-0006",
        "name": "Central Taxi Stand Raipur Dispatch",
        "dob": "1980-01-01",
        "address": "Pandri Bus Terminal, Raipur",
        "source_doc": "CDR",
        "phone_raw": decoy_phone,
        "vehicle_raw": "CG-04-TX-1000",
        "org_id": "O-RP-02"
    })
    phones_raw.append({
        "evidence_id": "PH-R-RP-0006",
        "phone_raw": decoy_phone,
        "owner_record_id": "R-RP-0006",
        "sim_status": "active",
        "activation_date": "2020-01-01",
        "deactivation_date": "",
        "imei": "860000000000001"
    })

    # Generate remaining people up to 35
    for i in range(7, 36):
        rid = f"R-RP-{i:04d}"
        nm = f"{random.choice(first_names)} {random.choice(last_names)}"
        ph = f"+91 {random.randint(60000, 99999)}-{random.randint(10000, 99999)}"
        pl = f"CG-04-{random.choice(['AA','AB','AC','AD'])}-{random.randint(1000, 9999)}" if random.random() < 0.4 else ""
        oid = random.choice([o["org_id"] for o in orgs]) if random.random() < 0.4 else ""
        persons_raw.append({
            "record_id": rid,
            "evidence_id": f"PR-{rid}",
            "name": nm,
            "dob": f"19{random.randint(75, 99)}-0{random.randint(1, 9)}-{random.randint(10, 28)}",
            "address": f"Sector {random.randint(1, 12)}, Raipur",
            "source_doc": "CDR",
            "phone_raw": ph,
            "vehicle_raw": pl,
            "org_id": oid
        })
        phones_raw.append({
            "evidence_id": f"PH-{rid}",
            "phone_raw": ph,
            "owner_record_id": rid,
            "sim_status": "active",
            "activation_date": "2025-06-01",
            "deactivation_date": "",
            "imei": f"86{random.randint(1000000000000, 9999999999999)}"
        })
        if pl:
            vehicles_raw.append({
                "evidence_id": f"VH-{rid}",
                "plate_raw": pl,
                "owner_record_id": rid,
                "vehicle_type": "Sedan" if "AA" in pl else "Motorcycle"
            })

    # Accounts (25), including planted pass-through account
    accounts_raw.append({
        "account_id": planted_account,
        "owner_record_id": "R-RP-0005",
        "opened_date": "2026-01-15",
        "bank_name": "State Bank of India Raipur Main Branch"
    })
    for i in range(1, 25):
        aid = f"ACC-RP-{i:04d}"
        accounts_raw.append({
            "account_id": aid,
            "owner_record_id": persons_raw[i]["record_id"],
            "opened_date": "2025-05-10",
            "bank_name": random.choice(["HDFC Bank Raipur", "Punjab National Bank", "ICICI Bank Raipur", "Bank of Baroda"])
        })

    # Calls (120 calls)
    # Ensure decoy number has 20 calls from various people
    calls_raw = []
    call_idx = 1
    # Decoy high-call volume
    for i in range(20):
        caller = persons_raw[i % len(persons_raw)]["phone_raw"]
        calls_raw.append({
            "evidence_id": f"CDR-RP-{call_idx:04d}",
            "caller_raw": caller,
            "callee_raw": decoy_phone,
            "timestamp": f"2026-09-18T{10 + (i % 10):02d}:{random.randint(10, 59):02d}:00",
            "duration_sec": random.randint(45, 180),
            "tower_location_id": "LOC-RP-03"
        })
        call_idx += 1

    # Missing persons calling planted ad phone (bait)
    for mp in missing_persons:
        caller = [p["phone_raw"] for p in persons_raw if p["record_id"] == mp["record_id"]][0]
        calls_raw.append({
            "evidence_id": f"CDR-RP-{call_idx:04d}",
            "caller_raw": caller,
            "callee_raw": planted_ad_phone,
            "timestamp": f"2026-09-18T{11 + random.randint(0, 3):02d}:{random.randint(10, 50):02d}:00",
            "duration_sec": random.randint(120, 360),
            "tower_location_id": "LOC-RP-01"
        })
        call_idx += 1

    # Remaining calls
    all_phones = [p["phone_raw"] for p in persons_raw if p["phone_raw"]]
    while len(calls_raw) < 120:
        c1, c2 = random.sample(all_phones, 2)
        calls_raw.append({
            "evidence_id": f"CDR-RP-{call_idx:04d}",
            "caller_raw": c1,
            "callee_raw": c2,
            "timestamp": f"2026-09-1{random.randint(5, 9)}T{random.randint(8, 22):02d}:{random.randint(0, 59):02d}:00",
            "duration_sec": random.randint(20, 300),
            "tower_location_id": random.choice([loc["location_id"] for loc in locations])
        })
        call_idx += 1

    # Transactions (50)
    txns_raw = []
    # Pass-through activity using planted_account
    txn_idx = 1
    for i in range(10):
        txns_raw.append({
            "evidence_id": f"TXN-RP-{txn_idx:04d}",
            "from_account": f"ACC-RP-{random.randint(1, 10):04d}",
            "to_account": planted_account,
            "amount_inr": random.randint(25000, 48000),
            "timestamp": f"2026-09-18T1{i:01d}:10:00",
            "channel": "UPI"
        })
        txn_idx += 1
        txns_raw.append({
            "evidence_id": f"TXN-RP-{txn_idx:04d}",
            "from_account": planted_account,
            "to_account": f"ACC-RP-{random.randint(11, 20):04d}",
            "amount_inr": random.randint(24000, 47000),
            "timestamp": f"2026-09-18T1{i:01d}:18:00",
            "channel": "IMPS"
        })
        txn_idx += 1

    all_acc_ids = [a["account_id"] for a in accounts_raw]
    while len(txns_raw) < 50:
        a1, a2 = random.sample(all_acc_ids, 2)
        txns_raw.append({
            "evidence_id": f"TXN-RP-{txn_idx:04d}",
            "from_account": a1,
            "to_account": a2,
            "amount_inr": random.randint(1000, 30000),
            "timestamp": f"2026-09-1{random.randint(5, 9)}T{random.randint(9, 20):02d}:{random.randint(0, 59):02d}:00",
            "channel": "NEFT" if random.random() < 0.5 else "UPI"
        })
        txn_idx += 1

    # Tower Dump (100 rows)
    tower_rows = []
    for i in range(1, 101):
        tower_rows.append({
            "evidence_id": f"TWR-RP-{i:04d}",
            "phone_raw": random.choice(all_phones),
            "location_id": random.choice([loc["location_id"] for loc in locations]),
            "timestamp": f"2026-09-18T{random.randint(12, 23):02d}:{random.randint(0, 59):02d}:00"
        })

    # Stays (15)
    stays = []
    for i in range(1, 16):
        stays.append({
            "evidence_id": f"STY-RP-{i:04d}",
            "guest_record_id": persons_raw[i % len(persons_raw)]["record_id"],
            "companion_record_ids": persons_raw[(i + 1) % len(persons_raw)]["record_id"],
            "hotel_location_id": "LOC-RP-08",
            "checkin": f"2026-09-18T{14 + (i % 6):02d}:00:00",
            "checkout": f"2026-09-19T{10 + (i % 4):02d}:00:00"
        })

    # Transit Logs (25)
    transit_logs = []
    for i in range(1, 26):
        transit_logs.append({
            "evidence_id": f"TRN-RP-{i:04d}",
            "kind": "fastag",
            "plate_or_person_ref": vehicles_raw[i % len(vehicles_raw)]["plate_raw"],
            "location_id": "LOC-RP-04",
            "timestamp": f"2026-09-18T{21 + (i % 3):02d}:{random.randint(0, 59):02d}:00",
            "direction": "outbound_sambalpur"
        })

    # Ads (3)
    ads = [
        {
            "evidence_id": "AD-RP-01",
            "ad_text": "Immediate joining: Boutique executive and hospitality assistants in Naya Raipur. Free boarding, high stipend. Contact Raipur Quick Placement.",
            "contact_phone": planted_ad_phone, # Overlap bait!
            "posted_time": "2026-09-16T11:00:00"
        },
        {
            "evidence_id": "AD-RP-02",
            "ad_text": "Delivery executives needed for wholesale grocery warehouse Pandri Raipur. Fixed salary.",
            "contact_phone": "+91 88990-11223",
            "posted_time": "2026-09-10T10:00:00"
        },
        {
            "evidence_id": "AD-RP-03",
            "ad_text": "Commercial taxi driver opening for airport and outstation routes. Clean driving record required.",
            "contact_phone": "+91 77665-44332",
            "posted_time": "2026-09-12T15:00:00"
        }
    ]

    # FIR Sentences (40)
    fir_sentences = [
        {"evidence_id": "FIR-RP-01-S01", "doc_id": "FIR-RP-01", "sentence_idx": 1, "text": "Complainant states his daughter Pooja Sahu left home on 18 September for a job interview in Pandri."},
        {"evidence_id": "FIR-RP-01-S02", "doc_id": "FIR-RP-01", "sentence_idx": 2, "text": "She responded to an online hospitality vacancy advertisement promising boarding in Raipur."},
        {"evidence_id": "FIR-RP-01-S03", "doc_id": "FIR-RP-01", "sentence_idx": 3, "text": "Witnesses observed a white SUV vehicle CG-04-RP-9921 departing near Tatibandh junction late evening."},
        {"evidence_id": "FIR-RP-01-S04", "doc_id": "FIR-RP-01", "sentence_idx": 4, "text": "The phone was abruptly switched off past the toll boundary."},
        {"evidence_id": "FIR-RP-02-S01", "doc_id": "FIR-RP-02", "sentence_idx": 1, "text": "Second victim Sarita Markam reported missing under identical circumstances from Telibandha."},
        {"evidence_id": "FIR-RP-02-S02", "doc_id": "FIR-RP-02", "sentence_idx": 2, "text": "Suspect Ramesh Tiwari alias Bhura was seen coordinating movements near hotel transit desk."},
        {"evidence_id": "FIR-RP-02-S03", "doc_id": "FIR-RP-02", "sentence_idx": 3, "text": "Frequent financial transfers noted via UPI to centralized account."},
        {"evidence_id": "FIR-RP-02-S04", "doc_id": "FIR-RP-02", "sentence_idx": 4, "text": "Investigation instituted under section 365 IPC at Kotwali Raipur."}
    ]
    # Pad sentences to 40
    for idx in range(9, 41):
        fir_sentences.append({
            "evidence_id": f"FIR-RP-02-S{idx:02d}",
            "doc_id": "FIR-RP-02",
            "sentence_idx": idx,
            "text": f"Corroborating record of continuous transit telemetry recorded across checkpost checkpoint {idx}."
        })

    # WRITE ALL CSVs
    def write_csv(name, fieldnames, rows):
        with open(sp021_dir / name, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv("locations.csv", ["location_id", "name", "lat", "lon", "type"], locations)
    write_csv("orgs.csv", ["org_id", "name", "type", "city"], orgs)
    write_csv("missing_persons.csv", ["evidence_id", "record_id", "name", "age", "last_seen_lat", "last_seen_lon", "last_seen_time", "fir_ref", "reported_time"], missing_persons)
    write_csv("persons_raw.csv", ["record_id", "evidence_id", "name", "dob", "address", "source_doc", "phone_raw", "vehicle_raw", "org_id"], persons_raw)
    write_csv("phones.csv", ["evidence_id", "phone_raw", "owner_record_id", "sim_status", "activation_date", "deactivation_date", "imei"], phones_raw)
    write_csv("vehicles.csv", ["evidence_id", "plate_raw", "owner_record_id", "vehicle_type"], vehicles_raw)
    write_csv("accounts.csv", ["account_id", "owner_record_id", "opened_date", "bank_name"], accounts_raw)
    write_csv("calls.csv", ["evidence_id", "caller_raw", "callee_raw", "timestamp", "duration_sec", "tower_location_id"], calls_raw)
    write_csv("transactions.csv", ["evidence_id", "from_account", "to_account", "amount_inr", "timestamp", "channel"], txns_raw)
    write_csv("tower_dump.csv", ["evidence_id", "phone_raw", "location_id", "timestamp"], tower_rows)
    write_csv("stays.csv", ["evidence_id", "guest_record_id", "companion_record_ids", "hotel_location_id", "checkin", "checkout"], stays)
    write_csv("transit_logs.csv", ["evidence_id", "kind", "plate_or_person_ref", "location_id", "timestamp", "direction"], transit_logs)
    write_csv("ads.csv", ["evidence_id", "ad_text", "contact_phone", "posted_time"], ads)
    write_csv("firs_sentences.csv", ["evidence_id", "doc_id", "sentence_idx", "text"], fir_sentences)

    # 3. WRITE data/cross_case_truth.json
    truth = {
        "case_a": "SP-014",
        "case_b": "SP-021",
        "seed": 7,
        "planted_overlaps": [
            {
                "type": "ad_phone",
                "value": norm_phone(planted_ad_phone),
                "raw_value": planted_ad_phone,
                "description": "The SP-014 fake-ad contact number used as bait in SP-021"
            },
            {
                "type": "account",
                "value": planted_account,
                "raw_value": planted_account,
                "description": "The SP-014 pass-through account number appearing in SP-021"
            },
            {
                "type": "broker_phone",
                "value": norm_phone(planted_broker_phone),
                "raw_value": planted_broker_phone,
                "description": "One broker phone returning under new alias name in SP-021"
            }
        ],
        "decoy": {
            "type": "phone",
            "value": norm_phone(decoy_phone),
            "raw_value": decoy_phone,
            "description": "Taxi stand number appearing in both cases with high call volume",
            "suppressed": True
        }
    }
    with open(sp014_dir / "cross_case_truth.json", "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=2)

    print("Generated SP-021 files in", sp021_dir)
    print("Truth key written to", sp014_dir / "cross_case_truth.json")
    return truth

if __name__ == "__main__":
    generate_sp021()
