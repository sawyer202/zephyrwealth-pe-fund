# ZephyrWealth.ai — Product Requirements Document

**Last Updated:** 2025-02-05
**Platform:** ZephyrWealth.ai (alias: zephyrtrust.ai)
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
- **AI:** Anthropic Claude via Emergent Universal Key

## Design System
- Sidebar: #252523 | Main BG: #FAFAF8 | Primary: #1B3A6B
- Accent/Gold: #C9A84C | Brand Cyan: #00A8C6
- Success: #10B981 | Warning: #F59E0B | Danger: #EF4444
- Fonts: Chivo (headings), Inter (body), JetBrains Mono (data)

---

## Architecture

### Backend (FastAPI)
- `/app/backend/server.py` — Main API server
- Routes: `/api/auth/*`, `/api/dashboard/*`, `/api/investors`, `/api/deals`, `/api/audit-logs`
- JWT auth via httpOnly cookies
- Rate limiting: 5 failed attempts → 15 min lockout
- MongoDB collections: users, investors, deals, audit_logs, login_attempts

### Frontend (React)
- `/app/frontend/src/context/AuthContext.js` — Auth state
- `/app/frontend/src/components/` — Sidebar, KPICard, RiskBadge, QueueTable, Layout
- `/app/frontend/src/pages/` — Login, Dashboard, Investors, Deals, Portfolio, Reports, Settings

---

## Phase 1 — COMPLETED (2025-02-05)

### Feature 1: Authentication + Role System
- [x] Three roles: compliance, risk, manager
- [x] Seeded accounts: compliance@, risk@, manager@zephyrwealth.ai
- [x] bcrypt password hashing
- [x] JWT (httpOnly cookies, 8h access + 7d refresh)
- [x] Rate limiting: 5 attempts → 15 min lockout
- [x] Password validation (min 8, 1 uppercase, 1 number)
- [x] Audit logging on login

### Feature 2: Executive Dashboard Shell
- [x] Sidebar navigation (Dashboard, Investors, Deals, Portfolio, Reports, Settings)
- [x] KPI cards: Total Investors, Pending KYC, Deals in Pipeline, Flagged Items
- [x] Investor Queue tab with risk badges + status + disabled action buttons
- [x] Deal Queue tab
- [x] Demo accounts quick-fill on login page
- [x] Role-based avatar colors in sidebar

### MongoDB Collections Created
- users, investors, deals, audit_logs, login_attempts

### Seeded Demo Data
- 3 investors: Harrington (medium/pending), Castlebrook (low/approved), Meridian (high/flagged)
- 2 deals: Nassau Waterfront (medium/due_diligence), Caribbean Logistics (low/term_sheet)

---

## Backlog — Phase 2

### P0 (Critical)
- [ ] KYC Scorecard workflow (enables action buttons)
- [ ] Investor onboarding form + document upload
- [ ] Deal pipeline Kanban view

### P1 (Important)
- [ ] AI compliance scoring (Claude integration)
- [ ] PDF report generation (pdf-lib)
- [ ] Dashboard charts (Recharts — investor funnel, deal stages)
- [ ] Role-based access control enforcement (UI + API)

### P2 (Nice to have)
- [ ] Two-factor authentication
- [ ] Email notifications (SendGrid)
- [ ] Advanced audit log viewer
- [ ] Document storage integration
- [ ] Portfolio analytics page
- [ ] Reports export (PDF/CSV)

---

## Security Notes
- .gitignore includes .env, node_modules, build
- .env.example committed with placeholder values only
- Real .env never committed
- All routes authenticated via JWT cookie
- Audit logs capture all login events
