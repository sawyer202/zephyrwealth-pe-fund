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
| /api/investors/{id}/documents/{doc_id}/download | GET | Download document (authenticated) |
| /api/investors/{id}/scorecard | POST | Generate AI compliance scorecard |
| /api/investors/{id}/scorecard | GET | Get latest scorecard |
| /api/investors/{id}/decision | POST | Make decision (approve/reject/more_info) |
| /api/deals | GET | List deals |
| /api/audit-logs | GET | Audit log (compliance/manager only) |
| /api/health | GET | Health check |

## Seeded Phase 2 Investors (full schema)

| Name | Entity Type | Risk | KYC Status | Scorecard | ID prefix |
|------|-------------|------|------------|-----------|-----------|
| Victoria Pemberton | Individual | Low | approved | Approve (score=91) | starts with 69d... |
| Apex Meridian Holdings Ltd | Corporate | Medium | pending | (none initially) | starts with 69d... |
| Dmitri Volkov | Individual | High | flagged | Reject (score=34) | starts with 69d... |

## App URL
https://compliance-ops-5.preview.emergentagent.com
