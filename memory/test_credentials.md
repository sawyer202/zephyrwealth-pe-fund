# ZephyrWealth Test Credentials

## Authentication Accounts

| Role | Email | Password | Name |
|------|-------|----------|------|
| Compliance Officer | compliance@zephyrwealth.ai | Comply1234! | Sarah Chen |
| Risk Officer | risk@zephyrwealth.ai | Risk1234! | Marcus Webb |
| Fund Manager | manager@zephyrwealth.ai | Manager1234! | Jonathan Morrow |

## Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/auth/login | POST | Login with email + password |
| /api/auth/logout | POST | Logout (clears cookies) |
| /api/auth/me | GET | Get current user |
| /api/auth/refresh | POST | Refresh access token |

## Phase 2 Data Endpoints (all require auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/dashboard/stats | GET | KPI stats |
| /api/investors | GET | List all investors |
| /api/investors | POST | Create new investor (onboarding) |
| /api/investors/{id} | GET | Get single investor |
| /api/investors/{id}/documents | POST | Upload document (multipart: file + document_type) |
| /api/investors/{id}/documents | GET | List investor documents |
| /api/investors/{id}/scorecard | POST | Generate AI compliance scorecard |
| /api/investors/{id}/scorecard | GET | Get latest scorecard |
| /api/investors/{id}/decision | POST | Make decision (approve/reject/more_info) |
| /api/investors/{id}/export-pdf | GET | KYC Pack PDF (compliance only) |
| /api/investors/{id}/fund-participation | PATCH | Update share class + capital (compliance only) |
| /api/deals | GET | List deals |
| /api/deals/{id}/export-pdf | GET | IC Pack PDF (compliance + risk only) |
| /api/audit-logs | GET | Audit log with filters (compliance/manager only) |
| /api/reports/tav-pdf | GET | TAV Regulatory Report PDF (compliance only) |
| /api/portfolio/summary | GET | Portfolio KPIs + chart data + holdings |
| /api/agents | GET | List placement agents |
| /api/agents | POST | Create placement agent (compliance only) |
| /api/agents/{id} | GET | Agent detail with linked investors + invoices |
| /api/agents/{id} | PATCH | Update agent (compliance only) |
| /api/capital-calls | GET | List capital calls (compliance + risk) |
| /api/capital-calls | POST | Create draft capital call (compliance only) |
| /api/capital-calls/{id}/issue | POST | Issue capital call (compliance only) |
| /api/capital-calls/{id} | GET | Capital call detail with line items |
| /api/capital-calls/{id}/line-items/{investor_id} | PATCH | Mark line item received/defaulted |
| /api/capital-calls/{id}/notices | GET | Download all notices as ZIP or PDF |
| /api/capital-calls/{id}/export-csv | GET | Export line items as CSV |
| /api/trailer-fees/generate | POST | Generate trailer fee invoices (compliance only) |
| /api/trailer-fees | GET | List trailer fee invoices |
| /api/trailer-fees/{id} | GET | Invoice detail |
| /api/trailer-fees/{id}/issue | POST | Issue invoice |
| /api/trailer-fees/{id}/mark-paid | POST | Mark as paid |
| /api/trailer-fees/{id}/pdf | GET | Trailer fee invoice PDF |
| /api/health | GET | Health check |

## Phase 5 Seed Data

| Investor | Share Class | Committed Capital |
|----------|-------------|-------------------|
| Cayman Tech Ventures SPV Ltd | Class A | $750,000 |
| Nassau Capital Partners IBC | Class A | $500,000 |
| Marcus Harrington | Class B | $150,000 |
| Yolanda Santos | Class B | $100,000 |
| Meridian Global Holdings Ltd | Class C | $200,000 |
| Olympus Private Capital Ltd | Class C | $0 (rejected) |

**Seed Totals (all investors):** Committed $1,700,000 | Called $675,000 | Uncalled $1,025,000
**Dashboard (approved only):** Committed $1,400,000 | Called $630,000 | Uncalled $770,000 | Call Rate 45%

| Placement Agent | VAT | Linked Investors |
|----------------|-----|-----------------|
| Island Capital Advisors Ltd | 10% VAT | Meridian Global Holdings |
| Caribbean Wealth Partners | No VAT | Olympus Private Capital |

| Capital Call | % | Total | Status |
|-------------|---|-------|--------|
| Q1 2026 — Initial Drawdown | 20% | $300,000 | Issued (all received) |
| Q2 2026 — Harbour House Acquisition | 25% | $375,000 | Issued (Yolanda pending) |

| Trailer Fee Invoice | Total | Status |
|--------------------|-------|--------|
| TF-2025-001 (Island Capital, 2025) | $1,650 incl. VAT | Issued |

## Seeded Demo Investors (Phase 4 — Idempotent)

| Name | Entity Type | KYC Status | Nationality |
|------|-------------|------------|-------------|
| Cayman Tech Ventures SPV Ltd | Corporate | approved | Cayman Islands |
| Nassau Capital Partners IBC | Corporate | approved | Bahamas |
| Marcus Harrington | Individual | approved | Barbados |
| Yolanda Santos | Individual | pending | Trinidad and Tobago |
| Meridian Global Holdings Ltd | Corporate | flagged | Panama |
| Olympus Private Capital Ltd | Corporate | rejected | British Virgin Islands |

## Seeded Demo Deals (Phase 4 — Idempotent)

| Company | Stage | Mandate | Entry Valuation |
|---------|-------|---------|-----------------|
| CaribPay Solutions Ltd | closing | In Mandate | $4,200,000 |
| AgroHub Africa Ltd | ic_review | In Mandate | $2,800,000 |
| InsureSync Caribbean ICON | ic_review | Exception | $3,100,000 |
| SaaSAfrica BV | due_diligence | In Mandate | $1,500,000 |
| CariLogix Ltd | leads | Exception | $900,000 |

## Fund Profile
- Fund: Zephyr Caribbean Growth Fund I
- License: SCB-2024-PE-0042
- Manager: Zephyr Asset Management Ltd

## App URL
https://compliance-hub-demo.preview.emergentagent.com
