# SAKSHI synthetic dataset: Case SP-014 "Durg Missing Cluster"

**ALL DATA IS FICTIONAL.** Names, phone numbers, plates, accounts and events are invented. Real Chhattisgarh/Maharashtra place names are only map context; the events never happened.

## Run it
```
python generator.py          # writes sakshi/data/ (seed 42, deterministic, standard library only)
python validate_dataset.py   # prints PASS/FAIL for the 12 required checks + 6 extra sanity checks
```
`generator.py --out DIR` writes somewhere else (the validator uses this to check determinism). Written for Python 3.11; tested on 3.12. No third-party packages.

## Files (all UTF-8 CSV, header row, timestamps like `2026-09-27T18:45:00`, IST, no timezone)
| File | What it holds |
|---|---|
| `persons_raw.csv` | 74 person records for 60 real identities. Aliases and spelling variants create the extra records. `source_doc` says which document the record came from. Phones and plates are deliberately messy. |
| `phones.csv` | 71 numbers with owner record, SIM status, activation/deactivation and IMEI. The burner and two noise numbers have no owner. |
| `vehicles.csv` | 15 vehicles (plates in mixed formats) and their owner record. |
| `orgs.csv` | 6 organisations (agency, transport, shop, trading). |
| `locations.csv` | 12 places with approximate lat/lon: 5 towers, 2 hotels, 1 toll, 3 hubs, 1 home. |
| `calls.csv` | 400 CDR rows with the tower the caller was on. |
| `accounts.csv` | 46 accounts at fictional banks. |
| `transactions.csv` | 150 transfers (UPI/IMPS/NEFT/cash-deposit). Cash deposits use `from_account = CASH`. |
| `tower_dump.csv` | 175 rows: 25 around the victims' last-seen points, 150 background. |
| `transit_logs.csv` | 30 toll, train and bus rows. Toll rows reference a plate, train/bus rows reference a record_id. |
| `stays.csv` | 15 hotel stays with semicolon-separated companion record ids. |
| `missing_persons.csv` | 5 missing women (ages 17-24) with last-seen point/time and FIR reference. |
| `ads.csv` | 3 fake job ads (1 bait, 2 decoys). |
| `firs/FIR_01..10.txt` | 10 FIR texts, 8-9 sentences each, English with some Hinglish. |
| `firs_sentences.csv` | The same FIRs split into sentences. `evidence_id` is `FIR-03-S2` (FIR 3, sentence 2), `doc_id` is `FIR-03`. |
| `ground_truth.json` | Hidden answer key. **Never load it in the app; validation only.** |

## The hidden story
- **Five missing persons.** FIR_01..05, all last seen within 3 km of Bhilai Civic Center between 27 Sep 17:10 and 28 Sep 13:20 (20 h span).
- **Burner number.** SIM activated 17 Sep, appears on the tower near 4 of the 5 victims (not MP-03) 70-95 minutes before each disappearance, deactivated at 15:40 on 28 Sep. Two noise numbers appear near 1-2 victims only.
- **Job-ad bait.** All 5 victims call the number in ad AD-01 within 3 days before vanishing. AD-02/AD-03 are decoys. The bait number belongs to a recruiter's second SIM.
- **The ring.** Group A (5 recruiters/spotters), Group B (5 transit/finance), 2 leaders, plus the broker. A and B never call each other; calls inside each group are dense (3-8 per pair).
- **The broker.** One person, three records ("Sureshchandra Rathore", "Suresh Rathod", "Suresh alias Bhura") with different phones and plates. The shared link is the same organisation (O02). He calls both groups. Trap: two different "Rahul Sharma" records (different DOB and city) must not be merged.
- **Money.** Recruiter, pass-through account, broker, financier. The pass-through account forwards 93-97% of each deposit 2-5.5 h later, 6 times. Also 4 split transfers, a 3-account circular path, and 3 cash deposits just under 50,000.
- **Transit.** The ring vehicle (a white Bolero) is logged "out" at the Durg toll at 02:35 on 28 Sep. One adult (Karan Mishra) has 4 hotel stays with 4 different young women/minors, with different surnames, in the previous 3 weeks.
- **Decoy.** Shopkeeper Mahesh Gupta: 70 calls with 25 different numbers, no transfers, and no shared vehicle/hotel/org with the ring. The broker has 36 calls.
- **Noise.** About 35 unrelated people with random calls, small UPI payments and random tower rows.

## Counts (actual)
persons_raw 74 (60 identities), phones 71, vehicles 15, orgs 6, locations 12, calls 400, accounts 46, transactions 150, tower_dump 175, transit_logs 30, stays 15, missing_persons 5, ads 3, FIR files 10.

## Notes for backend/frontend
- `activation_date` / `deactivation_date` in `phones.csv` hold full ISO timestamps, not just dates (the burner needs the hour).
- `orgs.csv`, `locations.csv` and `accounts.csv` have no `evidence_id` column because the brief fixes their exact columns. They use `org_id`, `location_id` and `account_id`.
- `ground_truth.json` has the brief's keys plus `case` and an `extras` block (noise phones, decoy ad phones, trap people, circular accounts, split-transfer evidence, pass-through pairs). `identity_groups` lists all 60 people, not only the multi-record ones.
- Toll/transit evidence ids are `TR-xxxx` as in the task spec (the project brief's examples say `TOLL-007`).
