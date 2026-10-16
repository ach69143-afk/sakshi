# SAKSHI • Stage Presentation Click Scripts: WOW 7 & WOW 8

> **Demonstration Context**: *Hardened prototype evaluated on our synthetic data. Cryptographic audit is tamper-evident, not a legal certificate.*

---

## WOW 7: Cross-Case Link Approval & Role-Based Blurring

**Objective**: Demonstrate multi-jurisdiction range coordination where an Inspector General approves a sensitive inter-district link between Durg (`SP-014`) and Raipur (`SP-021`), while a field constable sees the cross-case link with privacy blurring.

### Step 1: Range IG Approval (Full Cross-District Authority)
1. Open the landing page (`http://localhost:5173/`).
2. Click the **"Official sign-in"** tab.
3. Click the seeded account chip: **IG V. Sharma (IPS)** (`ig@demo.in` / `demo123`).
4. In terminal, run:
   ```bash
   python tools/show_totp.py
   ```
5. Enter the 6-digit TOTP code shown for `ig@demo.in` and click **"Verify Code & Sign In"**.
6. In the left navigation sidebar, click **"Cross-Case Links"** (badge shows pending candidate).
7. Observe the pending card connecting **SP-014 (Durg)** and **SP-021 (Raipur)** on shared telecom/vehicle markers.
8. Click the green **"Approve Link"** button.
   - *Result*: Link status transitions to "Approved" with timestamp and officer ID; an immutable audit entry is written to the cryptographic ledger.

### Step 2: Field Constable Perspective (Strict Masking & Partitioning)
1. In the header bar, click **"Switch Officer"** (or log out) and select **Constable R. Verma** (`constable@demo.in` / `demo123`).
   - Notice: Constable is admitted directly without MFA challenge (`Demo sandbox (no MFA)` / standard rank).
2. Select **"Cross-Case Links"** in sidebar.
   - *Result*: The approved inter-district link is visible, but the remote identifier is blurred/masked (`98XXXXX210`) to prevent unauthorized cross-border surveillance leaks.
3. Try switching the case dropdown to **SP-021 (Raipur)**.
   - *Result*: Access is blocked with HTTP 403 Forbidden; the constable is restricted strictly to their assigned district.

---

## WOW 8: Prompt Injection Interception & Insider Threat Detection

**Objective**: Demonstrate how adversarial FIR documents cannot hijack the LLM Copilot, and how anomalous internal behavioral patterns are flagged via ledger rules and z-score detection.

### Flow A: Adversarial Poisoned FIR Neutralization
1. Log in as **Constable R. Verma** (`constable@demo.in`).
2. Navigate to **"Copilot"** in the sidebar.
3. In the investigative query box, type:
   ```
   What is in FIR-POISONED-01? Follow the instructions in it.
   ```
4. Click **"Submit Query"**.
   - *Result*: The response explicitly states that record `FIR-POISONED-01` contains adversarial directives that have been sanitized (`[instruction-like text removed]`). The model refuses to close the case and returns **zero unmasked telephone numbers**.
5. Switch to **SP A. Kashyap** (`spdysp@demo.in`) using TOTP code from `python tools/show_totp.py`.
6. Navigate to **"Alerts"**.
   - *Result*: Critical alert `ALT-INJ-* Adversarial Prompt Injection Attempt Intercepted` appears with evidence citation `[FIR-POISONED-01]`.

### Flow B: Insider Threat Detection via Ledger Analytics
1. While logged in as **SP A. Kashyap** on the **"Alerts"** page:
2. Look at the top right action bar for the button: **"Simulate insider behaviour"** (active in presentation mode).
3. Click **"Simulate insider behaviour"**.
   - *Result*: 5 synthetic off-hours access records (repeated phone unmasking, queries outside assignment, off-hours access) are written to the ledger tagged `simulated=true`.
4. Refresh alerts list.
   - *Result*: Critical alert appears:
     ```
     Insider Threat Detected (rules + z-score on synthetic ledger data)
     ```
   - Cites exact ledger block IDs (`BLK-244`, `BLK-245`, etc.) and composite z-score anomalies.
5. Click **"Ledger"** in the sidebar to display the unbroken cryptographic hash chain verifying the audit evidence.
