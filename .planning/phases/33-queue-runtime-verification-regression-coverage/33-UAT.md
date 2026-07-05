---
status: complete
phase: 33-queue-runtime-verification-regression-coverage
source: [29-01-SUMMARY.md, 30-01-SUMMARY.md, 31-01-SUMMARY.md, 32-01-SUMMARY.md, 33-01-SUMMARY.md]
started: 2026-07-05T04:45:00Z
updated: 2026-07-05T06:05:19Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill running server, start fresh, server boots without errors, a primary route (`/`) returns live data.
result: issue
reported: "Server started fine, but `http://127.0.0.1:5000/` returned 302 to `https://127.0.0.1:5000/`, which failed outright (SSL handshake error) — the Werkzeug dev server has no TLS listener. Root cause: real `.env` predates the Phase 29 change and has no `FLASK_ENV` set, so `is_local_environment()` returned False and Talisman forced HTTPS. Fixed by adding `FLASK_ENV=development` to `.env` and restarting; retested `/` → 200 OK."
severity: blocker
resolved: true
resolution: "User added FLASK_ENV=development to local .env and restarted. Also added a startup warning in app.py (logged to logs/app.log) that fires whenever FLASK_ENV/APP_ENV is unset, so future teammates pulling this change get an explicit heads-up instead of a silent forced-HTTPS lockout. README already documents FLASK_ENV as required for new clones (line 48)."

### 2. Production security defaults (Phase 29 / TODO items 1)
expected: Secure cookies, rate limiting, HSTS, and forced HTTPS enabled by default outside dev/test; login route rate-limited.
result: pass
notes: "Verified via full pytest run (178 passed) and live curl. Rate-limit enforcement itself is dev-mode-exempt by design (RATELIMIT_ENABLED defaults False when FLASK_ENV=development) — confirmed via test_security_hardening.py rather than live 429, since forcing production mode live would re-trigger the HTTPS lockout above."

### 3. Ownership scoping — sales/product/customer/reports/automation (Phase 30 / TODO items 2-4)
expected: Non-owners cannot delete/update/list another user's sales, products, customers, reports, or automation rules.
result: pass
notes: "Covered by tests/test_security_hardening.py (owner-scope tests) — all passing."

### 4. Google account password hashing (Phase 31 / TODO item 5)
expected: Google-created users get bcrypt hashes via AuthManager, not werkzeug's generate_password_hash.
result: pass

### 5. Webhook SSRF protection (Phase 31 / TODO item 6)
expected: trigger_webhook() resolves DNS and blocks private/loopback/link-local/reserved targets before the HTTP call.
result: pass

### 6. CSRF exemption scope (Phase 31 / TODO item 7)
expected: Only the n8n webhook blueprint is CSRF-exempt; no other authenticated routes carry csrf.exempt.
result: pass
notes: "Live grep across routes/ and app.py confirms exactly one exemption: `csrf.exempt(n8n_api_bp)` in app.py."

### 7. Safe API error responses (Phase 32 / TODO item 8)
expected: API 500s return a correlation ID, not the raw exception string.
result: pass

### 8. Upload size/type validation (Phase 29/31 / TODO item 9)
expected: MAX_CONTENT_LENGTH enforced; unsupported file types/extensions rejected before processing.
result: pass
notes: "MAX_CONTENT_LENGTH configured (16MB default, env-overridable) in app.py; validate_upload() rejection covered by test_security_hardening.py."

### 9. current_app.extensions usage in sales routes (Phase 32 / TODO item 10)
expected: No direct module-level db_manager import in routes/sales_routes.py.
result: pass

### 10. Google OAuth SQL moved to repository (Phase 32 / TODO item 11)
expected: routes/google_routes.py calls UserRepo/Database facade methods instead of raw SQL.
result: pass

### 11. RQ worker check before AI queue enqueue (Phase 33 / TODO item 11)
expected: AI chat enqueue refuses jobs when no RQ worker is registered, unless explicitly overridden.
result: pass

## Summary

total: 11
passed: 11
issues: 1 (found and resolved in-session)
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Fresh server start over plain HTTP serves the app without error"
  status: resolved
  reason: "Local .env lacked FLASK_ENV, so production-safe defaults (force_https) applied to a dev server with no TLS listener, making the app entirely unreachable over HTTP."
  severity: blocker
  test: 1
  root_cause: "core/security.py is_local_environment() depends on FLASK_ENV/APP_ENV env vars; app.py:82-92 wires force_https from that. Local .env predated the Phase 29 hardening and had no FLASK_ENV set."
  artifacts:
    - path: "app.py"
      issue: "No warning when FLASK_ENV/APP_ENV absent — silent switch to production-safe (HTTPS-forcing) defaults"
  missing:
    - "Startup warning when FLASK_ENV/APP_ENV unset"
  fix_applied: "Added logger.warning() in app.py create_app() (app.py:83-88) firing when both FLASK_ENV and APP_ENV are unset and not TESTING. Confirmed it lands in logs/app.log. README already lists FLASK_ENV as required for new setups."
  debug_session: ""
