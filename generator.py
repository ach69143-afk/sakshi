#!/usr/bin/env python3
"""
SAKSHI synthetic data generator -- Case SP-014: Durg Missing Cluster

ALL DATA IS FICTIONAL. Names, phone numbers, plates, accounts and events are invented.
Real Chhattisgarh / Maharashtra place names are used only as map context.

Usage:   python generator.py [--out DIR]       (default: ./sakshi/data next to this script)
Target:  Python 3.11, random seed 42 -> byte-identical output on every run.
"""
import argparse
import csv
import json
import math
import random
from datetime import date, datetime, timedelta
from itertools import combinations
from pathlib import Path

SEED = 42
FMT = "%Y-%m-%dT%H:%M:%S"
HERE = Path(__file__).resolve().parent
LETTERS = "ABCDEFGHJKLMNPRSTUVWXYZ"
TOWERS = ["L01", "L02", "L03", "L04", "L12"]

W0 = datetime(2026, 9, 1, 0, 0, 0)
W1 = datetime(2026, 9, 30, 23, 59, 59)
INC0 = datetime(2026, 9, 27, 16, 0, 0)
INC1 = datetime(2026, 9, 28, 14, 0, 0)


def dt(s):
    return datetime.strptime(s, FMT)


def ts(d):
    return d.strftime(FMT)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------------------
# Static world definition
# --------------------------------------------------------------------------------------
LOCATIONS = [
    ("L01", "Bhilai Civic Center", 21.2170, 81.3450, "tower"),
    ("L02", "Supela Market", 21.2205, 81.3395, "tower"),
    ("L03", "Kohka Chowk", 21.2055, 81.3330, "tower"),
    ("L04", "Smriti Nagar", 21.2290, 81.3470, "tower"),
    ("L05", "Durg Railway Station", 21.1900, 81.2830, "hub"),
    ("L06", "Toll Plaza near Durg (NH-53)", 21.1620, 81.2530, "toll"),
    ("L07", "Hotel Sunrise Lodge, Supela", 21.2185, 81.3410, "hotel"),
    ("L08", "Hotel Raj Palace, Durg", 21.1925, 81.2860, "hotel"),
    ("L09", "Raipur Bus Stand", 21.2370, 81.6310, "hub"),
    ("L10", "Nagpur Railway Station", 21.1520, 79.0880, "hub"),
    ("L11", "Nehru Nagar, Bhilai", 21.2120, 81.3640, "home"),
    ("L12", "Power House Chowk, Durg", 21.1970, 81.2920, "tower"),
]
LOC = {l[0]: l for l in LOCATIONS}

ORGS = [
    ("O01", "Shree Care Placement Services", "agency", "Bhilai"),
    ("O02", "Maa Danteshwari Travels", "transport", "Durg"),
    ("O03", "Gupta General Store", "shop", "Durg"),
    ("O04", "Bhilai Agro Trading Co.", "trading", "Bhilai"),
    ("O05", "City Cab Services", "transport", "Raipur"),
    ("O06", "Anand Stationers", "shop", "Bhilai"),
]

BANKS = ["Mahanadi Cooperative Bank", "Shivnath Gramin Bank", "Hasdeo Savings Bank",
         "Kharun Bank of Commerce", "Indrawati Urban Bank"]


def P(tid, name, dob, addr, role, group=None, org="", tower="L01", src="CDR"):
    return dict(tid=tid, name=name, dob=dob, addr=addr, role=role, group=group, org=org, tower=tower, src=src)


CAST = [
    P("T001", "Sureshchandra Rathore", "1984-06-11", "Plot 14, Nehru Nagar East, Bhilai", "broker", None, "O02", "L01", "BANK"),
    P("T002", "Dinesh Kumar Chandrakar", "1975-02-19", "H.No. 22, Sector 6, Bhilai", "leader", "leaders", "", "L02", "BANK"),
    P("T003", "Vikram Singh Thakur", "1979-09-03", "Camp-2, Durg", "leader", "leaders", "", "L12", "CDR"),
    P("T004", "Ramesh Sahu", "1986-12-01", "Near Supela Market, Bhilai", "recruiter", "A", "O01", "L02", "CDR"),
    P("T005", "Pooja Dewangan", "1993-04-22", "Kohka, Bhilai", "recruiter", "A", "O01", "L03", "BANK"),
    P("T006", "Karan Mishra", "1990-07-17", "Smriti Nagar, Bhilai", "spotter", "A", "", "L04", "HOTEL"),
    P("T007", "Sunil Netam", "1992-01-28", "Risali, Bhilai", "spotter", "A", "", "L01", "CDR"),
    P("T008", "Anita Verma", "1988-10-05", "Civic Center, Bhilai", "recruiter", "A", "O01", "L01", "BANK"),
    P("T009", "Prakash Yadav", "1983-03-30", "Power House Chowk, Durg", "driver", "B", "O02", "L12", "CDR"),
    P("T010", "Rohit Pandey", "1991-08-12", "Pulgaon, Durg", "transit", "B", "O02", "L12", "BANK"),
    P("T011", "Santosh Baghel", "1985-05-25", "Sector 3, Bhilai", "finance", "B", "O04", "L01", "BANK"),
    P("T012", "Harish Agrawal", "1980-11-14", "Station Road, Durg", "finance", "B", "O04", "L12", "BANK"),
    P("T013", "Deepak Sinha", "1989-06-09", "Dhamtari Road, Durg", "transit", "B", "O02", "L12", "CDR"),
    P("T014", "Mahesh Gupta", "1972-03-08", "Gupta General Store, Station Road, Durg", "decoy", None, "O03", "L12", "CDR"),
    P("T015", "Rahul Sharma", "1991-03-14", "Sector 9, Bhilai", "trap", None, "", "L01", "BANK"),
    P("T016", "Rahul Sharma", "1987-11-02", "Kumhari, Durg", "trap", None, "", "L12", "CDR"),
]

# tid, name, dob, tower, last_seen, address
VICTIMS = [
    ("T017", "Neha Kosre", "2007-02-20", "L01", "2026-09-27T17:10:00", "Ward 12, Nehru Nagar, Bhilai"),
    ("T018", "Riya Markam", "2009-05-12", "L02", "2026-09-27T21:40:00", "Basti near Supela Market, Bhilai"),
    ("T019", "Sangeeta Nishad", "2004-08-30", "L03", "2026-09-28T00:30:00", "Kohka Village Road, Bhilai"),
    ("T020", "Anjali Dhruv", "2006-01-09", "L04", "2026-09-28T07:15:00", "Smriti Nagar Colony, Bhilai"),
    ("T021", "Kiran Sonwani", "2002-06-15", "L01", "2026-09-28T13:20:00", "Sector 7, Bhilai"),
]
VICTIM_REPORTED = ["2026-09-27T22:30:00", "2026-09-28T08:00:00", "2026-09-28T09:00:00",
                   "2026-09-28T11:40:00", "2026-09-28T18:10:00"]
# minutes before last-seen that the burner appears on the tower (victims 1,2,4,5 only)
BURNER_MIN_BEFORE = {0: 70, 1: 85, 3: 95, 4: 80}

COMPANIONS = [
    ("T022", "Seema Kanwar", "2007-04-18", "Kumhari, Durg"),
    ("T023", "Lata Bhoyar", "2009-11-23", "Risali, Bhilai"),
    ("T024", "Mamta Ratre", "2008-07-05", "Pulgaon, Durg"),
    ("T025", "Jyoti Lahre", "2010-02-14", "Supela, Bhilai"),
]

MALE = ["Ajay", "Vijay", "Mukesh", "Rajesh", "Manoj", "Sandeep", "Anil", "Sanjay", "Ashok", "Naresh",
        "Lokesh", "Yogesh", "Tarun", "Pankaj", "Devendra", "Bhupendra", "Omprakash", "Hemant", "Nitin",
        "Gaurav", "Ravi", "Sachin", "Umesh", "Dilip", "Kamlesh", "Tikeshwar", "Jitendra", "Bhaskar"]
FEMALE = ["Sunita", "Meena", "Kavita", "Rekha", "Geeta", "Sarita", "Usha", "Poonam", "Shanti", "Radha",
          "Durga", "Bharti", "Chhaya", "Kamla", "Savita", "Parvati"]
SURNAMES = ["Sahu", "Verma", "Yadav", "Tiwari", "Patel", "Banjare", "Kurre", "Sinha", "Tandon", "Deshmukh",
            "Jain", "Soni", "Kashyap", "Thakur", "Agrawal", "Sharma", "Dewangan", "Netam", "Baghel",
            "Chandrakar", "Pandey", "Mishra", "Gupta", "Rathore", "Varma", "Sonwani", "Dhruv", "Nishad"]
ADDRS = ["Sector 6, Bhilai", "Sector 9, Bhilai", "Supela, Bhilai", "Kohka, Bhilai", "Smriti Nagar, Bhilai",
         "Risali, Bhilai", "Civic Center, Bhilai", "Nehru Nagar, Bhilai", "Power House, Durg",
         "Station Road, Durg", "Camp-1, Durg", "Pulgaon, Durg", "Kumhari, Durg", "Padmanabhpur, Durg",
         "Khursipar, Bhilai", "Maroda, Bhilai"]

# Alias records for hand-authored people.
# key, tid, name, dob, addr, src, phone_mode(same/new/none), plate_mode(same/new/none), org
ALIASES = [
    ("T001_a1", "T001", "Suresh Rathod", "", "Nehru Nagar, Bhilai", "FIR-08", "new", "new", "O02"),
    ("T001_a2", "T001", "Suresh alias Bhura", "", "", "FIR-09", "new", "new", "O02"),
    ("T002_a1", "T002", "D. K. Chandrakar", "1975-02-19", "Sector 6, Bhilai", "BANK", "new", "none", ""),
    ("T003_a1", "T003", "Vikram S. Thakur", "", "Camp 2, Durg", "BANK", "same", "none", ""),
    ("T004_a1", "T004", "Ramesh Kumar Sahoo", "", "Supela, Bhilai", "CDR", "new", "none", "O01"),
    ("T005_a1", "T005", "Puja Dewangan", "", "Kohka Bhilai", "CDR", "same", "none", ""),
    ("T006_a1", "T006", "K. Mishra", "", "Smriti Nagar", "FIR-07", "new", "none", ""),
    ("T009_a1", "T009", "P. Yadav", "", "Power House, Durg", "FIR-10", "same", "same", ""),
    ("T011_a1", "T011", "Santosh Bagel", "", "", "CDR", "new", "none", ""),
    ("T012_a1", "T012", "Harish Aggarwal", "1980-11-14", "Station Rd, Durg", "CDR", "same", "none", ""),
]


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def new_phone(rng, used, prefix=None):
    while True:
        if prefix:
            p = prefix + "".join(rng.choice("0123456789") for _ in range(10 - len(prefix)))
        else:
            p = rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))
        if p.startswith("98765") or p in used:
            continue
        used.add(p)
        return p


def new_plate(rng, used):
    while True:
        p = "CG%s%s%s%04d" % (rng.choice(["04", "07", "08", "10", "24"]), rng.choice(LETTERS),
                              rng.choice(LETTERS), rng.randint(1000, 9999))
        if p != "CG04AB1234" and p not in used:
            used.add(p)
            return p


def fmt_phone(d, rng):
    r = rng.random()
    if r < 0.40:
        return d
    if r < 0.75:
        return "+91 %s-%s" % (d[:5], d[5:])
    return "0%s %s" % (d[:5], d[5:])


def fmt_plate(c, rng):
    r = rng.random()
    if r < 0.34:
        return c
    if r < 0.67:
        return ("%s %s %s %s" % (c[:2], c[2:4], c[4:6], c[6:])).lower()
    return "%s-%s-%s-%s" % (c[:2], c[2:4], c[4:6], c[6:])


def rand_ts(rng, start, end, h0=7, h1=22):
    days = (end.date() - start.date()).days
    while True:
        d = start.date() + timedelta(days=rng.randint(0, days))
        t = datetime(d.year, d.month, d.day, rng.randint(h0, h1), rng.randint(0, 59), rng.randint(0, 59))
        if start <= t <= end:
            return t


def spelling_variant(name):
    for a, b in (("Sh", "S"), ("v", "w"), ("ee", "i"), ("u", "oo"), ("th", "t")):
        if a in name:
            return name.replace(a, b, 1)
    return name + "a"


def clock12(d):
    return d.strftime("%I:%M %p").lstrip("0")


def dmy(d):
    return d.strftime("%d/%m/%Y")


def age_on(dob, on):
    y, m, d = (int(x) for x in dob.split("-"))
    return on.year - y - ((on.month, on.day) < (m, d))


# --------------------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------------------
def build():
    rng = random.Random(SEED)
    used_phones, used_plates = set(), set()

    # ---------------- people ----------------
    people = [dict(p) for p in CAST]
    for tid, name, dob, tower, ls, addr in VICTIMS:
        people.append(P(tid, name, dob, addr, "victim", None, "", tower, "FIR-0%d" % (int(tid[1:]) - 16)))
    for tid, name, dob, addr in COMPANIONS:
        people.append(P(tid, name, dob, addr, "companion", None, "", "L12", "HOTEL"))

    used_names = {p["name"] for p in people}
    bg = []
    for i in range(35):
        if i == 0:
            name = "Jagdish Kurre"
        else:
            while True:
                first = rng.choice(MALE) if rng.random() < 0.55 else rng.choice(FEMALE)
                name = "%s %s" % (first, rng.choice(SURNAMES))
                if name not in used_names:
                    break
        used_names.add(name)
        dob = (date(1958, 1, 1) + timedelta(days=rng.randint(0, 16800))).isoformat()
        org = "O05" if i in (10, 11) else ("O06" if i == 12 else "")
        src = "FIR-08" if i == 0 else rng.choice(["CDR", "BANK", "HOTEL"])
        p = P("T%03d" % (26 + i), name, dob, "%s, %s" % (rng.randint(1, 99), rng.choice(ADDRS)),
              "background", None, org, rng.choice(TOWERS), src)
        bg.append(p)
        people.append(p)
    T = {p["tid"]: p for p in people}
    bg_tids = [p["tid"] for p in bg]

    # ---------------- records ----------------
    plate_owners = {"T001", "T003", "T004", "T009", "T010", "T012", "T014"} | {bg_tids[i] for i in range(5, 11)}
    vehicle_type = {"T001": "SUV", "T003": "SUV", "T004": "bike", "T009": "SUV", "T010": "tempo",
                    "T012": "car", "T014": "bike"}
    records = []
    phone_of = {}        # tid -> [digits, ...]
    plate_of = {}        # tid -> canonical plate of primary record
    phone_owner_key = {}  # digits -> record key

    def add_record(key, tid, name, dob, addr, src, phone, plate, org):
        records.append(dict(key=key, tid=tid, name=name, dob=dob, addr=addr, src=src, phone=phone,
                            plate=plate, org=org))

    for p in people:
        ph = new_phone(rng, used_phones)
        pl = new_plate(rng, used_plates) if p["tid"] in plate_owners else ""
        add_record(p["tid"], p["tid"], p["name"], p["dob"], p["addr"], p["src"], ph, pl, p["org"])
        phone_of[p["tid"]] = [ph]
        phone_owner_key[ph] = p["tid"]
        if pl:
            plate_of[p["tid"]] = pl

    alias_plates = {}
    for key, tid, name, dob, addr, src, pm, plm, org in ALIASES:
        if pm == "same":
            ph = phone_of[tid][0]
        else:
            ph = new_phone(rng, used_phones)
            phone_of[tid].append(ph)
            phone_owner_key[ph] = key
        if plm == "same":
            pl = plate_of[tid]
        elif plm == "new":
            pl = new_plate(rng, used_plates)
            alias_plates[key] = pl
        else:
            pl = ""
        add_record(key, tid, name, dob, addr, src, ph, pl, org)

    # background aliases
    bg_alias_specs = [
        (bg_tids[0], "J. Kurre", "", "", "BANK", "same"),
        (bg_tids[1], ("Shri " if T[bg_tids[1]]["name"].split()[0] in MALE else "Smt. ") + T[bg_tids[1]]["name"], "", "", "CDR", "same"),
        (bg_tids[2], spelling_variant(T[bg_tids[2]]["name"]), T[bg_tids[2]]["dob"], "", "BANK", "new"),
        (bg_tids[3], T[bg_tids[3]]["name"].split()[0][0] + ". " + T[bg_tids[3]]["name"].split()[-1], "", "", "HOTEL", "new"),
    ]
    for i, (tid, name, dob, addr, src, pm) in enumerate(bg_alias_specs, 1):
        key = "%s_a1" % tid
        if pm == "same":
            ph = phone_of[tid][0]
        else:
            ph = new_phone(rng, used_phones)
            phone_of[tid].append(ph)
            phone_owner_key[ph] = key
        add_record(key, tid, name, dob, addr, src, ph, "", "")

    ALIAS_TIDS = {}
    for r in records:
        ALIAS_TIDS.setdefault(r["tid"], []).append(r["key"])

    order = list(range(len(records)))
    rng.shuffle(order)
    rid_of = {}
    for n, idx in enumerate(order, 1):
        rid_of[records[idx]["key"]] = "R%04d" % n
    rec_by_key = {r["key"]: r for r in records}
    prim = {tid: rid_of[tid] for tid in T}       # primary record id per person

    # special numbers
    S1, S2, S3 = phone_of["T001"][0], phone_of["T001"][1], phone_of["T001"][2]
    BAIT = phone_of["T004"][1]
    BURNER = new_phone(rng, used_phones, prefix="98")
    NOISE1 = new_phone(rng, used_phones)
    NOISE2 = new_phone(rng, used_phones)
    home_tower = {}
    for tid, lst in phone_of.items():
        for d in lst:
            home_tower[d] = T[tid]["tower"]
    home_tower[BURNER] = "L12"
    home_tower[NOISE1] = "L01"
    home_tower[NOISE2] = "L02"
    tid_of_phone = {}
    for tid, lst in phone_of.items():
        for d in lst:
            tid_of_phone[d] = tid

    ph = lambda tid, k=0: phone_of[tid][k]       # noqa: E731
    GA = ["T004", "T005", "T006", "T007", "T008"]
    GB = ["T009", "T010", "T011", "T012", "T013"]
    LEADERS = ["T002", "T003"]
    RING = ["T001"] + LEADERS + GA + GB

    # ---------------- victims / missing persons ----------------
    mp = []
    victim_info = []
    for i, (tid, name, dob, tower, ls, addr) in enumerate(VICTIMS):
        lsd = dt(ls)
        lat = round(LOC[tower][2] + rng.uniform(-0.0012, 0.0012), 5)
        lon = round(LOC[tower][3] + rng.uniform(-0.0012, 0.0012), 5)
        rep = dt(VICTIM_REPORTED[i])
        mp.append(dict(eid="MP-%02d" % (i + 1), rid=prim[tid], name=name, age=age_on(dob, lsd), lat=lat, lon=lon,
                       ls=lsd, fir="FIR-%02d" % (i + 1), rep=rep))
        victim_info.append(dict(tid=tid, tower=tower, ls=lsd, idx=i, eid="MP-%02d" % (i + 1)))
    clat = round(sum(m["lat"] for m in mp) / 5, 5)
    clon = round(sum(m["lon"] for m in mp) / 5, 5)

    # ---------------- calls ----------------
    calls = []

    def mk_call(a, b, when, tower=None):
        if tower is None:
            tower = home_tower.get(a, "L01") if rng.random() < 0.7 else rng.choice(TOWERS)
        dur = min(1800, max(8, int(rng.lognormvariate(4.3, 0.9))))
        calls.append(dict(a=a, b=b, when=when, dur=dur, tower=tower))

    def ring_time():
        if rng.random() < 0.7:
            return rand_ts(rng, datetime(2026, 9, 2), datetime(2026, 9, 26, 23, 59, 59), 8, 23)
        return rand_ts(rng, datetime(2026, 9, 26), datetime(2026, 9, 28, 11, 59, 59), 8, 23)

    def pair_calls(x, y, n, xk=0, yk=0):
        for _ in range(n):
            if rng.random() < 0.5:
                mk_call(ph(x, xk), ph(y, yk), ring_time())
            else:
                mk_call(ph(y, yk), ph(x, xk), ring_time())

    for grp in (GA, GB):
        for x, y in combinations(grp, 2):
            pair_calls(x, y, rng.randint(3, 8))
    # leaders
    pair_calls("T002", "T003", 5)
    pair_calls("T002", "T011", 5)
    pair_calls("T002", "T012", 5)
    pair_calls("T002", "T009", 3)
    pair_calls("T003", "T004", 5)
    pair_calls("T003", "T006", 4)
    pair_calls("T003", "T007", 3)
    pair_calls("T003", "T009", 3)
    # broker: three faces, three phones, both groups + leaders
    pair_calls("T001", "T002", 6, 0, 0)
    pair_calls("T001", "T003", 4, 0, 0)
    for t, n in (("T004", 5), ("T006", 4), ("T008", 3)):
        pair_calls("T001", t, n, 1, 0)
    for t, n in (("T009", 5), ("T011", 4), ("T013", 3)):
        pair_calls("T001", t, n, 2, 0)

    # burner activity
    BURNER_ACT = dt("2026-09-17T12:10:00")
    BURNER_OFF = dt("2026-09-28T15:40:00")
    mk_call(BURNER, ph("T006"), dt("2026-09-18T20:15:00"), "L12")
    mk_call(BURNER, ph("T007"), dt("2026-09-21T18:40:00"), "L01")
    mk_call(BURNER, ph("T003"), dt("2026-09-24T22:05:00"), "L12")
    mk_call(ph("T006"), BURNER, dt("2026-09-26T15:30:00"), "L04")
    mk_call(BURNER, ph("T007"), dt("2026-09-27T15:20:00"), "L01")
    mk_call(BURNER, ph("T003"), dt("2026-09-28T14:05:00"), "L12")

    # victims: bait calls (+ one callback) and a few ordinary calls
    bg_phones = [ph(t) for t in bg_tids]
    for v in victim_info:
        vp = ph(v["tid"])
        ls = v["ls"]
        mk_call(vp, BAIT, ls - timedelta(hours=rng.randint(48, 66), minutes=rng.randint(0, 59)), v["tower"])
        mk_call(BAIT, vp, ls - timedelta(hours=rng.randint(26, 40), minutes=rng.randint(0, 59)), v["tower"])
        mk_call(vp, BAIT, ls - timedelta(hours=rng.randint(4, 20), minutes=rng.randint(0, 59)), v["tower"])
        for _ in range(3):
            friend = rng.choice(bg_phones)
            when = rand_ts(rng, W0, ls - timedelta(hours=2), 8, 21)
            if rng.random() < 0.5:
                mk_call(vp, friend, when, v["tower"])
            else:
                mk_call(friend, vp, when, v["tower"])

    # decoy shopkeeper: 70 calls, 25 different numbers, never in any money/vehicle/hotel/org link with the ring
    contacts = rng.sample(bg_phones, 24)
    counts = {c: 2 for c in contacts}
    for _ in range(70 - 2 - 48):
        counts[rng.choice(contacts)] += 1
    dk = ph("T014")
    for c in contacts:
        for _ in range(counts[c]):
            when = rand_ts(rng, W0, W1, 7, 21)
            tw = "L12" if rng.random() < 0.85 else rng.choice(TOWERS)
            if rng.random() < 0.4:
                mk_call(dk, c, when, tw)
            else:
                mk_call(c, dk, when, tw)
    for _ in range(2):   # one ordinary customer call from a group-A member
        mk_call(ph("T008"), dk, rand_ts(rng, W0, datetime(2026, 9, 24), 9, 20), "L01")

    # ring members phoning ordinary contacts (family etc.)
    for _ in range(12):
        r = rng.choice(RING)
        c = rng.choice(bg_phones)
        w = rand_ts(rng, W0, W1, 8, 22)
        if rng.random() < 0.5:
            mk_call(ph(r), c, w)
        else:
            mk_call(c, ph(r), w)

    # background noise to ~400 calls
    pool = bg_tids + ["T015", "T016"]
    pool_phones = [ph(t) for t in pool]
    deg = {}
    for c in calls:
        deg[c["a"]] = deg.get(c["a"], 0) + 1
        deg[c["b"]] = deg.get(c["b"], 0) + 1
    need = max(60, 400 - len(calls))
    made = 0
    while made < need:
        a, b = rng.sample(pool_phones, 2)
        if deg.get(a, 0) >= 22 or deg.get(b, 0) >= 22:
            continue
        mk_call(a, b, rand_ts(rng, W0, W1, 7, 22))
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
        made += 1
    calls.sort(key=lambda c: (c["when"], c["a"], c["b"]))

    # ---------------- accounts & transactions ----------------
    acct_owners = list(RING) + ["T014", "T015", "T016"] + bg_tids[:29]
    entries = [(t, rid_of[t]) for t in acct_owners] + [("T001", rid_of["T001_a1"])]
    rng.shuffle(entries)
    accounts = []
    acct_of = {}
    broker_acct2 = None
    for n, (tid, rid) in enumerate(entries, 1):
        aid = "ACC%04d" % n
        opened = (date(2012, 1, 1) + timedelta(days=rng.randint(0, 4800))).isoformat()
        accounts.append((aid, rid, opened, rng.choice(BANKS)))
        if tid == "T001" and rid == rid_of["T001_a1"]:
            broker_acct2 = aid
        else:
            acct_of[tid] = aid
    PT = acct_of["T011"]
    txns = []

    def tx(a, b, amt, when, ch, tag=""):
        txns.append(dict(a=a, b=b, amt=int(amt), when=when, ch=ch, tag=tag))

    pt_events = [(3, 11, 20, 38500, "T004"), (8, 15, 5, 52000, "T004"), (13, 10, 40, 45000, "T005"),
                 (18, 17, 15, 61000, "T004"), (23, 12, 30, 47500, "T005"), (26, 9, 50, 55000, "T004")]
    outs = []
    for k, (d, h, m, amt, snd) in enumerate(pt_events):
        t_in = datetime(2026, 9, d, h, m, rng.randint(0, 59))
        tx(acct_of[snd], PT, amt, t_in, "UPI", "PT_IN_%d" % k)
        t_out = t_in + timedelta(hours=rng.uniform(2.0, 5.5))
        t_out = t_out.replace(microsecond=0)
        amt_out = int(round(amt * rng.uniform(0.93, 0.97) / 100.0) * 100)
        tx(PT, acct_of["T001"], amt_out, t_out, "IMPS", "PT_OUT_%d" % k)
        outs.append(amt_out)
    # structuring: 4 split transfers into the pass-through account, one lump forwarded
    split_amts = [14500, 14900, 14700, 14800]
    for k, (mm, a) in enumerate(zip((5, 42, 10, 38), split_amts)):
        hh = 10 if mm in (5, 42) else 11
        tx(acct_of["T005"], PT, a, datetime(2026, 9, 15, hh, mm, rng.randint(0, 59)), "UPI", "SPLIT_%d" % k)
    tx(PT, acct_of["T001"], 55000, datetime(2026, 9, 15, 16, 20, 0), "IMPS", "SPLIT_FWD")
    # broker forwards in lumps to the financier after days (not rapid pass-through)
    tx(acct_of["T001"], acct_of["T002"], int(round((sum(outs[:3]) + 55000) * 0.96 / 100) * 100),
       datetime(2026, 9, 17, 12, 10, 0), "NEFT", "BROKER_FWD_1")
    tx(acct_of["T001"], acct_of["T002"], int(round(sum(outs[3:]) * 0.96 / 100) * 100),
       datetime(2026, 9, 29, 11, 0, 0), "NEFT", "BROKER_FWD_2")
    # circular path T010 -> T012 -> T003 -> T010
    tx(acct_of["T010"], acct_of["T012"], 30000, datetime(2026, 9, 20, 11, 0, 0), "IMPS", "CYCLE_1")
    tx(acct_of["T012"], acct_of["T003"], 29000, datetime(2026, 9, 20, 15, 30, 0), "IMPS", "CYCLE_2")
    tx(acct_of["T003"], acct_of["T010"], 28000, datetime(2026, 9, 21, 10, 0, 0), "IMPS", "CYCLE_3")
    # cash deposits kept just under the 50,000 mark
    for k, (d, h, a) in enumerate(((24, 11, 49000), (25, 10, 49000), (25, 16, 48000))):
        tx("CASH", acct_of["T002"], a, datetime(2026, 9, d, h, rng.randint(0, 59), 0), "cash-deposit", "CASHDEP_%d" % k)
    # complaint payment (see FIR_08): victim of job-fraud pays the broker's second account
    tx(acct_of[bg_tids[0]], broker_acct2, 12000, datetime(2026, 9, 11, 16, 20, 0), "UPI", "FIR08_PAY")
    # misc ring flows
    misc = [("T002", "T004", 20000, 5), ("T002", "T005", 15000, 5), ("T003", "T006", 5000, 10),
            ("T003", "T007", 5000, 10), ("T002", "T009", 10000, 12), ("T002", "T013", 8000, 12),
            ("T003", "T008", 6000, 14), ("T002", "T010", 7500, 16)]
    for a, b, amt, d in misc:
        tx(acct_of[a], acct_of[b], amt, datetime(2026, 9, d, rng.randint(10, 18), rng.randint(0, 59), 0), "UPI")
    for _ in range(3):    # ring members paying ordinary contacts
        r = rng.choice(["T004", "T007", "T009", "T013"])
        tx(acct_of[r], acct_of[rng.choice(bg_tids[:29])], rng.choice([500, 1200, 2500]),
           rand_ts(rng, W0, W1, 9, 21), "UPI")
    # ordinary background payments up to ~150 rows (decoy never appears here)
    bg_acct = [acct_of[t] for t in bg_tids[:29]] + [acct_of["T015"], acct_of["T016"]]
    need = max(60, 150 - len(txns))
    for _ in range(need):
        a, b = rng.sample(bg_acct, 2)
        r = rng.random()
        if r < 0.78:
            ch, amt = "UPI", rng.choice([50, 100, 120, 200, 250, 300, 450, 500, 750, 1000, 1500, 2000, 3500])
        elif r < 0.90:
            ch, amt = "IMPS", rng.choice([5000, 6500, 8000, 12000, 15000, 22000])
        elif r < 0.97:
            ch, amt = "NEFT", rng.choice([10000, 18000, 25000, 40000])
        else:
            tx("CASH", b, rng.choice([2000, 5000, 9000]), rand_ts(rng, W0, W1, 10, 17), "cash-deposit")
            continue
        tx(a, b, amt, rand_ts(rng, W0, W1, 9, 21), ch)
    txns.sort(key=lambda t: (t["when"], t["a"], t["b"], t["amt"]))

    # ---------------- tower dump ----------------
    tw = []   # dicts: phone, loc, when, tag

    def tower_row(phone, loc, when, tag=""):
        tw.append(dict(phone=phone, loc=loc, when=when, tag=tag))

    for v in victim_info:
        ls, t = v["ls"], v["tower"]
        tower_row(ph(v["tid"]), t, ls - timedelta(minutes=rng.randint(3, 20)), "VICTIM_OWN")
        if v["idx"] in BURNER_MIN_BEFORE:
            tower_row(BURNER, t, ls - timedelta(minutes=BURNER_MIN_BEFORE[v["idx"]]), "BURNER_NEAR_" + v["eid"])
    tower_row(NOISE1, victim_info[0]["tower"], victim_info[0]["ls"] - timedelta(minutes=40), "NOISE1")
    tower_row(NOISE1, victim_info[2]["tower"], victim_info[2]["ls"] - timedelta(minutes=55), "NOISE1")
    tower_row(NOISE2, victim_info[1]["tower"], victim_info[1]["ls"] - timedelta(minutes=100), "NOISE2")
    passers = rng.sample(bg_phones, 13)
    for k, p in enumerate(passers):
        v = victim_info[k % 5]
        tower_row(p, v["tower"], v["ls"] - timedelta(minutes=rng.randint(10, 110)), "PASSERBY")
    # burner elsewhere
    tower_row(BURNER, "L12", dt("2026-09-20T19:10:00"), "BURNER_BG")
    tower_row(BURNER, "L12", dt("2026-09-24T21:50:00"), "BURNER_BG")
    tower_row(BURNER, "L12", dt("2026-09-28T14:30:00"), "BURNER_BG")
    # background rows
    blocked = [(v["ls"] - timedelta(hours=3), v["ls"] + timedelta(hours=1)) for v in victim_info]
    all_phones = [d for t in phone_of for d in phone_of[t]]
    for _ in range(147):
        while True:
            when = rand_ts(rng, W0, W1, 0, 23)
            if not any(lo <= when <= hi for lo, hi in blocked):
                break
        tower_row(rng.choice(all_phones), rng.choice(TOWERS), when, "BG")
    tw.sort(key=lambda r: (r["when"], r["phone"], r["loc"]))

    # ---------------- transit ----------------
    RING_PLATE = plate_of["T009"]
    tr = []

    def tr_row(kind, ref, loc, when, direction, tag=""):
        tr.append(dict(kind=kind, ref=ref, loc=loc, when=when, dir=direction, tag=tag))

    tr_row("toll", ("plate", RING_PLATE), "L06", dt("2026-09-27T14:10:00"), "in", "RING_IN")
    tr_row("toll", ("plate", RING_PLATE), "L06", dt("2026-09-28T02:35:00"), "out", "RING_OUT")
    tr_row("toll", ("plate", RING_PLATE), "L06", dt("2026-09-29T06:20:00"), "in", "RING_BACK")
    bg_plate_tids = [bg_tids[i] for i in range(5, 11)] + ["T010", "T012", "T004"]
    tr_row("toll", ("plate", plate_of[bg_plate_tids[0]]), "L06", dt("2026-09-27T23:15:00"), "out", "DECOY_OUT")
    tr_row("toll", ("plate", plate_of[bg_plate_tids[1]]), "L06", dt("2026-09-28T05:40:00"), "out", "DECOY_OUT")
    for k in range(13):
        tid = bg_plate_tids[k % len(bg_plate_tids)]
        while True:
            when = rand_ts(rng, W0, W1, 5, 23)
            if not (INC0 <= when <= INC1):
                break
        tr_row("toll", ("plate", plate_of[tid]), "L06", when, "in" if k % 2 == 0 else "out")
    tr_row("train", ("rec", prim["T013"]), "L05", dt("2026-09-28T05:05:00"), "out", "STORY")
    tr_row("train", ("rec", prim["T013"]), "L10", dt("2026-09-28T10:00:00"), "in", "STORY")
    for k in range(5):
        tid = rng.choice(bg_tids)
        tr_row("train", ("rec", prim[tid]), rng.choice(["L05", "L10"]), rand_ts(rng, W0, W1, 5, 22), rng.choice(["in", "out"]))
    for k in range(5):
        tid = rng.choice(bg_tids)
        tr_row("bus", ("rec", prim[tid]), "L09", rand_ts(rng, W0, W1, 6, 21), rng.choice(["in", "out"]))
    tr.sort(key=lambda r: (r["when"], r["kind"]))

    # ---------------- hotel stays ----------------
    stays = []
    karan = prim["T006"]
    kcomp = [prim["T022"], prim["T023"], prim["T024"], prim["T025"]]
    for (d, loc, comp) in ((6, "L07", kcomp[0]), (11, "L08", kcomp[1]), (16, "L07", kcomp[2]), (23, "L07", kcomp[3])):
        cin = datetime(2026, 9, d, rng.randint(14, 19), rng.randint(0, 59), 0)
        cout = datetime(2026, 9, d + 1, rng.randint(7, 10), rng.randint(0, 59), 0)
        stays.append(dict(guest=karan, comp=comp, loc=loc, cin=cin, cout=cout, tag="KARAN"))
    g, c = prim[bg_tids[20]], prim[bg_tids[21]]
    for d in (4, 14, 24):   # a couple who always stay together (same companion every time)
        stays.append(dict(guest=g, comp=c, loc="L08", cin=datetime(2026, 9, d, 15, rng.randint(0, 59), 0),
                          cout=datetime(2026, 9, d + 1, 10, rng.randint(0, 59), 0), tag="COUPLE"))
    for k in range(8):
        gi, ci = rng.sample(range(len(bg_tids)), 2)
        d = rng.randint(1, 28)
        comps = prim[bg_tids[ci]]
        if rng.random() < 0.2:
            comps += ";" + prim[bg_tids[(ci + 1) % len(bg_tids)]]
        stays.append(dict(guest=prim[bg_tids[gi]], comp=comps, loc=rng.choice(["L07", "L08"]),
                          cin=datetime(2026, 9, d, rng.randint(13, 20), rng.randint(0, 59), 0),
                          cout=datetime(2026, 9, d + 1, rng.randint(7, 11), rng.randint(0, 59), 0), tag="BG"))
    stays.sort(key=lambda s: (s["cin"], s["guest"]))

    # ---------------- ads ----------------
    ads = [
        ("AD-01", "URGENT VACANCY: Front-office / reception staff (female, 18-25) for hotel & travel desk, Durg-Bhilai. "
                  "Salary Rs 28,000 + free stay. No experience needed. Shree Care Placement Services. Call now.",
         BAIT, dt("2026-09-19T10:30:00")),
        ("AD-02", "Home-based data entry work, Rs 12,000 per month, laptop not required. Contact Anand Stationers, Bhilai.",
         ph(bg_tids[12]), dt("2026-09-08T09:15:00")),
        ("AD-03", "Wanted: hospital receptionist and ward assistant, Sector 9 Bhilai. Walk-in interview Monday.",
         ph(bg_tids[13]), dt("2026-09-22T17:45:00")),
    ]

    return dict(rng=rng, T=T, records=records, rid_of=rid_of, prim=prim, phone_of=phone_of, plate_of=plate_of,
                phone_owner_key=phone_owner_key, alias_plates=alias_plates, BAIT=BAIT, BURNER=BURNER,
                BURNER_ACT=BURNER_ACT, BURNER_OFF=BURNER_OFF, NOISE1=NOISE1, NOISE2=NOISE2, S=(S1, S2, S3),
                calls=calls, accounts=accounts, acct_of=acct_of, broker_acct2=broker_acct2, PT=PT, txns=txns,
                tw=tw, tr=tr, stays=stays, ads=ads, mp=mp, clat=clat, clon=clon, RING=RING, GA=GA, GB=GB,
                LEADERS=LEADERS, bg_tids=bg_tids, vehicle_type=vehicle_type, RING_PLATE=RING_PLATE,
                bg_plate_tids=bg_plate_tids, victim_info=victim_info, ALIAS_TIDS=ALIAS_TIDS)


# --------------------------------------------------------------------------------------
# FIR text
# --------------------------------------------------------------------------------------
def make_firs(W, rng):
    T, prim, ph = W["T"], W["prim"], W["phone_of"]
    mp = W["mp"]
    S1, S2, S3 = W["S"]
    bait = W["BAIT"]
    fp = lambda d: fmt_phone(d, rng)         # noqa: E731
    fq = lambda c: fmt_plate(c, rng)         # noqa: E731
    ring = W["RING_PLATE"]
    firs = {}

    def vic(i):
        m = mp[i]
        return m, m["ls"], m["rep"]

    m, ls, rep = vic(0)
    firs["FIR-01"] = [
        "On %s at about %s, Smt. Savitri Kosre came to Supela Thana, Bhilai and reported that her daughter Neha Kosre, aged %d years, has gone missing since the evening of %s." % (dmy(rep), clock12(rep), m["age"], dmy(ls)),
        "She stated that Neha left home around 4:00 PM saying she was going to Bhilai Civic Center for a job interview, and was last seen near Civic Center at about %s on %s." % (clock12(ls), dmy(ls)),
        "Neha was wearing a yellow kurti with blue jeans and carrying a black sling bag.",
        "Ghar waalon ne uske mobile %s par baar baar call kiya, lekin phone switch off aa raha hai." % fp(ph["T017"][0]),
        "The mother further stated that Neha had been talking for a few days about a placement agency's front-office job offer and had saved the contact number %s in her phone." % fp(bait),
        "Neha ki saheli ne bataya ki woh is number par do-teen baar baat kar chuki thi aur ek baar interview ke liye bulaya gaya tha.",
        "No ransom or threatening call has been received by the family so far.",
        "The family has no enmity with anyone and Neha has never left home earlier without informing them.",
        "A missing person report was registered and a request was made to circulate her photograph to all police stations in Durg district.",
    ]
    m, ls, rep = vic(1)
    firs["FIR-02"] = [
        "On %s at about %s, Shri Bhagat Ram Markam, a labourer, informed Supela Thana that his minor daughter Riya Markam, aged %d years, did not return home after going out on the evening of %s." % (dmy(rep), clock12(rep), m["age"], dmy(ls)),
        "As per the complainant, Riya was last seen at about %s near Supela Market by a neighbour who was buying vegetables there." % clock12(ls),
        "She was wearing a green salwar suit with a pink dupatta and had a school bag with her.",
        "Uska mobile number %s usi raat se switch off hai." % fp(ph["T018"][0]),
        "Riya had told her elder sister that she was looking for part-time work to help with her fees.",
        "The complainant says Riya never stayed out at night earlier and has no relatives in other cities.",
        "Since the girl is a minor, a missing minor case has been registered and senior officers have been informed.",
        "Railway station and bus stand staff have been requested to check their CCTV footage.",
    ]
    m, ls, rep = vic(2)
    firs["FIR-03"] = [
        "On %s at about %s, Shri Gopal Nishad lodged a report at Supela Thana about his sister Sangeeta Nishad, aged %d years, who did not reach home last night." % (dmy(rep), clock12(rep), m["age"]),
        "Sangeeta works as a data-entry operator and was returning from a friend's birthday when she was last seen at Kohka Chowk at about %s by an autorickshaw driver." % clock12(ls),
        "She was wearing a black top, blue jeans and white sneakers.",
        "Bhai ne bataya ki Sangeeta ne pichle hafte ek job ad dekh kar %s par call kiya tha, jahan se use hotel reception ka kaam batakar interview ke liye bulaya gaya tha." % fp(bait),
        "Her mobile number %s has been unreachable since 12:45 AM." % fp(ph["T019"][0]),
        "The family has checked with friends and relatives in Bhilai and Raipur without success.",
        "The complainant fears that she may have been lured away on the pretext of employment.",
        "Investigation has been initiated and cameras in the area are being checked.",
    ]
    m, ls, rep = vic(3)
    firs["FIR-04"] = [
        "On %s at %s, Smt. Phulbasan Dhruv reported at Supela Thana that her daughter Anjali Dhruv, aged %d years, left for early morning coaching class and has not returned." % (dmy(rep), clock12(rep), m["age"]),
        "Anjali was last seen near Smriti Nagar crossing at about %s on %s by a shopkeeper who knows the family." % (clock12(ls), dmy(ls)),
        "The coaching institute informed that she did not attend class today.",
        "Uska phone %s band aa raha hai." % fp(ph["T020"][0]),
        "The mother states that Anjali had mentioned a job offer from an agency and had been in touch with the number %s for a few days." % fp(bait),
        "She was wearing a white kurta with red leggings and carrying a blue backpack.",
        "Anjali has no personal dispute and is not known to be in any relationship.",
        "Report registered; her photograph has been shared with all local police stations and Durg railway station.",
    ]
    m, ls, rep = vic(4)
    firs["FIR-05"] = [
        "On %s at %s, Shri Dayaram Sonwani lodged a missing person report at Supela Thana for his daughter Kiran Sonwani, aged %d years." % (dmy(rep), clock12(rep), m["age"]),
        "Kiran, a B.Com graduate, left home at 12:30 PM for a visit to Civic Center market and was last seen near Bhilai Civic Center at about %s." % clock12(ls),
        "Her friends told the family that she was applying for private jobs and had gone to meet some people about a position.",
        "Kiran ka mobile %s 2 baje ke baad se switch off hai." % fp(ph["T021"][0]),
        "She was wearing a maroon kurti with white palazzo and carrying a brown handbag.",
        "Kiran has never gone out of town alone and the family knows of no financial difficulty.",
        "The complainant requests urgent action as this is the fifth such missing report from the same area in the last 24 hours.",
        "Report registered and linked to the earlier missing reports for investigation.",
    ]
    firs["FIR-06"] = [
        "On 28/09/2026 at about 10:20 AM, Shri Mohan Lal Tandon, security guard of a commercial complex near Bhilai Civic Center, informed the police about a suspicious vehicle.",
        "He stated that on 27/09/2026 around 5:05 PM a white Bolero bearing registration %s remained parked near the Civic Center for almost an hour with its engine running." % fq(ring),
        "Two men were sitting in the front seats and kept looking at the girls passing through the market.",
        "When he asked them to move, the driver said he was waiting for a passenger and drove towards Supela.",
        "The guard noted the number as %s in his duty diary." % fq(ring),
        "He could not identify the men but said the driver was heavily built and wore a grey cap.",
        "The complainant offered to show the diary entry and the complex CCTV footage to the police.",
        "The vehicle number has been sent to the toll plaza and traffic police for checking.",
    ]
    karan_alias = W["phone_of"]["T006"][1]
    firs["FIR-07"] = [
        "On 25/09/2026 at 11:30 AM, Shri Ashok Rao, manager of Hotel Sunrise Lodge, Supela, submitted a written complaint at Supela Thana.",
        "He stated that a guest registering as K. Mishra (mobile %s) has stayed at the lodge three times in the last three weeks and each time brought a different young girl." % fp(karan_alias),
        "The girls looked below 18 years of age and the guest did not provide proper ID proof for them, saying they were his relatives.",
        "Hotel staff noticed that the girls appeared nervous and one of them was crying at the reception during the last visit.",
        "Manager ne bataya ki guest har baar cash mein payment karta hai aur subah jaldi nikal jata hai.",
        "The manager has preserved the hotel register and CCTV footage and requested police verification of the guest.",
        "No complaint has been made by any of the girls themselves.",
        "The statement was recorded and the guest's identity will be verified.",
    ]
    firs["FIR-08"] = [
        "On 12/09/2026 at about 12:00 noon, Shri Jagdish Kurre came to Supela Thana and reported that he was cheated in the name of a job placement.",
        "He stated that he paid Rs 12,000 as registration fee on 11/09/2026 by UPI to a person introduced as Suresh Rathod (mobile %s) who claimed to work with Shree Care Placement Services, Bhilai." % fp(S2),
        "He was promised a security supervisor job in Nagpur and told that the joining letter would be sent within three days.",
        "Jab usne dobara phone kiya to Suresh ne kaha ki abhi seat full hai aur paisa wapas nahi hoga.",
        "The complainant has screenshots of the UPI payment and the chat messages.",
        "He also heard from two other applicants that they were asked to deposit similar amounts.",
        "The accused is described as about 40 years old, of medium height, and moves around in a car with number %s." % fq(W["alias_plates"]["T001_a1"]),
        "Complaint registered as cheating and an enquiry has been started.",
    ]
    firs["FIR-09"] = [
        "On 29/09/2026 at 3:00 PM, Shri Lakhan Sinha, an autorickshaw driver at Durg railway station, gave a statement to the police.",
        "He stated that a man known locally as Bhura or Bhura bhaiya, whose real name he believes is Suresh, arranges rides and rooms for young girls who come from villages looking for work.",
        "He often sees Bhura bhaiya moving in a black Scorpio bearing number %s near the railway station and Hotel Raj Palace." % fq(W["plate_of"]["T001"]),
        "On 27/09/2026 at night he saw Bhura bhaiya talking on phone %s near the station and then driving away towards the highway." % fp(S3),
        "Usne bataya ki Bhura bhaiya ke saath kabhi kabhi do-teen log aur hote hain jo alag alag gaadiyon se aate hain.",
        "The witness is willing to identify Bhura bhaiya if shown.",
        "The statement was recorded and the witness was asked to inform the police if he sees the person again.",
        "The area beat staff have been asked to check the mentioned vehicle.",
    ]
    firs["FIR-10"] = [
        "On 28/09/2026 at about 12:00 noon, Shri Anil Tamrakar, supervisor at the toll plaza near Durg on NH-53, reported an unusual vehicle movement to the police.",
        "According to him, a white Bolero with number %s passed the plaza in the outward direction at about 2:35 AM on 28/09/2026 with all windows closed and curtains drawn." % fq(ring),
        "The same vehicle had entered towards Durg at about 2:10 PM on 27/09/2026.",
        "FASTag records show the vehicle is registered to one P. Yadav of Power House Chowk, Durg.",
        "Driver ne toll booth par cash mein payment kiya aur contact number %s likhwaya." % fp(ph["T009"][0]),
        "The toll staff noticed at least two passengers on the rear seats but could not see their faces.",
        "Toll CCTV footage for the night has been preserved for the police.",
        "The police have been requested to trace the vehicle and its owner.",
    ]
    return firs


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Generate the SAKSHI synthetic dataset (Case SP-014).")
    ap.add_argument("--out", default=str(HERE / "sakshi" / "data"))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "firs").mkdir(parents=True, exist_ok=True)

    W = build()
    rng = W["rng"]
    records, rid_of, T = W["records"], W["rid_of"], W["T"]
    fmt_rng = random.Random(SEED + 1)     # separate stream for cosmetic phone/plate formatting
    fph = lambda d: fmt_phone(d, fmt_rng)      # noqa: E731
    fpl = lambda c: fmt_plate(c, fmt_rng)      # noqa: E731

    # 1 persons_raw
    recs = sorted(records, key=lambda r: rid_of[r["key"]])
    pr_rows = []
    for n, r in enumerate(recs, 1):
        pr_rows.append([rid_of[r["key"]], "PR-%04d" % n, r["name"], r["dob"], r["addr"], r["src"],
                        fph(r["phone"]) if r["phone"] else "", fpl(r["plate"]) if r["plate"] else "", r["org"]])
    write_csv(out / "persons_raw.csv", ["record_id", "evidence_id", "name", "dob", "address", "source_doc",
                                        "phone_raw", "vehicle_raw", "org_id"], pr_rows)

    # 2 phones
    ph_list = []
    for d, key in W["phone_owner_key"].items():
        ph_list.append((d, rid_of[key], "active", "", "", None))
    owned = {p[0] for p in ph_list}
    ph_list.append((W["BURNER"], "", "deactivated", W["BURNER_ACT"], W["BURNER_OFF"], None))
    ph_list.append((W["NOISE1"], "", "active", "", "", None))
    ph_list.append((W["NOISE2"], "", "active", "", "", None))
    ph_list.sort(key=lambda x: (x[0] != W["BURNER"], x[0]))
    # stable order: by digits, burner not first (avoid making it obvious)
    ph_list.sort(key=lambda x: x[0])
    ph_rows = []
    for n, (d, owner, st, act, deact, _) in enumerate(ph_list, 1):
        if not act:
            act = datetime(2018, 1, 1) + timedelta(days=rng.randint(0, 2800))
        imei = "".join(rng.choice("0123456789") for _ in range(15))
        ph_rows.append(["PH-%04d" % n, fph(d), owner, st, ts(act),
                        ts(deact) if deact else "", imei])
    write_csv(out / "phones.csv", ["evidence_id", "phone_raw", "owner_record_id", "sim_status", "activation_date",
                                   "deactivation_date", "imei"], ph_rows)

    # 3 vehicles
    veh = []
    for r in recs:
        if r["plate"] and (r["key"] in T or r["key"] in W["alias_plates"]):
            if r["tid"] == "T009" and r["key"] != "T009":
                continue
            vt = W["vehicle_type"].get(r["tid"], rng.choice(["car", "bike", "auto", "bike"]))
            if r["key"] in ("T001_a1",):
                vt = "car"
            if r["key"] in ("T001_a2",):
                vt = "scooter"
            veh.append((r["plate"], rid_of[r["key"]], vt))
    veh_rows = [["VH-%04d" % n, fpl(p), o, v] for n, (p, o, v) in enumerate(veh, 1)]
    write_csv(out / "vehicles.csv", ["evidence_id", "plate_raw", "owner_record_id", "vehicle_type"], veh_rows)

    # 4 orgs, 5 locations
    write_csv(out / "orgs.csv", ["org_id", "name", "type", "city"], [list(o) for o in ORGS])
    write_csv(out / "locations.csv", ["location_id", "name", "lat", "lon", "type"],
              [[a, b, "%.5f" % c, "%.5f" % d, e] for a, b, c, d, e in LOCATIONS])

    # 6 calls
    call_rows = [["CDR-%04d" % n, fph(c["a"]), fph(c["b"]), ts(c["when"]), c["dur"], c["tower"]]
                 for n, c in enumerate(W["calls"], 1)]
    write_csv(out / "calls.csv", ["evidence_id", "caller_raw", "callee_raw", "timestamp", "duration_sec",
                                  "tower_location_id"], call_rows)

    # 7 accounts / 8 transactions
    write_csv(out / "accounts.csv", ["account_id", "owner_record_id", "opened_date", "bank_name"],
              [list(a) for a in W["accounts"]])
    tx_rows, tx_tag = [], {}
    for n, t in enumerate(W["txns"], 1):
        eid = "TXN-%04d" % n
        tx_rows.append([eid, t["a"], t["b"], t["amt"], ts(t["when"]), t["ch"]])
        if t["tag"]:
            tx_tag[t["tag"]] = eid
    write_csv(out / "transactions.csv", ["evidence_id", "from_account", "to_account", "amount_inr", "timestamp",
                                         "channel"], tx_rows)

    # 9 tower dump
    tw_rows = [["TWR-%04d" % n, fph(r["phone"]), r["loc"], ts(r["when"])] for n, r in enumerate(W["tw"], 1)]
    write_csv(out / "tower_dump.csv", ["evidence_id", "phone_raw", "location_id", "timestamp"], tw_rows)

    # 10 transit
    tr_rows, tr_tag = [], {}
    for n, r in enumerate(W["tr"], 1):
        eid = "TR-%04d" % n
        ref = fpl(r["ref"][1]) if r["ref"][0] == "plate" else r["ref"][1]
        tr_rows.append([eid, r["kind"], ref, r["loc"], ts(r["when"]), r["dir"]])
        if r["tag"]:
            tr_tag.setdefault(r["tag"], []).append(eid)
    write_csv(out / "transit_logs.csv", ["evidence_id", "kind", "plate_or_person_ref", "location_id", "timestamp",
                                         "direction"], tr_rows)

    # 11 stays
    st_rows, karan_ev = [], []
    for n, s in enumerate(W["stays"], 1):
        eid = "HT-%04d" % n
        st_rows.append([eid, s["guest"], s["comp"], s["loc"], ts(s["cin"]), ts(s["cout"])])
        if s["tag"] == "KARAN":
            karan_ev.append(eid)
    write_csv(out / "stays.csv", ["evidence_id", "guest_record_id", "companion_record_ids", "hotel_location_id",
                                  "checkin", "checkout"], st_rows)

    # 12 missing persons / 13 ads
    write_csv(out / "missing_persons.csv", ["evidence_id", "record_id", "name", "age", "last_seen_lat",
                                            "last_seen_lon", "last_seen_time", "fir_ref", "reported_time"],
              [[m["eid"], m["rid"], m["name"], m["age"], "%.5f" % m["lat"], "%.5f" % m["lon"], ts(m["ls"]),
                m["fir"], ts(m["rep"])] for m in W["mp"]])
    write_csv(out / "ads.csv", ["evidence_id", "ad_text", "contact_phone", "posted_time"],
              [[a, t, fph(p), ts(w)] for a, t, p, w in W["ads"]])

    # 14 FIRs
    firs = make_firs(W, fmt_rng)
    sent_rows = []
    for k in range(1, 11):
        doc = "FIR-%02d" % k
        sents = firs[doc]
        with open(out / "firs" / ("FIR_%02d.txt" % k), "w", encoding="utf-8", newline="") as f:
            f.write(" ".join(sents) + "\n")
        for i, s in enumerate(sents, 1):
            sent_rows.append(["%s-S%d" % (doc, i), doc, i, s])
    write_csv(out / "firs_sentences.csv", ["evidence_id", "doc_id", "sentence_idx", "text"], sent_rows)

    # 15 ground truth
    ids = {}
    for r in records:
        ids.setdefault(r["tid"], []).append(rid_of[r["key"]])
    roles = {t: T[t]["role"] for t in T}
    roles["T001"] = "broker"
    groups = [{"person_id": t, "record_ids": sorted(v), "role": roles[t]} for t, v in sorted(ids.items())]
    pt_pairs = []
    for k in range(6):
        pt_pairs.append([tx_tag["PT_IN_%d" % k], tx_tag["PT_OUT_%d" % k]])
    gt = {
        "seed": SEED,
        "case": "SP-014 Durg Missing Cluster",
        "identity_groups": groups,
        "do_not_merge": [[rid_of["T015"], rid_of["T016"]]],
        "ring_members": W["RING"],
        "groups": {"A": W["GA"], "B": W["GB"], "leaders": W["LEADERS"]},
        "broker_person_id": "T001",
        "pass_through_account": W["PT"],
        "money_chain": [W["acct_of"]["T004"], W["PT"], W["acct_of"]["T001"], W["acct_of"]["T002"]],
        "golden_hour": {"missing_ids": [m["eid"] for m in W["mp"]], "centroid": [W["clat"], W["clon"]],
                        "radius_km": 3, "window_hours": 24},
        "burner_phone": W["BURNER"],
        "burner_seen_near": [m["eid"] for i, m in enumerate(W["mp"]) if i in BURNER_MIN_BEFORE],
        "bait_phone": W["BAIT"],
        "ring_vehicle_plate": W["RING_PLATE"],
        "ring_vehicle_toll_evidence": tr_tag["RING_OUT"][0],
        "co_traveler_adult_record": W["prim"]["T006"],
        "co_traveler_stay_evidence": karan_ev,
        "decoy_person_id": "T014",
        "extras": {
            "noise_phones": [W["NOISE1"], W["NOISE2"]],
            "decoy_ad_phones": [W["ads"][1][2], W["ads"][2][2]],
            "trap_person_ids": ["T015", "T016"],
            "victim_person_ids": [v["tid"] for v in W["victim_info"]],
            "circular_accounts": [W["acct_of"]["T010"], W["acct_of"]["T012"], W["acct_of"]["T003"]],
            "structuring_evidence": [tx_tag["SPLIT_%d" % k] for k in range(4)],
            "pass_through_pairs": pt_pairs,
            "broker_phones": list(W["S"]),
            "broker_second_account": W["broker_acct2"],
        },
    }
    with open(out / "ground_truth.json", "w", encoding="utf-8", newline="") as f:
        json.dump(gt, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")

    print("Wrote dataset to %s" % out)
    print("  persons_raw=%d phones=%d vehicles=%d orgs=%d locations=%d calls=%d accounts=%d txns=%d" % (
        len(pr_rows), len(ph_rows), len(veh_rows), len(ORGS), len(LOCATIONS), len(call_rows),
        len(W["accounts"]), len(tx_rows)))
    print("  tower_dump=%d transit=%d stays=%d missing=%d ads=%d firs=10" % (
        len(tw_rows), len(tr_rows), len(st_rows), len(W["mp"]), len(W["ads"])))


if __name__ == "__main__":
    main()
