# ZephyrWealth.ai — PRD

## Original Problem Statement
Building ZephyrWealth.ai — a professional back-office platform for a licensed Bahamian Private Equity fund. Target users: Compliance Officers, Risk Officers, and Fund Managers.

## Architecture
```
/app/
├── backend/
│   ├── server.py          # App init, CORS, startup, router registration (63 lines)
│   ├── database.py        # MongoDB connection + DOCUMENTS_DIR
│   ├── models.py          # All shared Pydantic models
│   ├── utils.py           # JWT, password, get_current_user, deal helpers
│   ├── pdf_utils.py       # ReportLab PDF helpers, _build_notice_pdf
│   ├── seed.py            # Idempotent seed functions (Phase 1-5)
│   ├── requirements.txt
│   ├── .env
│   └── routes/
│       ├── __init__.py
│       ├── auth.py         # /api/auth/*
│       ├── dashboard.py    # /api/dashboard/*
│       ├── investors.py    # /api/investors/*
│       ├── deals.py        # /api/deals/*
│       ├── reports.py      # /api/audit-logs, /api/reports/tav-pdf
│       ├── portfolio.py    # /api/portfolio/*
│       ├── capital_calls.py # /api/capital-calls/*
│       ├── agents.py       # /api/agents/*
│       ├── trailer_fees.py  # /api/trailer-fees/*
│       └── admin.py        # /api/admin/*
├── frontend/
│   ├── .env
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── App.js
│       ├── components/
│       │   ├── Layout.js
│       │   ├── Sidebar.js
│       │   └── QueueTable.js
│       └── pages/
│           ├── Dashboard.js
│           ├── Deals.js
│           ├── DealDetail.js
│           ├── Investors.js
│           ├── InvestorDetail.js
│           ├── InvestorOnboarding.js
│           ├── Login.js
│           └── Reports.js
└── memory/
    ├── PRD.md
    └── test_credentials.md
```

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts, Sonner (Toasts)
- **Backend**: FastAPI (modular APIRouter), Python, ReportLab (PDF)
- **Database**: MongoDB (Motor async)
- **Auth**: JWT (Secure Cookies, COOKIE_SECURE=true)
- **AI**: Emergent Universal Key (Claude Sonnet for KYC Scorecards)

## DB Schema
- `users`: {_id, email, password_hash, role, name, title, created_at}
- `investors`: {_id, legal_name, entity_type, kyc_status, risk_rating, share_class, committed_capital, capital_called, placement_agent_id, deal_associations, ...}
- `documents`: {_id, entity_id, document_type, file_path, file_name, file_size}
- `compliance_scorecards`: {_id, entity_id, entity_type, scorecard_data, recommendation}
- `deals`: {_id, company_name, sector, geography, expected_irr, entry_valuation, entity_type, pipeline_stage, mandate_status}
- `fund_mandate`: {_id, fund_name, allowed_sectors[], allowed_geographies[], irr_min, irr_max}
- `audit_logs`: {_id, user_id, user_email, user_role, user_name, action, target_id, target_type, timestamp, notes}
- `fund_profile`: {_id, fund_name, license_number, fund_manager, mandate}
- `placement_agents`: {_id, agent_name, company_name, email, bank_name, bank_account_number, swift_code, vat_registered}
- `capital_calls`: {_id, call_name, call_type, target_classes, call_percentage, status, line_items[]}
- `trailer_fee_invoices`: {_id, agent_id, period_year, line_items[], subtotal, vat_applicable, total_due, status}

## What's Been Implemented

### Phase 1 (Complete)
- Security Setup, JWT Authentication + Role System (compliance/risk/manager)
- Executive Dashboard shell

### Phase 2 (Complete)
- Investor Onboarding (KYC) flow with full document upload
- AI Compliance Scorecard (Claude Sonnet via Emergent Universal Key)
- Local file storage (/documents)

### Phase 3 (Complete)
- Deal Pipeline Kanban with mandate checking
- Dashboard Charts (Recharts)
- Role-Based UI visibility toggling

### Phase 4 (Complete)
- PDF exports: Deal IC Pack, Investor KYC Pack, TAV Regulatory Report
- Audit Logs viewer with filtering and CSV export
- Demo Seed Data (idempotent) + Demo Reset button (compliance only)

### Phase 5 (Complete)
- Portfolio Analytics (/portfolio) page
- Capital Calls engine (fund-level + deal-specific)
- Trailer Fee Automation with PDF invoices
- Placement Agents management
- Fund Participation (share class, committed capital)

### Backend Refactor (Complete — 2026-02-xx)
- Monolithic server.py (2,747 lines) → modular architecture
- server.py reduced to 63 lines
- 10 route files, 5 shared modules (database.py, models.py, utils.py, pdf_utils.py, seed.py)
- 38/38 regression tests pass, zero breaking changes

### Deployment Fixes (Complete — 2026-04-05)
- **`requirements.txt` cleaned**: removed embedded pip output (lines 9–12), added
  `--extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/` for `emergentintegrations`,
  added `python-multipart` (required for FastAPI `UploadFile` / form handling)
- **`/health` route added**: FastAPI now responds to both `GET /health` (Kubernetes pod probe,
  no `/api` prefix) and `GET /api/health` (application-level check)
- **Dual-domain CORS fix** (see critical section below)

---

## ⚠️ CRITICAL — Dual-Domain CORS Configuration

> **Any future change to `server.py` CORS configuration MUST preserve this logic.**

### Problem
The Emergent deployment system sets `FRONTEND_URL` once and skips it on subsequent deploys
(`"secret FRONTEND_URL already exists, skipping"`). This means `FRONTEND_URL` in the
production pod can permanently hold the **preview** URL
(`https://<app>.preview.emergentagent.com`) even after the app is live at the **production**
domain (`https://<app>.emergent.host`).

When the browser sends `Origin: https://<app>.emergent.host` and CORS only allows the preview
URL, the `Access-Control-Allow-Origin` header is absent → the browser blocks every API
response → **login silently fails**.

### Fix — `backend/server.py` lines 24–44
```python
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Always whitelist both preview ↔ production counterpart domains.
# The deployment system may freeze FRONTEND_URL at the preview URL even after
# production go-live, so both must be explicitly allowed.
_allowed_origins = [FRONTEND_URL]
if ".preview.emergentagent.com" in FRONTEND_URL:
    _allowed_origins.append(FRONTEND_URL.replace(".preview.emergentagent.com", ".emergent.host"))
elif ".emergent.host" in FRONTEND_URL:
    _allowed_origins.append(FRONTEND_URL.replace(".emergent.host", ".preview.emergentagent.com"))
_allowed_origins.append("https://zephyrtrustai.com")
_allowed_origins.append("https://www.zephyrtrustai.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Always-Required Allowed Origins
The following origins **must always be present** in `_allowed_origins`. Never remove any of them:
1. `FRONTEND_URL` (dynamic — from env var)
2. Its counterpart domain (preview ↔ `.emergent.host`, derived automatically)
3. `https://zephyrtrustai.com` — custom production domain
4. `https://www.zephyrtrustai.com` — custom production domain (www)

### Rules
1. **Never replace `_allowed_origins` with a single-item list** — login will break on production.
2. **Never hardcode** `https://compliance-hub-demo.emergent.host` or the preview URL — the
   derivation logic handles all app names automatically.
3. **Never use `allow_origins=["*"]`** — incompatible with `allow_credentials=True` and
   insecure for a compliance platform.
4. If `FRONTEND_URL` is updated in `.env` (e.g., to a custom domain), the derivation block
   will fall through cleanly and only that one origin will be allowed — this is correct
   behaviour for custom domains.

### Verification
After any CORS-touching change, run this check against the live production domain:
```bash
curl -s -D - -X POST "https://<app>.emergent.host/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: https://<app>.emergent.host" \
  -d '{"email":"compliance@zephyrwealth.ai","password":"Comply1234!"}' \
  | grep -i "access-control-allow-origin"
# Expected: access-control-allow-origin: https://<app>.emergent.host
```

## Prioritized Backlog

### P1 — Upcoming
- Fund Manager deal creation improvement — better UX for managers adding deals

### P2 — Near-term
- Trailer Fee Dashboard on Agents page (total fees YTD, outstanding, collection rate)
- Preview Demo dry-run for reset (shows counts of records affected before executing)

### P3 — Future
- shadcn DatePicker for Reports/TAV modal
- Email notifications (SendGrid) for capital call notices
- Bulk investor CSV import
- Cloud document storage (S3)
- Investor portal (read-only LP view)
