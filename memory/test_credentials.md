# Test Credentials — ZephyrWealth.ai

## Back-Office Users
| Role | Email | Password |
|---|---|---|
| Compliance Officer | compliance@zephyrwealth.ai | Comply1234! |
| Fund Manager | manager@zephyrwealth.ai | Comply1234! |
| Risk Officer | risk@zephyrwealth.ai | Comply1234! |

## Investor Portal Users
| Investor | Email | Password | Notes |
|---|---|---|---|
| Cayman Tech Ventures SPV Ltd | investor1@caymantech.com | Invest1234! | first_login: true (reset via demo reset) |
| Marcus Harrington (HNW Barbadian) | marcus.bajan@gmail.com | Invest1234! | first_login: true (reset via demo reset) |

## Notes
- All back-office passwords: `Comply1234!`
- All investor portal initial passwords: `Invest1234!` — investors MUST change on first login
- After investor changes password, `first_login` becomes `false`
- **To restore all seed data:** `POST /api/admin/demo-reset` (as compliance user) resets investor_users, clears all demo data, and re-seeds fresh

## Portal URL
- Investor portal login: `https://compliance-hub-demo.preview.emergentagent.com/portal/login`
- Back-office login: `https://compliance-hub-demo.preview.emergentagent.com/login`
