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

## Data Endpoints (all require auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/dashboard/stats | GET | KPI stats |
| /api/investors | GET | List investors |
| /api/deals | GET | List deals |
| /api/audit-logs | GET | Audit log (compliance/manager only) |
| /api/health | GET | Health check |

## App URL
https://pe-compliance-hub.preview.emergentagent.com
