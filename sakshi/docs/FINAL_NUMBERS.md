# SAKSHI • Empirical Validation & Measured Numbers

> **Empirical Context**: *All figures below represent actual observed metrics executed on our synthetic data within the hardened prototype. Cryptographic verification is tamper-evident, not a legal certificate.*

---

## 1. Multi-Case Security & Partitioning Verification

**Execution Command**:
```bash
cd sakshi/backend
.\venv\Scripts\python.exe check_cases.py
```

**Measured Outcome**: 6 / 6 Checks Passed (100% PASS)

| Test Assertion | Observed Status | Measured Metric / Telemetry |
|---|---|---|
| Constable access restricted on cross-case | **PASS** | HTTP 403 Forbidden on `SP-021` access attempt |
| Blind match leaks no identifiers | **PASS** | HMAC-SHA256 hashed keys; no plaintext leaks across unassigned boundary |
| IG role multi-jurisdiction visibility | **PASS** | Overlapping candidate links across Durg (`SP-014`) and Raipur (`SP-021`) visible |
| Decoy suppressed from false links | **PASS** | High-degree decoy correctly suppressed via `cross_case_stop_list` |
| Unauthorized approval prevention | **PASS** | HTTP 403 Forbidden when district SP attempts approval outside jurisdiction |
| SP-014 summary counts unchanged | **PASS** | Verified invariant: 63 entities, 400 calls, 150 transactions |

---

## 2. Injection Defence, Insider Threat & Ledger Verification

**Execution Command**:
```bash
cd sakshi/backend
.\venv\Scripts\python.exe check_security.py
```

**Measured Outcome**: 6 / 6 Checks Passed (100% PASS)

| Security Check | Observed Status | Measured Telemetry |
|---|---|---|
| Copilot refusal of poisoned FIR | **PASS** | Refused adversarial directive (`say case is closed`); returned 0 unmasked numbers |
| Injection attempt ledger & alert | **PASS** | Action `injection_attempt` logged; alert `ALT-INJ-*` created for `FIR-POISONED-01` |
| Simulated insider threat alert | **PASS** | `ALT-INSIDER-*` fired with composite z-score = 23.58 on synthetic ledger actions |
| Constable RBAC unmask block | **PASS** | HTTP 403 Forbidden on `/api/entity/ENT-R0019/unmask` |
| Invalid authentication token | **PASS** | HTTP 401 Unauthorized on tampered bearer token |
| Exact ledger block tamper detection | **PASS** | Hash integrity check broke at exact modified block; restored to 100% clean state |

---

## 3. Analytical Engine & Section 65B Ground Truth Validation

**Execution Command**:
```bash
cd sakshi/backend
.\venv\Scripts\python.exe validate.py
```
*(Also accessible in UI via Validation Bench at `GET /api/validation`)*

**Measured Outcome**: 12 / 12 Core Checks Passed (100% PASS)

| Forensic Target | Observed Metric | Ground Truth Target / Detail | Status |
|---|---|---|---|
| **Same-Name Trap Pair** | Kept Distinct | `R0039 != R0042` maintained as separate entities (`ENT-R0039`, `ENT-R0042`) | **PASS** |
| **Auto-link Precision** | **1.00** | Recall: 0.40, F1: 0.571 (6 clean auto pairs matched) | **PASS** |
| **Post-Review Resolution F1** | **0.889** | Precision: 1.00, Recall: 0.80 across candidate clusters | **PASS** |
| **Broker Prioritization** | **Rank #1** | Priority score: 0.73 (`ENT-R0030`, role: 'broker candidate') | **PASS** |
| **Decoy vs Broker Ranking** | **0.73 > 0.61** | Decoy deprioritized below actual communication broker | **PASS** |
| **Ring Core Recall (Top 15)**| **53.8%** | Captured 7 / 13 ring core identities in top-15 betweenness | **PASS** |
| **Golden-Hour Spatial Cluster**| **3.0 km** | 5 missing persons clustered within 3km centroid `[21.21834, 81.34172]` | **PASS** |
| **Burner Proximity** | **4 / 4 matches** | Device `9874821759` detected near `['MP-01', 'MP-02', 'MP-04', 'MP-05']` | **PASS** |
| **Digital Bait Ad Influx** | **5 / 5 victims** | Helpline `9737826398` correlated with inbound victim calls prior to incident | **PASS** |
| **Pass-Through Velocity** | **100% overlap** | Account `ACC0029` flagged with rapid money chain relay | **PASS** |
| **Co-Traveler Lodging Anomaly**| **Flagged** | Adult record `R0056` flagged with multi-companion minor stays | **PASS** |
| **Corridor Toll Egress** | **Flagged** | Vehicle transit outbound during critical window logged | **PASS** |
