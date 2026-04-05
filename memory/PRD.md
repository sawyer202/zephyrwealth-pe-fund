# ZephyrWealth.ai — Product Requirements Document

**Last Updated:** 2026-04-05 (Phase 3 complete)
**Platform:** ZephyrWealth.ai
**Type:** Professional back-office SaaS for a licensed Bahamian Private Equity fund

---

## Problem Statement
Build an institutional-grade back-office platform for Compliance Officers, Risk Officers, and Fund Managers to manage investor onboarding (KYC) and deal pipelines with AI-assisted compliance scoring. Think Bloomberg terminal meets modern SaaS dashboard.

## Target Users
- Chief Compliance Officer
- Head of Risk
- Fund Manager

## Tech Stack
- **Backend:** FastAPI + Python + Motor (async MongoDB)
- **Frontend:** React 18 + Tailwind CSS + Lucide React + Recharts
- **Database:** MongoDB (local)
- **Auth:** Custom JWT (httpOnly cookies) + bcrypt
- **AI:** Anthropic Claude (`claude-4-sonnet-20250514`) via Emergent Universal Key

## Design System
- Sidebar: #252523 | Main BG: #FAFAF8 | Primary: #1B3A6B
- Accent/Gold: #C9A84C | Brand Cyan: #00A8C6
- Success: #10B981 | Warning: #F59E0B | Danger: #EF4444
- Fonts: Chivo (headings), Inter (body), JetBrains Mono (data)

---

## Architecture

### Backend (FastAPI)
- `/app/backend/server.py` — Main API server (v3.0.0)
- Routes: `/api/auth/*`, `/api/dashboard/*`, `/api/investors`, `/api/investors/{id}`, `/api/investors/{id}/documents`, `/api/investors/{id}/scorecard`, `/api/investors/{id}/decision`, `/api/deals`, `/api/deals/{id}`, `/api/deals/{id}/stage`, `/api/deals/{id}/health-score`, `/api/deals/{id}/execute`, `/api/audit-logs`
- JWT auth via httpOnly cookies
- Rate limiting: 5 failed attempts → 15 min lockout
- File storage: `/documents/{entity_id}/{document_type}/{filename}`
- AI: Claude via `emergentintegrations` (`EMERGENT_LLM_KEY`)

### Frontend (React)
- `/app/frontend/src/context/AuthContext.js` — Auth state
- `/app/frontend/src/components/` — Sidebar, KPICard, RiskBadge, QueueTable, Layout
- `/app/frontend/src/pages/` — Login, Dashboard (with Recharts), Investors, InvestorOnboarding, InvestorDetail, Deals (Kanban), DealDetail, Portfolio, Reports, Settings
- `/app/frontend/src/constants/countries.js` — Full country list

---

## Phase 1 — COMPLETED (2025-02-05)

### Feature 1: Authentication + Role System
- [x] Three roles: compliance, risk, manager
- [x] Seeded accounts: compliance@, risk@, manager@zephyrwealth.ai
- [x] bcrypt password hashing
- [x] JWT (httpOnly cookies, 8h access + 7d refresh)
- [x] Rate limiting: 5 attempts → 15 min lockout
- [x] Audit logging on login

### Feature 2: Executive Dashboard Shell
- [x] Sidebar navigation
- [x] KPI cards: Total Investors, Pending KYC, Deals in Pipeline, Flagged Items
- [x] Investor Queue + Deal Queue tabs
- [x] Demo accounts quick-fill on login page
- [x] Role-based avatar colors in sidebar

---

## Phase 2 — COMPLETED (2026-04-05)

### Feature 3: Investor Onboarding (4-Step Form at /investors/new)
- [x] Step 1: Entity type toggle (Individual/Corporate), legal name, DOB/incorporation date, nationality + residence country dropdowns (full country list)
- [x] UBO Declaration section (Corporate only): add/remove beneficial owners >10%
- [x] Step 2: Email, phone, full address with country
- [x] Step 3: Classification, net worth ($), annual income ($), source of wealth, investment experience, accredited declaration checkbox
- [x] Step 4: Document upload (drag-and-drop): passport, proof of address, source of wealth doc, corporate docs (corporate only), terms acceptance
- [x] Files stored at `/documents/{entity_id}/{document_type}/{filename}` (PDF, JPG, PNG, max 5MB)
- [x] POST /api/investors creates investor + audit log entry
- [x] Per-step validation, back button preserves form state
- [x] Success → redirect to /investors

### Feature 4: AI Compliance Scorecard (/investors/{id})
- [x] Investor detail page: entity info, contact, financial profile cards (3-column)
- [x] UBO declarations table (corporate only)
- [x] Documents section with download links (authenticated `/api/investors/{id}/documents/{doc_id}/download`)
- [x] AI Scorecard panel (dark #252523 background) with traffic-light indicators, confidence score, recommendation
- [x] Action buttons (Approve/Request More Info/Reject) — Compliance-only; hidden for Risk/Manager
- [x] Decisions write to audit_logs collection
- [x] "Generate AI Review" button calls POST /api/investors/{id}/scorecard (Claude AI live)
- [x] Regenerate button after first generation

---

## Phase 3 — COMPLETED (2026-04-05)

### P0 Bug Fix: investors.filter crash
- [x] Fixed array guard in Investors.js: `Array.isArray(data) ? data : data.investors || []`
- [x] Fixed array guard in Dashboard.js investor fetch

### Feature 5: Deal Pipeline Kanban (/deals)
- [x] 4-column Kanban board: Leads → Due Diligence → IC Review → Closing
- [x] Deal cards: company name, sector, geography, IRR%, entity type (IBC/ICON), mandate badge
- [x] Mandate filter dropdown: All / In Mandate / Exception
- [x] "Add New Deal" modal with fields: company name, sector, geography, asset class, entity type, IRR%, entry valuation
- [x] Form validation — required fields check before POST
- [x] POST /api/deals with auto mandate check and stamp duty calculation
- [x] New deal appears in Leads column immediately after creation
- [x] Deal card click → navigates to /deals/:id (DealDetail)
- [x] Route /deals/:id added in App.js
- [x] Seed data: NexaTech Caribbean (IC Review, IBC, In Mandate), West African Fintrust (Due Diligence, ICON, Exception), Nassau Microfinance (Leads, IBC, In Mandate)

### Feature 5b: DealDetail (/deals/:id)
- [x] Company info, financials, pipeline stage cards
- [x] Pipeline stage progress indicator
- [x] Documents section
- [x] Deal Health Score panel (formula-based: compliance risk, financial alignment, document status, mandate status, stamp duty estimate)
- [x] "Advance Stage" button (all roles, mandate override flow for exception deals)
- [x] "Execute Transaction" button (compliance + risk only; hidden for manager)
- [x] Mandate override modal (Risk Officer only) for exception deals
- [x] ICON notice banner when entity_type = ICON
- [x] Execute generates IBC Subscription Agreement or ICON Participation Agreement as downloadable .txt

### Feature 6: Dashboard Charts
- [x] Two Recharts BarCharts below KPI cards
- [x] Investor funnel: status distribution (Pending/Approved/Flagged/Rejected)
- [x] Deal pipeline: deals by stage (Leads/Due Diligence/IC Review/Closing)
- [x] Data from GET /api/dashboard/charts
- [x] Status colors per segment (#00A8C6, #F59E0B, #10B981, #EF4444, #6B7280)

### Feature 7: Role-Based UI
- [x] Compliance Officer: full access — New Investor button, Approve/Reject/More Info in InvestorDetail, Execute Transaction in DealDetail
- [x] Risk Officer: no New Investor; no Approve/Reject/More Info; CAN advance stages + override mandate exceptions; CAN execute transactions
- [x] Fund Manager: no New Investor; no Approve/Reject/More Info; no Execute Transaction; CAN advance stages

### New MongoDB Collections (Phase 3 additions)
- `deals`: {_id, company_name, sector, geography, asset_class, expected_irr, entry_valuation, entity_type (IBC/ICON), mandate_status, pipeline_stage, stamp_duty_estimate, status, created_at, created_by}
- `fund_mandate`: {_id, fund_name, allowed_sectors[], allowed_geographies[], irr_min, irr_max, max_single_investment, updated_at}

---

## Backlog — Phase 4+

### P2 (Nice to have)
- [ ] PDF report generation (pdf-lib) from DealDetail or InvestorDetail
- [ ] Advanced audit log viewer page (/reports)
- [ ] Portfolio analytics page (/portfolio)
- [ ] Two-factor authentication
- [ ] Email notifications (SendGrid)
- [ ] Document storage integration (cloud)
- [ ] Reports export (PDF/CSV)
- [ ] Bulk investor import (CSV)

---

## Security Notes
- .gitignore includes .env, node_modules, build
- .env.example committed with placeholder values only
- Real .env never committed
- All routes authenticated via JWT cookie
- Audit logs capture all login events and investor decisions
- Documents require authenticated download endpoint
