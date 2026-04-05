# ZephyrWealth.ai — PRD

## Problem Statement
Building ZephyrWealth.ai — a professional back-office platform for a licensed Bahamian Private Equity fund. Target users: Compliance Officers, Risk Officers, and Fund Managers.

## App URL
https://compliance-hub-demo.preview.emergentagent.com

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts, Lucide Icons
- **Backend**: FastAPI (Python), ReportLab (PDF generation)
- **Database**: MongoDB (local)
- **AI**: Emergent Universal Key (Claude Sonnet for Compliance Scorecard)
- **Auth**: JWT + HttpOnly Cookies (SameSite=lax, Secure=true)

## Design System
- Sidebar: `#252523`
- Background: `#FAFAF8`
- Accent: `#00A8C6`
- Navy: `#1B3A6B`
- Gold: `#C9A84C`

## User Roles
- `compliance` — Full access, PDF exports, /reports page
- `risk` — Deal access, IC Pack PDF, no investor decisions
- `manager` — Read-only; no PDFs, no /reports

---

## Implemented Features (All Phases)

### Phase 1 — Auth & Shell (DONE)
- JWT auth with bcrypt password hashing
- Role-based access control (compliance / risk / manager)
- HttpOnly cookies with `Secure=true`, `SameSite=lax`
- Executive Dashboard shell

### Phase 2 — Investor Onboarding (DONE)
- 4-step KYC onboarding form (`/investors/new`)
- Document upload (local filesystem)
- AI Compliance Scorecard (Claude Sonnet via Emergent Universal Key)
- Approve / Reject / More Info decisions

### Phase 3 — Deal Pipeline & Dashboard (DONE)
- Deal Pipeline Kanban at `/deals` with mandate filters
- Deal Detail page (`/deals/:id`) with health score
- Recharts on Dashboard (investor funnel + deal pipeline)
- Role-based UI visibility (manager hides approve/reject, new investor)

### Phase 4 — PDF Exports, Reports, Seed Data (DONE — 2026-04-05)
- **COOKIE_SECURE fix**: cookies now set with `Secure=true` via env var
- **Mobile responsiveness**: hamburger sidebar (375px overlay), KPI single column, chart max 250px, table overflow-x-auto
- **Feature 8 — Deal IC Pack PDF**: `GET /api/deals/{id}/export-pdf` (ReportLab), Compliance+Risk only
- **Feature 9 — Investor KYC Pack PDF**: `GET /api/investors/{id}/export-pdf` (ReportLab), Compliance only
- **Feature 10 — Audit Log Viewer** `/reports`: Compliance only in nav; filter bar (date, action, role), paginated table (20/page), Export CSV
- **Feature 11 — TAV Regulatory Report**: Modal with auto-calculated current quarter; `GET /api/reports/tav-pdf?from=&to=`; 5-section PDF (Cover, Fund Overview, Portfolio Summary, TAV Breakdown, Investor Base, Compliance Summary)
- **Feature 12 — Demo Seed Data** (idempotent via `fund_profile` guard):
  - Fund Profile: Zephyr Caribbean Growth Fund I (SCB-2024-PE-0042)
  - 6 investors: 3 approved, 1 pending, 1 flagged, 1 rejected
  - 5 deals: CaribPay (Closing), AgroHub (IC Review), InsureSync (IC Review/Exception), SaaSAfrica (Due Diligence), CariLogix (Leads/Exception)
  - 15 audit log entries spanning 60 days

---

## DB Schema

| Collection | Key Fields |
|---|---|
| `users` | `_id, email, password_hash, role, name, title` |
| `investors` | `_id, legal_name, entity_type, nationality, kyc_status, risk_rating, scorecard_completed` |
| `documents` | `_id, entity_id, document_type, file_path, file_name, file_size, uploaded_at` |
| `compliance_scorecards` | `_id, entity_id, scorecard_data, recommendation, decision, decision_at` |
| `deals` | `_id, company_name, sector, geography, entity_type, pipeline_stage, mandate_status, entry_valuation, expected_irr` |
| `fund_mandate` | `_id, allowed_sectors[], allowed_geographies[], irr_min, irr_max` |
| `fund_profile` | `_id, fund_name, license_number, fund_manager, mandate_sectors[], irr_min, irr_max` |
| `audit_logs` | `_id, user_id, user_email, user_role, user_name, action, target_id, target_type, timestamp, notes` |

---

## Key API Endpoints

| Endpoint | Auth | Description |
|---|---|---|
| `POST /api/auth/login` | — | Login |
| `GET /api/auth/me` | all | Current user |
| `GET /api/dashboard/stats` | all | KPI stats |
| `GET /api/investors` | all | List investors |
| `GET /api/deals` | all | List deals |
| `GET /api/deals/{id}/export-pdf` | compliance, risk | IC Pack PDF |
| `GET /api/investors/{id}/export-pdf` | compliance | KYC Pack PDF |
| `GET /api/audit-logs` | compliance, manager | Filtered audit logs |
| `GET /api/reports/tav-pdf` | compliance | TAV Regulatory Report PDF |
| `GET /api/portfolio/summary` | all | Portfolio KPIs + chart data + holdings |

---

## Test Results
- Phase 3: 36/36 (100%)
- Phase 4: 39/39 (100%)
- Phase 5 Portfolio Analytics: 34/34 (100%)
- Phase 5 Capital Calls: 56/56 (100%)

---

## Remaining / Backlog

### P2
- Refactor server.py into modules (auth, deals, investors, reports, pdf_generators) — 1738 lines currently
- Use shadcn DatePicker instead of native date inputs in Reports filter bar and TAV modal

### Phase 5 — Capital Calls & Trailer Fee Automation (DONE — 2026-04-05)

**Step 1: Data Model Updates**
- New collections: `placement_agents`, `capital_calls`, `trailer_fee_invoices`
- New investor fields: `share_class`, `committed_capital`, `capital_called`, `capital_uncalled`, `placement_agent_id`, `deal_associations`

**Step 2: InvestorDetail Fund Participation** (Compliance only)
- Share class dropdown (A/B/C), committed capital input, read-only called/uncalled
- Class C: placement agent dropdown + deal association multi-select
- `PATCH /api/investors/{id}/fund-participation`

**Step 3: Placement Agents Management** (`/agents` — Compliance only)
- Table: name, company, email, VAT status, linked investors, total fees
- Add Agent modal with all schema fields
- `GET/POST /api/agents`, `GET/PATCH /api/agents/{id}`
- AgentDetail: agent info, linked Class C investors, invoice history

**Step 4 & 5: Capital Call Engine** (`/capital-calls` — Compliance + Risk)
- 3-step modal: Setup → Preview → Issue
- Fund Level (Class A/B) or Deal Specific (Class C)
- Capital Call Detail: line items, mark received/defaulted, 8% p.a. interest accrual
- Export Notices (PDF/ZIP), Export Summary CSV
- `GET/POST /api/capital-calls`, `POST /{id}/issue`, `GET /{id}`, `PATCH /{id}/line-items/{investor_id}`
- `GET /{id}/notice-pdf/{investor_id}`, `GET /{id}/notices`, `GET /{id}/export-csv`

**Step 6: Trailer Fee Invoice Generator** (0.75% × committed_capital, +10% VAT if registered)
- Generate modal on /agents page: select year + agents
- Invoice Detail: line items, subtotal, VAT, total due
- Issue / Mark Paid / Export PDF
- `POST /api/trailer-fees/generate`, `GET/GET/{id}/POST/{id}/issue/POST/{id}/mark-paid/GET/{id}/pdf`

**Step 7: Dashboard & Portfolio Updates**
- Dashboard: 8 KPI cards (4 investor/deal + 4 capital)
- Portfolio: 5th KPI card (Total Committed), Capital Called vs Uncalled by Share Class chart

**Step 8: Seed Data**
- 2 placement agents (Island Capital Advisors, Caribbean Wealth Partners)
- 5 investors updated with share class + committed capital ($1.7M total)
- 2 capital calls (Q1 2026 $300K all received, Q2 2026 $375K with 1 pending)
- 1 trailer fee invoice (Island Capital 2025, $1,650 incl. 10% VAT, issued)
- Test: 56/56 pass (100%)
- **Feature 13 — Portfolio Analytics** (`/portfolio`): Accessible to all 3 roles.
  - Section 1 — KPI Strip: Total Portfolio Value, Active Investments (IC Review + Closing), Weighted Avg IRR (valuation-weighted), Mandate Exception Rate %
  - Section 2 — 4 Charts: Sector Allocation donut, Geography Allocation donut, IRR Distribution horizontal bar (In Mandate=teal, Exception=amber), Pipeline Stage Value bar
  - Section 3 — Holdings Table: Sortable columns (click header), row click navigates to `/deals/:id`
  - Backend: `GET /api/portfolio/summary` — single endpoint returns {kpis, charts, holdings}
  - Test: 34/34 pass (all 3 roles, all KPIs, all charts, sortable table, row navigation)

---

### P2 (Backlog)
- Refactor server.py into modules (auth, deals, investors, reports, pdf_generators) — 1948 lines currently
- Deal creation improvement for Fund Manager role
- Use shadcn DatePicker instead of native date inputs in Reports filter bar and TAV modal

### P3 (Backlog)
- Email notifications via SendGrid (investor decisions, stage changes)
- Cloud document storage (S3/GCS) instead of local filesystem
- Bulk investor import via CSV upload
- Two-factor authentication
- Deal mandate exception approval workflow (Risk Officer override with IC sign-off)
- Advanced search/filter on Investors and Deals pages

---

## File Structure
```
/app/
├── backend/
│   ├── .env (MONGO_URL, DB_NAME, JWT_SECRET, FRONTEND_URL, EMERGENT_LLM_KEY, COOKIE_SECURE)
│   ├── server.py (1738 lines — monolith, P2 refactor)
│   └── requirements.txt
├── frontend/
│   ├── .env (REACT_APP_BACKEND_URL)
│   └── src/
│       ├── App.js
│       ├── components/
│       │   ├── Layout.js (mobile hamburger, sidebar state)
│       │   ├── Sidebar.js (role-gated nav, onClose prop)
│       │   ├── KPICard.js
│       │   ├── QueueTable.js
│       │   └── RiskBadge.js
│       └── pages/
│           ├── Dashboard.js (Recharts, mobile charts)
│           ├── Deals.js (Kanban)
│           ├── DealDetail.js (Export IC Pack button)
│           ├── Investors.js
│           ├── InvestorDetail.js (Export KYC Pack button)
│           ├── InvestorOnboarding.js
│           ├── Reports.js (Audit Log + TAV modal — FULL REWRITE)
│           └── Login.js
└── memory/
    ├── PRD.md (this file)
    ├── test_credentials.md
    └── CHANGELOG.md
```
