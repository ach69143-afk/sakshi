#!/usr/bin/env python3
"""
SAKSHI dataset validator -- checks the synthetic Case SP-014 dataset against the spec.

Usage:  python validate_dataset.py [--data DIR]       (default: ./sakshi/data next to this script)
Exit code 0 = every check passed, 1 = at least one FAIL.
Checks 1-12 are the required ones from the task brief; checks X1-X6 are extra sanity checks.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
FMT = "%Y-%m-%dT%H:%M:%S"

COLS = {
    "persons_raw.csv": ["record_id", "evidence_id", "name", "dob", "address", "source_doc", "phone_raw",
                        "vehicle_raw", "org_id"],
    "phones.csv": ["evidence_id", "phone_raw", "owner_record_id", "sim_status", "activation_date",
                   "deactivation_date", "imei"],
    "vehicles.csv": ["evidence_id", "plate_raw", "owner_record_id", "vehicle_type"],
    "orgs.csv": ["org_id", "name", "type", "city"],
    "locations.csv": ["location_id", "name", "lat", "lon", "type"],
    "calls.csv": ["evidence_id", "caller_raw", "callee_raw", "timestamp", "duration_sec", "tower_location_id"],
    "accounts.csv": ["account_id", "owner_record_id", "opened_date", "bank_name"],
    "transactions.csv": ["evidence_id", "from_account", "to_account", "amount_inr", "timestamp", "channel"],
    "tower_dump.csv": ["evidence_id", "phone_raw", "location_id", "timestamp"],
    "transit_logs.csv": ["evidence_id", "kind", "plate_or_person_ref", "location_id", "timestamp", "direction"],
    "stays.csv": ["evidence_id", "guest_record_id", "companion_record_ids", "hotel_location_id", "checkin",
                  "checkout"],
    "missing_persons.csv": ["evidence_id", "record_id", "name", "age", "last_seen_lat", "last_seen_lon",
                            "last_seen_time", "fir_ref", "reported_time"],
    "ads.csv": ["evidence_id", "ad_text", "contact_phone", "posted_time"],
    "firs_sentences.csv": ["evidence_id", "doc_id", "sentence_idx", "text"],
}
EID_RE = {
    "persons_raw.csv": r"PR-\d{4}", "phones.csv": r"PH-\d{4}", "vehicles.csv": r"VH-\d{4}",
    "calls.csv": r"CDR-\d{4}", "transactions.csv": r"TXN-\d{4}", "tower_dump.csv": r"TWR-\d{4}",
    "transit_logs.csv": r"TR-\d{4}", "stays.csv": r"HT-\d{4}", "missing_persons.csv": r"MP-\d{2}",
    "ads.csv": r"AD-\d{2}", "firs_sentences.csv": r"FIR-\d{2}-S\d+",
}
# (target, tolerance) -- tolerance 20% as in the brief; exact where the brief gives an exact number
TARGETS = {
    "persons_raw (records)": (75, 0.20), "identities": (60, 0.20), "phones": (70, 0.20), "vehicles": (15, 0.20),
    "orgs": (6, 0.20), "locations": (12, 0.20), "calls": (400, 0.20), "transactions": (150, 0.20),
    "tower_dump": (175, 0.20), "transit_logs": (30, 0.20), "stays": (15, 0.20),
    "missing_persons": (5, 0.0), "ads": (3, 0.0), "fir files": (10, 0.0),
}

results = []


def report(label, ok, detail=""):
    results.append((label, ok))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pt(s):
    return datetime.strptime(s, FMT)


def norm_phone(s):
    return re.sub(r"\D", "", s or "")[-10:]


def norm_plate(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def hav(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def hash_tree(root):
    h = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "sakshi" / "data"))
    args = ap.parse_args()
    D = Path(args.data)
    print("SAKSHI dataset validation -- %s\n" % D)

    # ---------------- 1. files, columns, unique ids ----------------
    problems = []
    tables = {}
    for fn, cols in COLS.items():
        p = D / fn
        if not p.exists():
            problems.append("missing " + fn)
            continue
        with open(p, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), [])
        if header != cols:
            problems.append("%s columns %s != %s" % (fn, header, cols))
        tables[fn] = rd(p)
    for k in range(1, 11):
        if not (D / "firs" / ("FIR_%02d.txt" % k)).exists():
            problems.append("missing firs/FIR_%02d.txt" % k)
    if not (D / "ground_truth.json").exists():
        problems.append("missing ground_truth.json")
    if problems:
        report("1. All files exist with exact columns; evidence_ids unique", False, "; ".join(problems[:4]))
        print("\nCannot continue without the files above.")
        sys.exit(1)
    gt = json.load(open(D / "ground_truth.json", encoding="utf-8"))
    all_eids = []
    bad_fmt = 0
    for fn, rx in EID_RE.items():
        for r in tables[fn]:
            all_eids.append(r["evidence_id"])
            if not re.fullmatch(rx, r["evidence_id"]):
                bad_fmt += 1
    dupes = [k for k, v in Counter(all_eids).items() if v > 1]
    other_ids = (Counter(r["record_id"] for r in tables["persons_raw.csv"]),
                 Counter(r["org_id"] for r in tables["orgs.csv"]),
                 Counter(r["location_id"] for r in tables["locations.csv"]),
                 Counter(r["account_id"] for r in tables["accounts.csv"]))
    dup_other = sum(1 for c in other_ids for v in c.values() if v > 1)
    report("1. All files exist with exact columns; evidence_ids unique across dataset",
           not dupes and not bad_fmt and not dup_other,
           "%d evidence_ids, %d duplicates, %d bad formats, %d duplicate key ids" % (len(all_eids), len(dupes), bad_fmt, dup_other))

    # ---------------- shared lookups ----------------
    recs = {r["record_id"]: r for r in tables["persons_raw.csv"]}
    rec2tid = {}
    for g in gt["identity_groups"]:
        for rid in g["record_ids"]:
            rec2tid[rid] = g["person_id"]
    phone_owner = {norm_phone(r["phone_raw"]): r["owner_record_id"] for r in tables["phones.csv"]}
    phone2tid = {p: rec2tid.get(o) for p, o in phone_owner.items() if o}
    tid_phones = defaultdict(set)
    for p, t in phone2tid.items():
        if t:
            tid_phones[t].add(p)
    calls = tables["calls.csv"]
    acct_owner = {a["account_id"]: a["owner_record_id"] for a in tables["accounts.csv"]}
    acct_tid = {a: rec2tid.get(o) for a, o in acct_owner.items()}
    txns = tables["transactions.csv"]
    locs = {l["location_id"]: l for l in tables["locations.csv"]}

    # ---------------- 2. counts ----------------
    counts = {
        "persons_raw (records)": len(tables["persons_raw.csv"]),
        "identities": len({g["person_id"] for g in gt["identity_groups"]}),
        "phones": len(tables["phones.csv"]), "vehicles": len(tables["vehicles.csv"]),
        "orgs": len(tables["orgs.csv"]), "locations": len(tables["locations.csv"]),
        "calls": len(calls), "transactions": len(txns), "tower_dump": len(tables["tower_dump.csv"]),
        "transit_logs": len(tables["transit_logs.csv"]), "stays": len(tables["stays.csv"]),
        "missing_persons": len(tables["missing_persons.csv"]), "ads": len(tables["ads.csv"]),
        "fir files": len(list((D / "firs").glob("FIR_*.txt"))),
    }
    bad = []
    for k, (tgt, tol) in TARGETS.items():
        lo, hi = tgt * (1 - tol), tgt * (1 + tol)
        if not (lo <= counts[k] <= hi):
            bad.append("%s=%d (want %d +-%d%%)" % (k, counts[k], tgt, int(tol * 100)))
    report("2. Counts roughly match the world size (+-20%)", not bad,
           "; ".join(bad) if bad else ", ".join("%s=%d" % (k, v) for k, v in counts.items()))

    # ---------------- 3. missing persons ----------------
    mps = tables["missing_persons.csv"]
    clat, clon = gt["golden_hour"]["centroid"]
    dists = [hav(float(m["last_seen_lat"]), float(m["last_seen_lon"]), clat, clon) for m in mps]
    times = [pt(m["last_seen_time"]) for m in mps]
    span_h = (max(times) - min(times)).total_seconds() / 3600
    ok3 = len(mps) == 5 and max(dists) <= 3.0 and span_h <= 24
    report("3. 5 missing persons within 3 km of centroid and within a 24 h window", ok3,
           "max distance %.2f km, time span %.1f h" % (max(dists), span_h))

    # ---------------- 4. burner ----------------
    burner = norm_phone(gt["burner_phone"])
    brow = [r for r in tables["phones.csv"] if norm_phone(r["phone_raw"]) == burner]
    twr = tables["tower_dump.csv"]
    near, detail4 = 0, []
    for m in mps:
        ls = pt(m["last_seen_time"])
        lat, lon = float(m["last_seen_lat"]), float(m["last_seen_lon"])
        hit = False
        for r in twr:
            if norm_phone(r["phone_raw"]) != burner:
                continue
            t = pt(r["timestamp"])
            L = locs[r["location_id"]]
            if ls - timedelta(hours=2) <= t <= ls and hav(lat, lon, float(L["lat"]), float(L["lon"])) <= 1.5:
                hit = True
        near += hit
        detail4.append("%s:%s" % (m["evidence_id"], "Y" if hit else "n"))
    last_ls = max(times)
    off_ok = False
    if brow:
        b = brow[0]
        if b["sim_status"] == "deactivated" and b["deactivation_date"] and not b["owner_record_id"]:
            dd = pt(b["deactivation_date"])
            off_ok = last_ls < dd <= last_ls + timedelta(hours=3)
        act_days = (min(times) - pt(brow[0]["activation_date"])).days
    else:
        act_days = -1
    noise = [norm_phone(x) for x in gt.get("extras", {}).get("noise_phones", [])]
    noise_near = {n: sum(1 for r in twr if norm_phone(r["phone_raw"]) == n) for n in noise}
    report("4. Burner near >=4 of 5 victims within 2 h before last-seen; deactivated within 3 h after last one",
           near >= 4 and off_ok and 8 <= act_days <= 12,
           "near %d/5 (%s), deactivation ok=%s, activated %d days before, noise rows=%s" % (
               near, " ".join(detail4), off_ok, act_days, list(noise_near.values())))

    # ---------------- 5. bait ----------------
    bait = norm_phone(gt["bait_phone"])
    ad1 = [a for a in tables["ads.csv"] if a["evidence_id"] == "AD-01"]
    ad_ok = bool(ad1) and norm_phone(ad1[0]["contact_phone"]) == bait
    ok5, d5 = 0, []
    for m in mps:
        vp = {p for p, o in phone_owner.items() if o == m["record_id"]}
        ls = pt(m["last_seen_time"])
        hit = any(norm_phone(c["caller_raw"]) in vp and norm_phone(c["callee_raw"]) == bait
                  and ls - timedelta(days=3) <= pt(c["timestamp"]) <= ls for c in calls)
        ok5 += hit
        d5.append(m["evidence_id"] + (":Y" if hit else ":n"))
    decoy_ads = all(norm_phone(a["contact_phone"]) != bait for a in tables["ads.csv"] if a["evidence_id"] != "AD-01")
    report("5. All 5 victims called the bait number (AD-01) in the 3 days before last-seen", ad_ok and ok5 == 5 and decoy_ads,
           "AD-01 matches bait=%s, victims %d/5 (%s), decoy ads use other numbers=%s" % (ad_ok, ok5, " ".join(d5), decoy_ads))

    # ---------------- 6. groups A/B never call ----------------
    A, B = set(gt["groups"]["A"]), set(gt["groups"]["B"])
    cross, intra_pairs = 0, defaultdict(int)
    for c in calls:
        x, y = phone2tid.get(norm_phone(c["caller_raw"])), phone2tid.get(norm_phone(c["callee_raw"]))
        if (x in A and y in B) or (x in B and y in A):
            cross += 1
        if x and y and x != y and ((x in A and y in A) or (x in B and y in B)):
            intra_pairs[tuple(sorted((x, y)))] += 1
    dense = sum(1 for g in (A, B) for p in combinations(sorted(g), 2) if 3 <= intra_pairs[p] <= 10)
    report("6. No call between any Group A member and any Group B member", cross == 0,
           "cross-group calls=%d; intra-group pairs with 3-10 calls: %d/20" % (cross, dense))

    # ---------------- 7. identities ----------------
    bg = [g for g in gt["identity_groups"] if g["person_id"] == gt["broker_person_id"]]
    broker_ok = bool(bg) and len(bg[0]["record_ids"]) == 3 and all(r in recs for r in bg[0]["record_ids"])
    names = [recs[r]["name"] for r in bg[0]["record_ids"]] if broker_ok else []
    dnm = gt["do_not_merge"]
    trap_ok = len(dnm) >= 1
    for a, b in dnm:
        ra, rb = recs.get(a), recs.get(b)
        if not (ra and rb and ra["name"].lower() == rb["name"].lower() and ra["dob"] != rb["dob"]
                and rec2tid.get(a) != rec2tid.get(b)):
            trap_ok = False
    report("7. Broker has 3 records in identity_groups; same-name trap pair is in do_not_merge", broker_ok and trap_ok,
           "broker records=%s; trap pair=%s" % (names, [(recs[a]["name"], recs[a]["dob"], recs[b]["dob"]) for a, b in dnm if a in recs and b in recs]))

    # ---------------- 8. pass-through ----------------
    pta = gt["pass_through_account"]
    ins = sorted([t for t in txns if t["to_account"] == pta], key=lambda t: t["timestamp"])
    outs = sorted([t for t in txns if t["from_account"] == pta], key=lambda t: t["timestamp"])
    used, pairs = set(), 0
    for i in ins:
        ti, ai = pt(i["timestamp"]), float(i["amount_inr"])
        for k, o in enumerate(outs):
            if k in used:
                continue
            dtm = (pt(o["timestamp"]) - ti).total_seconds() / 3600
            if 0 <= dtm <= 6 and abs(float(o["amount_inr"]) - ai) / ai <= 0.10:
                used.add(k)
                pairs += 1
                break
    chain = gt["money_chain"]
    edges = {(t["from_account"], t["to_account"]) for t in txns}
    chain_ok = all((chain[k], chain[k + 1]) in edges for k in range(len(chain) - 1)) or \
        all(any((chain[k], x) in edges for x in [chain[k + 1]]) for k in range(len(chain) - 1))
    report("8. Pass-through account has >=5 matched in/out pairs (<=10% amount, <=6 h); chain exists",
           pairs >= 5 and chain_ok, "matched pairs=%d, chain edges present=%s" % (pairs, chain_ok))

    # ---------------- 9. decoy ----------------
    deg = Counter()
    distinct = defaultdict(set)
    for c in calls:
        x, y = phone2tid.get(norm_phone(c["caller_raw"])), phone2tid.get(norm_phone(c["callee_raw"]))
        a, b = norm_phone(c["caller_raw"]), norm_phone(c["callee_raw"])
        for t, other in ((x, b), (y, a)):
            if t:
                deg[t] += 1
                distinct[t].add(other)
    decoy = gt["decoy_person_id"]
    ranked = deg.most_common(3)
    decoy_accts = {a for a, t in acct_tid.items() if t == decoy}
    d_tx = [t for t in txns if t["from_account"] in decoy_accts or t["to_account"] in decoy_accts]
    broker_deg = deg[gt["broker_person_id"]]
    ok9 = ranked and ranked[0][0] == decoy and not d_tx and deg[decoy] >= 60 and len(distinct[decoy]) >= 20 \
        and deg[decoy] >= 1.3 * broker_deg
    report("9. Decoy has the highest raw call degree and zero transfers", bool(ok9),
           "decoy calls=%d (%d numbers), broker=%d, next-highest=%s, decoy transfers=%d" % (
               deg[decoy], len(distinct[decoy]), broker_deg, ranked[1:], len(d_tx)))

    # ---------------- 10. ring vehicle toll ----------------
    plate = norm_plate(gt["ring_vehicle_plate"])
    inc0, inc1 = datetime(2026, 9, 27, 16), datetime(2026, 9, 28, 14)
    tr = tables["transit_logs.csv"]
    hits = [t for t in tr if t["kind"] == "toll" and norm_plate(t["plate_or_person_ref"]) == plate
            and t["direction"] == "out" and inc0 <= pt(t["timestamp"]) <= inc1
            and locs[t["location_id"]]["type"] == "toll"]
    veh_ok = any(norm_plate(v["plate_raw"]) == plate for v in tables["vehicles.csv"])
    ev_ok = any(h["evidence_id"] == gt["ring_vehicle_toll_evidence"] for h in hits)
    report("10. Ring vehicle has a toll 'out' row in the incident window", bool(hits) and veh_ok and ev_ok,
           "rows=%s, in vehicles.csv=%s, evidence id matches ground truth=%s" % (
               [h["evidence_id"] for h in hits], veh_ok, ev_ok))

    # ---------------- 11. co-traveler ----------------
    adult = gt["co_traveler_adult_record"]
    st = [s for s in tables["stays.csv"] if s["guest_record_id"] == adult]
    comps = set()
    for s in st:
        comps.update(x for x in s["companion_record_ids"].split(";") if x)
    adult_age = (datetime(2026, 9, 27) - pt(recs[adult]["dob"] + "T00:00:00")).days // 365 if adult in recs else 0
    comp_ages = [(datetime(2026, 9, 27) - pt(recs[c]["dob"] + "T00:00:00")).days // 365 for c in comps if c in recs]
    surnames = {recs[c]["name"].split()[-1] for c in comps if c in recs}
    ev_ok = set(gt["co_traveler_stay_evidence"]) <= {s["evidence_id"] for s in st}
    report("11. Co-traveler adult has >=3 stays with >=3 different companion records",
           len(st) >= 3 and len(comps) >= 3 and ev_ok and adult_age >= 18 and len(surnames) == len(comps),
           "stays=%d, distinct companions=%d, adult age=%d, companion ages=%s, distinct surnames=%d" % (
               len(st), len(comps), adult_age, sorted(comp_ages), len(surnames)))

    # ---------------- 12. determinism ----------------
    here_hash = hash_tree(D)
    gen = HERE / "generator.py"
    ok12, d12 = False, "generator.py not found next to validator"
    if gen.exists():
        try:
            outs12 = []
            for _ in range(2):
                tmp = tempfile.mkdtemp(prefix="sakshi_regen_")
                subprocess.run([sys.executable, str(gen), "--out", tmp], check=True, capture_output=True)
                outs12.append(hash_tree(tmp))
            ok12 = outs12[0] == here_hash and outs12[1] == here_hash
            d12 = "%d files hashed, two fresh regenerations %s the shipped data" % (
                len(here_hash), "match" if ok12 else "DIFFER from")
        except Exception as e:   # noqa: BLE001
            d12 = "regeneration failed: %s" % e
    report("12. Re-running generator.py (seed 42) produces byte-identical files", ok12, d12)

    # ---------------- extra checks ----------------
    print("\nExtra sanity checks")
    # X1 timestamps parse and sit inside the dataset window
    ts_cols = [("calls.csv", "timestamp"), ("transactions.csv", "timestamp"), ("tower_dump.csv", "timestamp"),
               ("transit_logs.csv", "timestamp"), ("stays.csv", "checkin"), ("stays.csv", "checkout"),
               ("missing_persons.csv", "last_seen_time"), ("missing_persons.csv", "reported_time"),
               ("ads.csv", "posted_time")]
    bad_ts, outside = 0, 0
    for fn, col in ts_cols:
        for r in tables[fn]:
            try:
                t = pt(r[col])
                if not (datetime(2026, 9, 1) <= t <= datetime(2026, 10, 1)):
                    outside += 1
            except ValueError:
                bad_ts += 1
    report("X1. All timestamps are ISO (no timezone) and inside 2026-09-01..30", bad_ts == 0 and outside == 0,
           "unparseable=%d, outside window=%d" % (bad_ts, outside))
    # X2 messy formats really present
    pf = Counter()
    for c in calls:
        for k in ("caller_raw", "callee_raw"):
            s = c[k]
            pf["plain" if re.fullmatch(r"\d{10}", s) else "+91" if s.startswith("+91 ") else "0-prefixed" if re.fullmatch(r"0\d{5} \d{5}", s) else "other"] += 1
    plf = Counter()
    for r in tables["persons_raw.csv"] + tables["vehicles.csv"]:
        s = r.get("vehicle_raw") or r.get("plate_raw") or ""
        if s:
            plf["compact" if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{2}\d{4}", s) else "lower-spaced" if re.fullmatch(r"[a-z]{2} \d{2} [a-z]{2} \d{4}", s) else "dashed" if re.fullmatch(r"[A-Z]{2}-\d{2}-[A-Z]{2}-\d{4}", s) else "other"] += 1
    report("X2. Messy phone and plate formats present", len(pf) >= 3 and pf["other"] == 0 and len(plf) >= 3 and plf["other"] == 0,
           "phones=%s plates=%s" % (dict(pf), dict(plf)))
    # X3 FIRs: 6-10 sentences, file text == joined sentence rows, victims' FIR has last-seen place/time
    sents = defaultdict(list)
    for r in tables["firs_sentences.csv"]:
        sents[r["doc_id"]].append(r)
    fir_ok = True
    for k in range(1, 11):
        doc = "FIR-%02d" % k
        rows = sorted(sents[doc], key=lambda r: int(r["sentence_idx"]))
        txt = (D / "firs" / ("FIR_%02d.txt" % k)).read_text(encoding="utf-8").strip()
        if not (6 <= len(rows) <= 10) or " ".join(r["text"] for r in rows) != txt:
            fir_ok = False
    miss_ok = True
    for i, m in enumerate(mps):
        t = pt(m["last_seen_time"]).strftime("%I:%M %p").lstrip("0")
        if t not in " ".join(r["text"] for r in sents[m["fir_ref"]]):
            miss_ok = False
    report("X3. FIR files: 6-10 sentences, match firs_sentences.csv; victim FIRs quote the last-seen time", fir_ok and miss_ok,
           "sentence counts=%s" % [len(sents["FIR-%02d" % k]) for k in range(1, 11)])
    # X4 referential integrity
    rec_ids = set(recs)
    ref_bad = 0
    ref_bad += sum(1 for r in tables["phones.csv"] if r["owner_record_id"] and r["owner_record_id"] not in rec_ids)
    ref_bad += sum(1 for r in tables["vehicles.csv"] if r["owner_record_id"] not in rec_ids)
    ref_bad += sum(1 for r in tables["accounts.csv"] if r["owner_record_id"] not in rec_ids)
    ref_bad += sum(1 for r in tables["missing_persons.csv"] if r["record_id"] not in rec_ids)
    ref_bad += sum(1 for r in tables["stays.csv"] if r["guest_record_id"] not in rec_ids
                   or any(x not in rec_ids for x in r["companion_record_ids"].split(";")))
    ref_bad += sum(1 for r in calls if r["tower_location_id"] not in locs)
    ref_bad += sum(1 for r in tables["tower_dump.csv"] if r["location_id"] not in locs)
    ref_bad += sum(1 for r in tables["transit_logs.csv"] if r["location_id"] not in locs)
    ref_bad += sum(1 for r in txns if (r["from_account"] not in acct_owner and r["from_account"] != "CASH") or r["to_account"] not in acct_owner)
    ref_bad += sum(1 for r in tables["persons_raw.csv"] if r["org_id"] and r["org_id"] not in {o["org_id"] for o in tables["orgs.csv"]})
    report("X4. Every foreign key points at an existing record, account, org or location", ref_bad == 0, "broken references=%d" % ref_bad)
    # X5 circular path + structuring + noise intersection
    ex = gt.get("extras", {})
    cyc = ex.get("circular_accounts", [])
    cyc_ok = len(cyc) == 3 and all((cyc[i], cyc[(i + 1) % 3]) in edges for i in range(3))
    split_ok = len(ex.get("structuring_evidence", [])) >= 3
    near_counts = defaultdict(set)
    for m in mps:
        ls = pt(m["last_seen_time"])
        for r in twr:
            L = locs[r["location_id"]]
            if ls - timedelta(hours=2) <= pt(r["timestamp"]) <= ls and hav(float(m["last_seen_lat"]), float(m["last_seen_lon"]), float(L["lat"]), float(L["lon"])) <= 1.5:
                near_counts[norm_phone(r["phone_raw"])].add(m["evidence_id"])
    top = sorted(((len(v), k) for k, v in near_counts.items()), reverse=True)[:3]
    unique_top = len(top) >= 2 and top[0][1] == burner and top[0][0] >= 4 and top[1][0] <= 2
    report("X5. Circular transfer path and structuring exist; burner is the only number near >=3 victims", cyc_ok and split_ok and unique_top,
           "cycle=%s, split transfers=%d, most-common numbers near victims=%s" % (cyc_ok, len(ex.get("structuring_evidence", [])), [(c, n[-4:]) for c, n in top]))
    # X6 ring structure: broker bridges A and B, victims silent after last-seen
    bt = gt["broker_person_id"]
    nb = defaultdict(set)
    for c in calls:
        x, y = phone2tid.get(norm_phone(c["caller_raw"])), phone2tid.get(norm_phone(c["callee_raw"]))
        if x and y:
            nb[x].add(y)
            nb[y].add(x)
    bridges = bool(nb[bt] & A) and bool(nb[bt] & B)
    vic_late = 0
    for m in mps:
        vp = {p for p, o in phone_owner.items() if o == m["record_id"]}
        ls = pt(m["last_seen_time"])
        vic_late += sum(1 for c in calls if (norm_phone(c["caller_raw"]) in vp or norm_phone(c["callee_raw"]) in vp) and pt(c["timestamp"]) > ls)
    report("X6. Broker calls both groups; victims' phones are silent after last-seen", bridges and vic_late == 0,
           "broker neighbours in A=%d, in B=%d; victim calls after last-seen=%d" % (len(nb[bt] & A), len(nb[bt] & B), vic_late))

    n_fail = sum(1 for _, ok in results if not ok)
    print("\nSummary: %d checks, %d passed, %d failed" % (len(results), len(results) - n_fail, n_fail))
    print("RESULT: %s" % ("ALL CHECKS PASSED" if n_fail == 0 else "VALIDATION FAILED"))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
