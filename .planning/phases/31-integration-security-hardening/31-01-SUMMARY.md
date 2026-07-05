---
phase: 31-integration-security-hardening
plan: "01"
requirements-completed:
  - AUTH-06
  - SEC-02
  - SEC-03
  - SEC-05
completed: 2026-07-05
---

# Phase 31 Plan 01: Integration Security Hardening Summary

## Accomplishments

- Added `UserRepo.update_google_account()` and `UserRepo.upsert_google_user()` plus `Database` facade methods.
- Google-created users now receive bcrypt hashes from `AuthManager.hash_password`.
- `trigger_webhook()` validates DNS-resolved destinations and blocks private, loopback, link-local, reserved, multicast, and unspecified addresses before outbound HTTP.
- Removed authenticated CSRF exemptions from admin subscription, admin user list, product import, wallet withdraw, and workflow execute routes.
- Added upload validation for AI uploads, DL detect uploads, product Excel imports, and workflow uploads.

## Files Modified

- `core/db/user_repo.py`
- `core/db/connection.py`
- `routes/google_routes.py`
- `core/make_integration.py`
- `routes/admin_subscription_routes.py`
- `routes/admin_user_routes.py`
- `routes/main_routes.py`
- `routes/wallet_routes.py`
- `routes/workflow_routes.py`
- `routes/ai_routes.py`
- `routes/dl_routes.py`
- `tests/test_security_hardening.py`

