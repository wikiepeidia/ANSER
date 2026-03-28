---
phase: 1
slug: foundation-and-branch-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual smoke testing (pytest setup is Phase 4) |
| **Config file** | none — no test framework in Phase 1 |
| **Quick run command** | `python -c "from app import create_app; app = create_app(); print('OK')"` |
| **Full suite command** | `python -c "from app import create_app; app = create_app(); client = app.test_client(); print(client.get('/').status_code)"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command (import check)
- **After every plan wave:** Run full suite command (app starts + responds)
- **Before `/gsd:verify-work`:** Full suite must pass
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 1 | FOUND-03 | manual | `git branch` shows 6 branches | N/A | pending |
| 01-02 | 01 | 1 | FOUND-02 | import | `python -c "from core.extensions import db_manager, login_manager, csrf, limiter"` | pending | pending |
| 01-03 | 01 | 1 | FOUND-01 | import | `python -c "from app import create_app; create_app()"` | pending | pending |
| 01-04 | 01 | 1 | FOUND-04 | manual | Demo branch exists and team knows freeze rule | N/A | pending |

---

## Wave 0 Requirements

- [ ] `core/extensions.py` — shared extension instances
- [ ] `app.py` refactored to `create_app()` factory pattern

*No test framework install needed — Phase 1 uses import checks and manual verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All 113 routes respond | FOUND-01 | No pytest yet | Start app, navigate to key pages (login, dashboard, wallet) |
| Demo branch freeze discipline | FOUND-04 | Team agreement | Verify team understands 48h freeze rule |
| Branch merge flow works | FOUND-03 | Git workflow | Create test commit on backend, merge to mixed, verify |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
