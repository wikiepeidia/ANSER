---
phase: 11
slug: baseline-contract-guardrails
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 11 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini (Wave 0 creates) |
| **Quick run command** | `python -m pytest tests/contracts -q` |
| **Full suite command** | `python -m pytest tests/contracts -q` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/contracts -q`
- **After every plan wave:** Run `python -m pytest tests/contracts -q`
- **Before /gsd-verify-work:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | TEST-03 | T-11-01 | Contract list is explicit and reviewable | contract | `python -m pytest tests/contracts/test_contract_routes.py -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | TEST-01 | T-11-02 | Test harness runs in isolated local app context | smoke | `python -m pytest tests/contracts -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | SAFE-01 | T-11-03 | Rollback point exists after each migration wave | process | `rg "Wave|Rollback" .planning/phases/11-baseline-contract-guardrails/11-migration-waves.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/contracts/test_contract_routes.py` - stubs for TEST-03
- [ ] `tests/contracts/test_contract_smoke.py` - stubs for TEST-03
- [ ] `tests/conftest.py` - shared Flask fixtures
- [ ] `pytest.ini` - pytest configuration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Key page route status check for `/`, `/dashboard`, `/imports`, `/exports` | TEST-03 | UI-page route behavior may depend on auth/session context and templates | Run app locally, hit each route with authenticated test path, confirm expected status and no server error |

---

## Validation Sign-Off

- [ ] All tasks have automated verification or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing test artifacts
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 seconds
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
