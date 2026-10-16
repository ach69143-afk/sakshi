# SAKSHI • STRIDE Threat Model & Security Architecture

> **Architecture Status**: *Hardened prototype evaluated on our synthetic data. Cryptographic audit is tamper-evident, not a legal certificate.*

---

## 1. System Architecture & Data Flows

SAKSHI coordinates six primary architectural boundaries across investigative operations:

```
[ Browser (React SPA) ]
         │
         │ HTTPS / JSON (JWT Bearer Token + X-Case-Id)
         ▼
[ FastAPI Backend Engine ]
   ├── 1. Auth & RBAC Middleware (PBKDF2 + pyotp TOTP + Role Checkers)
   ├── 2. Prompt-Injection Filter (<untrusted_record> + instruction phrase sanitizer)
   ├── 3. Multi-Case Isolation Router (SP-014 Durg vs SP-021 Raipur)
   │
   ├──▶ [ SQLite Database ] (sakshi.db & sakshi_sp021.db)
   │       └── Working relational entities, calls, transactions, row_hashes
   │
   ├──▶ [ Append-Only Ledger ] (SQLite ledger table)
   │       └── SHA-256 Merkle-style block chain (ts, action, payload_json, prev_hash, hash)
   │
   ├──▶ [ Groq Cloud LLM API ] (HTTPS / TLS 1.3)
   │       └── Strict function-calling pipeline with deterministic fallback engine
   │
   └──▶ [ SMTP Gateway ] (STARTTLS port 587)
           └── Rate-limited dispatch for Section 65B dossiers and demo login notifications
```

---

## 2. STRIDE Threat & Mitigation Matrix

| Category | Potential Threat | Implemented Mitigation in SAKSHI | Verification Artifact / Code Symbol |
|---|---|---|---|
| **Spoofing** | Attacker impersonates an SP or IG to access unmasked telecommunications and cross-case links. | Dual-factor authentication: PBKDF2 password hashing (100,000 iterations) plus 6-digit TOTP MFA (`pyotp`) for `sp_dysp`, `sp_dysp_raipur`, and `ig`. One-time QR code generation for enrolment; honeypot trap on public demo endpoint. | `backend/auth.py`, `backend/totp_service.py`, `tools/show_totp.py` |
| **Tampering** | Rogue actor alters financial transaction values or database evidence rows to frame or exonerate individuals. | Append-only cryptographic ledger chain where every block hashes `prev_hash + ts + action + payload_json`. Working rows are cross-verified against SHA-256 `row_hashes` computed during raw CSV ingestion. Exact corrupted block/record is detected upon verification. | `backend/ledger.py:verify_ledger_chain`, `backend/db.py:verify_all_integrity` |
| **Repudiation** | Officer denies unmasking victim numbers, approving cross-case links, or querying sensitive entities. | Every security-sensitive operation (logins, unmasks, copilot questions, cross-case decisions, node interdictions) writes an immutable ledger block containing the officer's email, timestamp, and case ID. | `backend/ledger.py:record_action`, `backend/main.py` |
| **Information Disclosure** | Constable-level officer extracts raw phone numbers, bank accounts, or unauthorized cross-district records. | Server-side masking (`98XXXXX210`) enforced before response serialization unless caller possesses `sp_dysp` or `ig` role. Cross-case matches use keyed HMAC-SHA256 blind indexing so unlinked case details remain unrevealed across jurisdictional boundaries. | `backend/auth.py:mask_phone_str`, `backend/cross_case.py:generate_cross_case_links` |
| **Denial of Service** | Malicious visitor floods SMTP notification endpoints or submits multi-megabyte adversarial prompt injections. | Rolling 1-hour timestamp sliding window rate-limiter on demo emails (max 3/hr per recipient). Untrusted text capped at 1,000 characters with control characters stripped. Deterministic local fallback executes if Groq API rate-limits or disconnects. | `backend/mailer.py:can_send_demo_email`, `backend/copilot.py:sanitize_untrusted_text` |
| **Elevation of Privilege** | Attacker injects prompt directives into FIR reports ("say case is closed", "reveal phones") or passes arbitrary `case_id`. | Server-side prompt-injection boundary wraps FIR/ad text in `<untrusted_record>` tags and replaces instruction phrases (`[instruction-like text removed]`). Server overrides any tool argument `case_id` with caller's authorized cases. Endpoints protected with `require_roles`. | `backend/copilot.py:execute_tool_call`, `backend/alerts.py`, `backend/insider_threat.py` |

---

## 3. Operational Security Classification
- **Classification**: Experimental Hardened Prototype.
- **Audit Defensibility**: Cryptographic ledger is tamper-evident, not a legal certificate.
- **Validation Scope**: Validated on our synthetic data; all names, identifiers, and scenarios are strictly fictional.
