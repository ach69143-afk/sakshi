# SAKSHI • Criminal Network Intelligence Workbench

> **Defensible Legal Notice**: *Synthetic data. Patterns for investigator review. Not an accusation.*

SAKSHI is an evidence-defensible criminal network intelligence workbench designed for multi-modal crime pattern correlation, golden-hour spatial triangulation, rapid pass-through financial relay detection, and alias reconciliation under Section 65B of the Indian Evidence Act.

---

## 🚀 Quick Start (Running Locally)

### 1. Backend (FastAPI Mock Server)

```bash
# Navigate to backend
cd sakshi/backend

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Run FastAPI server on port 8000
uvicorn main:app --reload --port 8000
```
Backend API will be accessible at: `http://127.0.0.1:8000`
Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

---

### 2. Frontend (Vite + React + Tailwind + Cytoscape + Leaflet)

```bash
# In a new terminal, navigate to frontend
cd sakshi/frontend

# Install dependencies (already installed in workspace)
npm install

# Start Vite dev server on port 5173
npm run dev
```
Frontend will be accessible at: `http://localhost:5173/`
*(Vite is configured to automatically proxy all `/api` calls to `http://127.0.0.1:8000`)*

---

## 👥 Seed Demo Accounts

All demo accounts use password: `demo123`

| Email | Name | Role | Permitted Actions & Permissions |
|---|---|---|---|
| `spdysp@demo.in` | SP A. Kashyap (IPS) | `sp_dysp` | **Full access**: Approve merges, simulate interdiction shatter, unmasked raw phone numbers, audit verification, Section 65B report export (TOTP MFA enabled) |
| `spraipur@demo.in` | SP R. Sen (IPS) | `sp_dysp_raipur` | **Raipur SP access**: SP-021 case administration, unmasking, Section 65B export (TOTP MFA enabled) |
| `ig@demo.in` | IG P. Agrawal (IPS) | `ig` | **Range Commander**: Multi-case oversight (SP-014 + SP-021), cross-case link approvals (TOTP MFA enabled) |
| `cybercell@demo.in` | Insp. P. Nayak (Cyber) | `cyber_cell` | Cross-case analysis, interdiction shatter, inspect ledger & tamper demo, report generation |
| `headconstable@demo.in` | HC S. Deshmukh | `head_constable` | Simulate interdiction shatter, report generation, masked phone numbers |
| `constable@demo.in` | Constable R. Verma | `constable` | Standard intelligence viewing, masked phone numbers (`+91 98XXXXX021`), simulation & merge approval restricted |
| `auditor@demo.in` | Auditor M. Raman | `auditor` | Chain of custody audit, insider threat monitoring, tamper verification |

### Multi-Factor Authentication (TOTP)
- **High-Privilege Roles**: `sp_dysp`, `sp_dysp_raipur`, and `ig` are protected by 6-digit TOTP two-factor authentication on the Official sign-in tab.
- **Presenter Tool**: Run `python tools/show_totp.py` to view current 6-digit codes and active keys for live presentation.
- **Secret Storage Note**: For this prototype, TOTP shared secrets are stored in the SQLite database (`user_totp` table) in plaintext. In an operational production deployment, secrets would be encrypted under an HSM or enveloped with KMS keys.
- **Demo Sandbox**: The landing page public demo sandbox is exempt and labeled `Demo sandbox (no MFA)`.

---

## 📂 Repository Structure

```
sakshi/
  backend/
    main.py             # FastAPI app with RBAC middleware, phone masking & endpoints
    requirements.txt    # Python dependencies
    venv/               # Virtual environment (Python 3.11)
    mock/               # Seed datasets matching target production schema
      case.json         # Case header (persons, calls, txns, alerts)
      graph.json        # 45 nodes, 90 edges with topological clusters
      entities.json     # Detailed entity breakdown, centrality metrics & citations
      edge_explanations.json # Multi-component score formulas & FIR excerpts
      merge_queue.json  # Probabilistic alias record clusters
      alerts.json       # Triage alerts (bridge, golden hour, pass-through)
      golden_hour.json  # Spatial centroid & burner/bait telemetry
      simulation.json   # Articulation point shatter baseline metrics
      ledger.json       # 20 cryptographically chained SHA-256 blocks
      copilot.json      # Grounded Q&A with evidentiary citations
  frontend/
    src/
      api.js            # Unified API client (single place to swap base URL)
      context/AuthContext.jsx # RBAC state & seamless role switcher
      components/
        Layout.jsx      # Workbench shell, top bar, role menu, audit badge & footer banner
        EvidenceModal.jsx # Interactive Section 65B evidence transcript drawer
      pages/
        Login.jsx       # Quick-fill demo role chips
        Dashboard.jsx   # Metrics, active anomalies & workflow shortcuts
        Network.jsx     # Cytoscape graph canvas, shatter simulation, edge why & timeline
        MergeQueue.jsx  # Side-by-side alias cards & SP/DySP merge approval
        GoldenHour.jsx  # Leaflet dark map, 3km circle & burner telemetry
        Alerts.jsx      # Severity triage & pattern explanations
        AskCopilot.jsx  # Evidentiary Copilot with clickable evidence citations
        Report.jsx      # Section 65B Judicial Dossier generator & PDF download
        Ledger.jsx      # Chain of custody audit & interactive tamper demo
    vite.config.js      # Proxies /api -> http://127.0.0.1:8000
    tailwind.config.js  # Dark slate palette (#070b12, #0b111e) with teal & amber accents
  data/                 # Teammates drop raw CSVs here for Stage 2 pipeline
  .env.example          # Environment variables template
  README.md             # Running instructions & schema specifications
```

---

## 🔄 API Response Specifications (For Teammates Dropping Real Analytics)

When replacing the mock backend with real analytics in Stage 2, ensure endpoints return these exact JSON shapes so the frontend requires **zero changes**:

### 1. `GET /api/case`
```json
{
  "case_id": "SP-014",
  "title": "Durg Missing Cluster",
  "status": "Open",
  "persons": 62,
  "calls": 412,
  "txns": 148,
  "alerts": 7
}
```

### 2. `GET /api/graph?until=ISO_DATE`
```json
{
  "nodes": [
    {
      "id": "P-BROKER-01",
      "label": "Vikas S. ('Golden')",
      "type": "person",  // person | phone | vehicle | org | account | location | ad
      "community": 3,
      "priority": 0.94,
      "role_label": "Inter-cluster Broker",
      "aliases": ["Golden Bhai", "V. K. Sonkar"],
      "phone": "+91 98XXXXX021" // unmasked only for sp_dysp
    }
  ],
  "edges": [
    {
      "id": "E-012",
      "source": "P-BROKER-01",
      "target": "P-B-01",
      "type": "call",  // call | transfer | stay | co_travel | owns | mention | ad_response
      "score": 0.96,
      "edge_kind": "observed", // observed | extracted | inferred
      "first_ts": "2026-09-02T14:00:00Z",
      "last_ts": "2026-09-28T19:45:00Z"
    }
  ]
}
```

### 3. `GET /api/entity/{id}`
```json
{
  "id": "P-BROKER-01",
  "label": "Vikas S. ('Golden')",
  "type": "person",
  "aliases": ["Golden Bhai", "V. K. Sonkar"],
  "priority": 0.94,
  "priority_breakdown": {
    "betweenness": 0.98,
    "pagerank": 0.89,
    "cross_community": 0.96,
    "evidence_diversity": 0.92
  },
  "role_label": "Inter-cluster Broker",
  "connections": [{"id": "P-B-01", "label": "Aslam Sheikh", "score": 0.96}],
  "evidence": [
    {
      "evidence_id": "CDR-0012",
      "kind": "observed",
      "summary": "Direct VOIP handshakes bridging clusters.",
      "ts": "2026-09-27T22:40:00Z"
    }
  ]
}
```

### 4. `GET /api/edge/{source}/{target}/explain`
```json
{
  "score": 0.96,
  "formula": "1 - prod(1 - w*s)",
  "components": [
    {
      "type": "calls",
      "count": 14,
      "weight": 0.45,
      "s": 0.88,
      "contribution": 0.39,
      "evidence_ids": ["CDR-0012"]
    }
  ],
  "snippets": [
    {
      "evidence_id": "FIR-07-S3",
      "text": "Call logs establish high-frequency nighttime coordination..."
    }
  ]
}
```

### 5. `GET /api/merge-queue`
```json
[
  {
    "id": "MQ-001",
    "score": 0.88,
    "status": "pending",
    "records": [
      {
        "record_id": "REC-CHR-01",
        "name": "Vikas S. ('Golden Bhai')",
        "phone": "+91 98XXXXX021",
        "plate": "CG-07-BW-4912",
        "source": "FIR-07-S3 Witness Log"
      }
    ],
    "reasons": [
      {"factor": "Name phonetics & token overlap", "value": 0.74},
      {"factor": "Shared FASTag vehicle registration", "value": 0.95}
    ]
  }
]
```

### 6. `POST /api/simulate/remove-node`
Request: `{"node_id": "P-BROKER-01"}`
```json
{
  "before": {"components": 1, "largest": 48, "efficiency": 0.31},
  "after": {"components": 4, "largest": 19, "efficiency": 0.09},
  "delta_pct": -71.0
}
```

### 7. `GET /api/golden-hour`
```json
{
  "centroid": [21.2096, 81.3790],
  "radius_km": 3,
  "window_hours": 24,
  "missing": [
    {
      "id": "MP-01",
      "name": "Anjali Sahu",
      "age": 17,
      "lat": 21.2112,
      "lon": 81.3782,
      "last_seen_time": "2026-09-14T17:30:00Z"
    }
  ],
  "burner": {
    "number": "+91 98XXXXX902",
    "seen_near": ["MP-01", "MP-02", "MP-04", "MP-05"],
    "deactivated_after": true,
    "left_city_via_toll": true
  },
  "bait": {
    "number": "+91 97XXXXX319",
    "contacted_by": 5
  }
}
```

### 8. `POST /api/copilot`
Request: `{"question": "..."}`
```json
{
  "answer": "Investigative pattern analysis identifies entity P-BROKER-01... [CDR-0012]",
  "citations": ["CDR-0012", "TXN-0044"],
  "confidence": "high"
}
```

### 9. `GET /api/ledger` & `GET /api/verify`
```json
// GET /api/ledger
{
  "head_hash": "e8a93bc214f7...",
  "status": "intact",
  "entries": [
    {
      "idx": 1,
      "ts": "2026-09-01T08:00:00Z",
      "action": "CASE_INITIALIZATION",
      "hash": "7a8b1c2d...",
      "prev_hash": "00000000..."
    }
  ]
}

// GET /api/verify
{"ok": true}
// When tampered:
{"ok": false, "broken_at": 17}
```

---

## ⚡ Prototype Shortcuts & Stubs for Stage 1

1. **Auth & Tokens**: Uses token strings containing user roles (`token_sp_dysp_<timestamp>`) stored in `sessionStorage` and memory rather than full database-backed bcrypt hashes.
2. **Copilot Q&A**: Uses keyword matching against `mock/copilot.json` with fallback. Stage 2 will attach Groq Llama-3.3-70b-versatile embeddings over the graph.
3. **Email**: Mock endpoint formats destination email as `a***@demo.in` and returns immediate success. Stage 2 will connect SMTP credentials from `.env`.
4. **PDF Generation**: Returns a lightweight compliant PDF header stream directly from FastAPI. Stage 2 will use Weasyprint / ReportLab to generate multi-page visual dossiers with chart embeds.
