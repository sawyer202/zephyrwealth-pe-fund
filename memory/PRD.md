# ZephyrWealth.ai — Product Requirements Document

**Last Updated:** 2026-04-05
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
- **Frontend:** React 18 + Tailwind CSS + Lucide React
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
- `/app/backend/server.py` — Main API server (v2.0.0)
- Routes: `/api/auth/*`, `/api/dashboard/*`, `/api/investors`, `/api/investors/{id}`, `/api/investors/{id}/documents`, `/api/investors/{id}/scorecard`, `/api/investors/{id}/decision`, `/api/deals`, `/api/audit-logs`
- JWT auth via httpOnly cookies
- Rate limiting: 5 failed attempts → 15 min lockout
- File storage: `/documents/{entity_id}/{document_type}/{filename}`
- AI: Claude via `emergentintegrations` (`EMERGENT_LLM_KEY`)

### Frontend (React)
- `/app/frontend/src/context/AuthContext.js` — Auth state
- `/app/frontend/src/components/` — Sidebar, KPICard, RiskBadge, QueueTable, Layout
- `/app/frontend/src/pages/` — Login, Dashboard, Investors, InvestorOnboarding, InvestorDetail, Deals, Portfolio, Reports, Settings
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
- [x] AI Scorecard panel (dark #252523 background) with:
  - Traffic-light indicators: sanctions, identity, document, source of funds, PEP, mandate
  - Identity confidence score (large number)
  - Score breakdown bars (documents 0-30, source of wealth 0-25, sanctions 0-25, nationality risk 0-20)
  - Recommendation in colored text (Approve/Review/Reject)
  - 2-3 sentence AI summary
  - Footer: "AI recommendation · human approval required"
- [x] Action buttons (Approve/Request More Info/Reject) — disabled until scorecard generated
- [x] Decisions write to audit_logs collection
- [x] "Generate AI Review" button calls POST /api/investors/{id}/scorecard (Claude AI live)
- [x] Regenerate button after first generation

### Seed Data Phase 2
- [x] Victoria Pemberton (individual, low risk, approved, scorecard=Approve, 3 docs)
- [x] Apex Meridian Holdings Ltd (corporate, medium risk, pending, 2 UBOs, 4 docs)
- [x] Dmitri Volkov (individual, high risk, flagged, scorecard=Reject, 2 docs)

### New MongoDB Collections
- `documents`: {_id, entity_id, document_type, file_path, file_name, file_size, uploaded_at}
- `compliance_scorecards`: {_id, entity_id, entity_type, scorecard_data, recommendation, generated_at, reviewed_by, decision, decision_at}

---

## Backlog — Phase 3

### P0 (Critical)
- [ ] Deal Pipeline Kanban view (/deals with drag-and-drop stages)
- [ ] Deal detail view + AI deal scorecard

### P1 (Important)
- [ ] Dashboard charts (Recharts — investor funnel, deal stages)
- [ ] Role-based access control enforcement (UI elements hide/show by role)
- [ ] PDF report generation (pdf-lib)
- [ ] Advanced audit log viewer page (/reports)

### P2 (Nice to have)
- [ ] Two-factor authentication
- [ ] Email notifications (SendGrid)
- [ ] Document storage integration (cloud)
- [ ] Portfolio analytics page (/portfolio)
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
