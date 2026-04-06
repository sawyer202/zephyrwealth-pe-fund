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

### Same-Origin Cookie Fix (Complete — 2026-04-06)
- **Problem**: `REACT_APP_BACKEND_URL` was set to the Emergent preview URL
  (`compliance-hub-demo.preview.emergentagent.com`). When the user accessed the app via the
  custom domain `zephyrtrustai.com`, the browser treated all API calls as **cross-origin** and
  blocked the `Set-Cookie` response headers under third-party cookie deprecation policies
  (Chrome 2026+). Login appeared to succeed (response body returned user data) but the cookie
  was never stored → Demo Reset and all protected endpoints returned `401 Not authenticated`.
- **Fix**: Changed `REACT_APP_BACKEND_URL=https://zephyrtrustai.com` so the React app makes
  API calls to the **same domain** as the page. The Kubernetes ingress already routes
  `zephyrtrustai.com/api/*` → FastAPI backend (port 8001). No new proxy configuration required.
- **FRONTEND_URL**: Updated to `https://zephyrtrustai.com` in `backend/.env`.
- **EMERGENT_ORIGIN**: Added `https://compliance-hub-demo.preview.emergentagent.com` as a
  separate env var in `backend/.env` to keep the Emergent preview/host URLs in the CORS
  allowlist. The `server.py` derivation loop now iterates both `FRONTEND_URL` and
  `EMERGENT_ORIGIN` so neither is ever dropped from `_allowed_origins`.
- **Reverse proxy**: The K8s ingress was already handling `zephyrtrustai.com/api/*` → port 8001.
  Verified via curl: `GET /api/health` → `{"status":"ok"}` ✅, login ✅, demo-reset ✅.

---

## ⚠️ CRITICAL — Domain & Cookie Configuration

> **Any future change to `server.py` CORS config or `.env` files MUST preserve this logic.**

### Env Vars (backend/.env)
| Variable | Current Value | Purpose |
|---|---|---|
| `FRONTEND_URL` | `https://zephyrtrustai.com` | Primary CORS origin; also used as same-origin API target |
| `EMERGENT_ORIGIN` | `https://compliance-hub-demo.preview.emergentagent.com` | Keeps Emergent preview + `.emergent.host` URLs in CORS allowlist |

### Env Vars (frontend/.env)
| Variable | Current Value | Purpose |
|---|---|---|
| `REACT_APP_BACKEND_URL` | `https://zephyrtrustai.com` | All browser API calls go here — must match the page's domain |

### Why REACT_APP_BACKEND_URL = https://zephyrtrustai.com
When `REACT_APP_BACKEND_URL` pointed to `compliance-hub-demo.preview.emergentagent.com` and the user accessed the app via `zephyrtrustai.com`, the browser blocked the `Set-Cookie` response from the cross-origin API domain (Chrome third-party cookie deprecation, 2026). Setting it to `zephyrtrustai.com` makes all API calls **same-origin** so cookies are always stored and sent without restrictions.

### Reverse Proxy (already handled by K8s ingress)
`https://zephyrtrustai.com/api/*` → FastAPI backend (port 8001) is managed by the Kubernetes ingress. **Do not add a second proxy.**

### CORS `_allowed_origins` (server.py lines 24–51)
The derivation loop runs over **both** `FRONTEND_URL` and `EMERGENT_ORIGIN`, so all four origins are always present:
1. `https://zephyrtrustai.com` (FRONTEND_URL)
2. `https://www.zephyrtrustai.com` (explicit static)
3. `https://compliance-hub-demo.preview.emergentagent.com` (EMERGENT_ORIGIN)
4. `https://compliance-hub-demo.emergent.host` (auto-derived from EMERGENT_ORIGIN)

### Rules
1. **Never set `REACT_APP_BACKEND_URL` to an Emergent subdomain** — breaks same-origin cookie storage on the custom domain.
2. **Never remove `EMERGENT_ORIGIN` from `backend/.env`** — the Emergent preview URL must stay in CORS for platform testing tools.
3. **Never use `allow_origins=["*"]`** — incompatible with `allow_credentials=True`.
4. **Never set cookies without `SameSite=none; Secure`** — required for the `zephyrtrustai.com` ↔ API pairing to work across potential subdomains.

### Verification (run after any CORS/auth change)
```bash
# Health
curl -s https://zephyrtrustai.com/api/health
# Expected: {"status":"ok","service":"ZephyrWealth API","version":"3.0.0"}

# CORS — custom domain
curl -si -X OPTIONS https://zephyrtrustai.com/api/health \
  -H "Origin: https://zephyrtrustai.com" \
  -H "Access-Control-Request-Method: GET" | grep access-control
# Expected: access-control-allow-origin: https://zephyrtrustai.com
#           access-control-allow-credentials: true

# CORS — Emergent preview (must not be broken)
curl -si -X OPTIONS https://zephyrtrustai.com/api/health \
  -H "Origin: https://compliance-hub-demo.preview.emergentagent.com" \
  -H "Access-Control-Request-Method: GET" | grep access-control
# Expected: access-control-allow-origin: https://compliance-hub-demo.preview.emergentagent.com
#           access-control-allow-credentials: true

# Login + cookie issuance
curl -sc /tmp/c https://zephyrtrustai.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"compliance@zephyrwealth.ai","password":"Comply1234!"}'
# Expected: 200 with Set-Cookie: access_token=...; SameSite=none; Secure

# Demo Reset (end-to-end auth check)
TOKEN=$(grep access_token /tmp/c | awk '{print $NF}')
curl -s -X POST https://zephyrtrustai.com/api/admin/demo-reset --cookie "access_token=$TOKEN"
# Expected: {"message":"Demo data reset successful..."}
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
