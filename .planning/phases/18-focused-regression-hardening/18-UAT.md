---
status: testing
phase: 18-focused-regression-hardening
source: [18-01-SUMMARY.md]
started: 2026-06-14T21:30:00Z
updated: 2026-06-14T21:30:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 7
name: Next pages to verify
expected: |
  Continue testing remaining pages: /products, /customers, /workspace, /wallet, /scenarios, /settings
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: App boots cleanly with `python app.py`. No import errors. http://127.0.0.1:5000 loads.
result: pass — all public routes 200/302, no 500s. App on NeonDB/Postgres.

### 2. Login Works
expected: /auth/signin loads and login succeeds.
result: pass — 200, user can log in.

### 3. User List Loads (Admin)
expected: /admin renders user list.
result: pass — user list shows. ISSUE: Recent Activity timestamps show "56 years ago" (wrong epoch calculation).

### 4. Create Import Transaction
expected: /imports renders and new import can be submitted.
result: pass

### 5. Create Export Transaction
expected: /exports renders and new export can be submitted.
result: pass

### 6. Dashboard Renders Correctly
expected: /dashboard loads with correct wallet balance and data.
result: ISSUE — dashboard initially flashes 10,000 VND then re-renders to 0. Likely JS fetch overwrites server-rendered value with empty/zero API response.

### 7. Remaining Pages
expected: /products, /customers, /workspace, /wallet, /scenarios, /settings — all load without 500.
result: partial — pages load OK; 3 API endpoints broken (all pre-existing, not Phase 18 regressions)
  - /products: page OK. DL forecast button → 500 (pre-existing, DL service not wired)
  - /customers: OK
  - /wallet: page OK. GET /api/user/wallet → 500, POST /api/user/wallet/topup → 500 (pre-existing)
  - /scenarios: OK
  - /settings: page OK. POST /api/settings/update → 500 (pre-existing)
  - /workspace: 302 → signin (auth guard OK, not tested authenticated)

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0
pre-existing-not-regressed: 3

## Gaps

### GAP-01 — Dashboard balance flickers 10k → 0
- Page: /dashboard
- Observed: Initial render shows 10,000 VND, then JS re-renders to 0.
- Likely cause: Server-rendered value correct; client-side fetch returns 0 or empty wallet data and overwrites it.
- Severity: High (wrong financial data shown to user)
- Pre-existing: unknown — needs investigation

### GAP-02 — Admin Recent Activity timestamps wrong
- Page: /admin (Recent Activity section)
- Observed: Timestamps display as "56 years ago" instead of recent times.
- Likely cause: Unix epoch seconds treated as milliseconds by JS (or vice versa), or wrong epoch base.
- Severity: Medium (cosmetic but misleading)
- Pre-existing: unknown — needs investigation

### GAP-03 (pre-existing) — DL forecast button 500
- Page: /products — DL forecast button
- Pre-existing: yes, DL service integration never completed
- Action: out of Phase 18 scope

### GAP-04 (pre-existing) — Wallet API 500
- Pages: GET /api/user/wallet, POST /api/user/wallet/topup
- Pre-existing: yes, never worked
- Action: out of Phase 18 scope

### GAP-05 (pre-existing) — Settings update API 500
- Page: POST /api/settings/update
- Pre-existing: yes, never worked
- Action: out of Phase 18 scope
