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
| /api/deals | GET | List deals |
| /api/deals/{id}/export-pdf | GET | IC Pack PDF (compliance + risk only) |
| /api/audit-logs | GET | Audit log with filters (compliance/manager only) |
| /api/reports/tav-pdf | GET | TAV Regulatory Report PDF (compliance only) |
| /api/health | GET | Health check |

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
