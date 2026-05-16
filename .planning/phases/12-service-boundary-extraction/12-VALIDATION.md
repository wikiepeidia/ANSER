---
phase: 12
slug: service-boundary-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 12 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini |
| **Quick run command** | `python -m pytest tests/services -q` |
| **Full suite command** | `python scripts/phase11_guardrail_check.py` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/services -q`
- **After every plan wave:** Run `python scripts/phase11_guardrail_check.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | REFAC-06 | T-12-01 | Extraction map records delegated ownership and status | unit | `python -m pytest tests/services/test_extraction_contracts.py -q` | ❌ W0 | pending |
| 12-01-02 | 01 | 1 | TEST-02 | T-12-02 | Service signatures reject Flask context objects | unit | `python -m pytest tests/services/test_extraction_contracts.py -q` | ❌ W0 | pending |
| 12-02-01 | 02 | 2 | REFAC-05 | T-12-03 | Workflow/AI service modules own business logic branches | unit | `python -m pytest tests/services/test_workflow_service.py tests/services/test_ai_chat_service.py -q` | ❌ W0 | pending |
| 12-02-02 | 02 | 2 | TEST-02 | T-12-04 | Route handlers delegate and preserve response contracts | integration | `python scripts/phase11_guardrail_check.py` | ✅ | pending |
| 12-03-01 | 03 | 3 | REFAC-05 | T-12-05 | Import/export inventory mutations are service-owned and transactional | unit | `python -m pytest tests/services/test_inventory_tx_service.py -q` | ❌ W0 | pending |
| 12-03-02 | 03 | 3 | TEST-02 | T-12-06 | Service-level tests plus parity gate pass before phase close | integration | `python scripts/phase11_guardrail_check.py` | ✅ | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/conftest.py` - shared service fixtures
- [ ] `tests/services/test_extraction_contracts.py` - service signature and delegation baseline checks
- [ ] `tests/services/` package scaffold - initial service test tree

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extraction-map readability for team handoff | REFAC-06 | Human review of migration traceability quality | Confirm map rows are complete and references resolve to real files |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing test scaffolds
- [ ] No watch-mode commands used in verification
- [ ] Feedback latency under 120 seconds
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
