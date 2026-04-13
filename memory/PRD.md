# ZephyrWealth.ai — PRD & Architecture Reference

## Problem Statement
Building ZephyrWealth.ai — a professional back-office platform for a licensed Bahamian Private Equity fund. Target users are Compliance Officers, Risk Officers, and Fund Managers. **Phase 6** adds a completely separate investor-facing portal accessible at `/portal/*`.

---

## Architecture

**Stack:** React + FastAPI + Local MongoDB  
**URL:** `https://compliance-hub-demo.preview.emergentagent.com`

```
/app/
├── backend/
│   ├── .env                     (JWT_SECRET, INVESTOR_JWT_SECRET, MONGO_URL, DB_NAME, ANTHROPIC_API_KEY, etc.)
│   ├── requirements.txt
│   ├── server.py                (FastAPI entry-point, CORS, routers, startup seed)
│   ├── database.py              (Motor MongoDB client)
│   ├── models.py                (Pydantic models)
│   ├── seed.py                  (Idempotent seed: investors, deals, capital calls, audit logs, portal users)
│   └── routes/
│       ├── auth.py              (Back-office login/logout/me — access_token cookie)
│       ├── investors.py         (CRUD investors, KYC PDF export)
│       ├── deals.py             (CRUD deals, IC Pack PDF export)
│       ├── capital_calls.py     (CRUD capital calls, notice PDF)
│       ├── reports.py           (TAV report PDF)
│       ├── audit.py             (Audit log CRUD)
│       ├── agents.py            (Placement agents)
│       ├── portfolio.py         (Portfolio summary)
│       ├── compliance.py        (Compliance scorecard AI)
│       ├── admin.py             (Demo reset — clears + re-seeds all data)
│       ├── portal_auth.py       (Investor portal login/logout/me/change-password — investor_token cookie)
│       └── portal.py            (Portal: dashboard, investment, capital-calls, documents, profile)
├── frontend/
│   ├── .env                     (REACT_APP_BACKEND_URL)
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── App.js               (All routes — back-office + portal)
│       ├── context/
│       │   ├── AuthContext.js           (Back-office auth — access_token)
│       │   └── InvestorAuthContext.js   (Investor portal auth — investor_token, INDEPENDENT)
│       ├── components/
│       │   ├── Layout.js, Sidebar.js, QueueTable.js, RiskBadge.js
│       └── pages/
│           ├── Login.js, Dashboard.js, Investors.js, InvestorOnboarding.js
│           ├── InvestorDetail.js    (+ Create Portal Access button/badge — compliance only)
│           ├── Deals.js, DealDetail.js, Portfolio.js, Reports.js
│           ├── Settings.js, Agents.js, AgentDetail.js, CapitalCalls.js, CapitalCallDetail.js
│           └── portal/
│               ├── PortalLogin.js          (/portal/login — split layout)
│               ├── PortalChangePassword.js (/portal/change-password — forced on first login)
│               ├── PortalLayout.js         (Top nav layout, no sidebar)
│               ├── PortalDashboard.js      (/portal/dashboard)
│               ├── PortalInvestment.js     (/portal/investment)
│               ├── PortalCapitalCalls.js   (/portal/capital-calls + detail modal)
│               ├── PortalDocuments.js      (/portal/documents + filter tabs)
│               └── PortalProfile.js        (/portal/profile + change password modal)
└── memory/
    ├── PRD.md
    ├── test_credentials.md
    └── CHANGELOG.md
```

---

## Design System

| Token | Value |
|---|---|
| Sidebar bg | `#111110` |
| Sidebar text (active) | `#E8E8E4` |
| Sidebar muted | `#5A5A56` |
| Main bg | `#FAFAF8` |
| Card bg | `#FFFFFF` |
| Card border | `#E8E6E0` |
| Primary text | `#0F0F0E` |
| Secondary text | `#888880` |
| Accent (logo only) | `#00A8C6` |
| Risk Low | bg `#F0FDF4` / text `#15803D` |
| Risk Medium | bg `#FFFBEB` / text `#92400E` |
| Risk High | bg `#FEF2F2` / text `#991B1B` |

---

## Database Collections

- `users` — `{_id, email, password_hash, role, name, created_at}`
- `investors` — `{_id, entity_type, legal_name, status, nationality, risk_rating, share_class, committed_capital, ...}`
- `investor_users` — `{_id, investor_id, email, password_hash, name, role: "investor", first_login, created_at, last_login}`
- `documents` — `{_id, entity_id, document_type, file_path, file_name, file_size, uploaded_at}`
- `compliance_scorecards` — `{_id, entity_id, scorecard_data, recommendation}`
- `deals` — `{_id, company_name, sector, geography, expected_irr, entry_valuation, pipeline_stage, status}`
- `capital_calls` — `{_id, call_name, deal_id, call_percentage, total_amount, issue_date, due_date, status, line_items[]}`
- `distributions` — `{_id, deal_id, type, gross_amount, net_amount, issue_date, status, line_items[]}`
- `fund_mandate` — `{_id, allowed_sectors[], allowed_geographies[], irr_min, irr_max}`
- `fund_profile` — `{_id, fund_name, license_number, fund_manager, bank_name, account_number, swift, mandate}`
- `audit_logs` — `{_id, user_email, user_role, user_name, action, target_id, target_type, timestamp, notes}`
- `agents`, `trailer_fee_invoices`, etc.

---

## Key API Endpoints

### Back-Office
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/me`
- `GET/POST /api/investors`, `GET /api/investors/{id}/export-pdf`
- `GET/POST /api/deals`, `GET /api/deals/{id}/export-pdf`
- `GET/POST /api/capital-calls`, `GET /api/capital-calls/{id}/notice-pdf/{investor_id}`
- `GET /api/audit-logs`
- `GET /api/reports/tav-pdf`
- `POST /api/admin/demo-reset`

### Investor Portal
- `POST /api/portal/auth/login` — sets `investor_token` HttpOnly cookie
- `POST /api/portal/auth/logout` — clears `investor_token`
- `GET /api/portal/auth/me`
- `POST /api/portal/auth/change-password`
- `POST /api/portal/admin/create-account` (compliance only)
- `GET /api/portal/admin/account-status/{investor_id}` (compliance only)
- `GET /api/portal/dashboard`
- `GET /api/portal/investment`
- `GET /api/portal/capital-calls`
- `GET /api/portal/documents` / `GET /api/portal/documents/{id}/download` (403 on cross-investor)
- `GET /api/portal/profile`

---

## Auth Architecture

**Two completely independent auth systems:**

| Property | Back-office | Investor Portal |
|---|---|---|
| Cookie name | `access_token` | `investor_token` |
| JWT secret env | `JWT_SECRET` | `INVESTOR_JWT_SECRET` |
| User collection | `users` | `investor_users` |
| React context | `AuthContext.js` | `InvestorAuthContext.js` |
| Login page | `/login` | `/portal/login` |

**Both:** `SameSite=lax`, `HttpOnly`, `Secure` cookies.

---

## Completed Phases

### Phase 1 — Auth + Dashboard Shell ✅
- JWT role-based authentication (compliance, risk, manager)
- Mobile-responsive layout with sidebar
- Executive dashboard shell

### Phase 2 — Investor KYC Flow ✅
- Full investor onboarding form
- AI Compliance Scorecard (Claude Sonnet via Emergent Universal Key)
- Document upload and storage

### Phase 3 — Deal Pipeline + Charts ✅
- Kanban deal pipeline
- Recharts dashboard charts
- Role-based UI visibility

### Phase 4 — PDF Reports + Audit Logs + Seed Data ✅
- ReportLab PDF generation (IC Pack, KYC Pack, TAV Report)
- Audit Logs viewer with filtering and CSV export
- Demo Seed Data (idempotent)
- Demo Reset button (compliance only, with confirmation modal + sonner toast)

### Phase 5 — Backend Refactor + Auth Hardening ✅
- Monolithic server.py split into modular routes/ directory
- Cross-site cookie blocking fixed (same-origin setup)
- SameSite=lax cookie hardening
- Logout button in sidebar

### Phase 6 — Investor Portal ✅ (Apr 2026)
- Separate investor portal at /portal/* routes
- Independent InvestorAuthContext.js (investor_token, INVESTOR_JWT_SECRET)
- 6 portal pages: Login, ChangePassword, Dashboard, Investment, CapitalCalls, Documents, Profile
- Strict document security: 403 on cross-investor document access
- "Create Portal Access" button on InvestorDetail (compliance only)
- "Portal Access Active" badge when account exists
- 20 seeded audit log entries in Reports page
- Pre-generated TAV Report entry in Reports page
- Demo Reset updated to clear + re-seed investor_users and audit logs
- **Test results: 42/42 backend, 19/19 frontend acceptance criteria**

---

## Backlog / Future Tasks

### P1 — Upcoming
- Preview Demo dry-run mode for Demo Reset (show how many records will be affected)
- Fund Manager deal creation UX improvement

### P2 — Future
- Trailer Fee Dashboard on Agents page
- Email notifications (SendGrid) — capital call notices, document uploads
- Cloud document storage (S3/GCS)
- Multi-fund support
- Two-factor authentication (TOTP)
