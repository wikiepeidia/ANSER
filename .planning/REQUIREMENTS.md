# Requirements: Group Project AI/ML Refactor

**Defined:** 2026-03-28
**Core Value:** Demonstrate clean, well-architected AI/ML integration — convincing the jury that engineering and methodology are sound.

## v1 Requirements

Requirements for the retake milestone. Each maps to roadmap phases.

### Foundation

- [ ] **FOUND-01**: Application uses factory pattern (`create_app()`) instead of module-level Flask instance
- [ ] **FOUND-02**: Shared extensions (db_manager, login_manager, csrf, limiter) live in `core/extensions.py` to prevent circular imports
- [ ] **FOUND-03**: Git branching strategy established with main, dev, and demo branches
- [ ] **FOUND-04**: Demo branch protection — frozen 24-48h before jury presentation

### Services

- [ ] **SRVC-01**: Wallet business logic extracted to `services/wallet_service.py` with zero Flask imports
- [ ] **SRVC-02**: Subscription business logic extracted to `services/subscription_service.py` with zero Flask imports
- [ ] **SRVC-03**: AI worker logic (background tasks, job files) extracted to `services/ai_worker_service.py`
- [ ] **SRVC-04**: Workflow CRUD logic extracted to `services/workflow_service.py` with zero Flask imports
- [ ] **SRVC-05**: DL proxy client logic extracted to `services/dl_proxy_service.py`

### Routes

- [ ] **ROUT-01**: Auth routes extracted to `routes/auth.py` as Flask Blueprint
- [ ] **ROUT-02**: Billing routes (wallet + subscription) extracted to `routes/billing.py` as Flask Blueprint
- [ ] **ROUT-03**: Workflow routes extracted to `routes/workflows.py` as Flask Blueprint
- [ ] **ROUT-04**: AI chat routes extracted to `routes/ai.py` as Flask Blueprint
- [ ] **ROUT-05**: DL proxy routes extracted to `routes/dl_proxy.py` as Flask Blueprint
- [ ] **ROUT-06**: All `url_for()` calls updated to use Blueprint-qualified endpoint names
- [ ] **ROUT-07**: App.py reduced to <100 lines (factory + blueprint registration only)

### Testing

- [ ] **TEST-01**: pytest + pytest-flask infrastructure set up with `tests/conftest.py`
- [ ] **TEST-02**: At least 5 unit tests covering service layer functions
- [ ] **TEST-03**: Coverage report generated via `pytest --cov=services`

### Documentation

- [ ] **DOCS-01**: Each service module has companion .md documentation file
- [ ] **DOCS-02**: Each route module has companion .md documentation file
- [ ] **DOCS-03**: Refactoring process documented in anser.md (how app.py was split, architecture decisions)

### Report

- [ ] **REPT-01**: Informal language removed from report
- [ ] **REPT-02**: Missing sections filled in
- [ ] **REPT-03**: Formatting fixed (abstract numbering, captions, figure references)

## v2 Requirements

Deferred to after retake. Tracked but not in current roadmap.

### Report Deep Fixes

- **REPT-V2-01**: Architecture diagram replaced with correct system architecture image
- **REPT-V2-02**: LSTM evaluation section redone with proper metrics
- **REPT-V2-03**: OCR evaluation section redone with proper metrics
- **REPT-V2-04**: Execution engine description added to report
- **REPT-V2-05**: Presentation aligned with report content

### Infrastructure

- **INFR-01**: CI/CD pipeline with GitHub Actions
- **INFR-02**: Docker containerization
- **INFR-03**: Database migration to PostgreSQL

## Out of Scope

| Feature | Reason |
|---------|--------|
| New application features | Jury evaluates existing system, not new features |
| Database migration | SQLite sufficient for demo; no time in 1-2 weeks |
| WebSocket/real-time | Not core to AI/ML demonstration |
| Mobile app | Web-first; not relevant for retake |
| CI/CD pipeline | Manual deploy sufficient for retake |
| OAuth providers beyond Google | Single provider sufficient for demo |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| SRVC-01 | Phase 2 | Pending |
| SRVC-02 | Phase 2 | Pending |
| SRVC-03 | Phase 2 | Pending |
| SRVC-04 | Phase 2 | Pending |
| SRVC-05 | Phase 2 | Pending |
| ROUT-01 | Phase 3 | Pending |
| ROUT-02 | Phase 3 | Pending |
| ROUT-03 | Phase 3 | Pending |
| ROUT-04 | Phase 3 | Pending |
| ROUT-05 | Phase 3 | Pending |
| ROUT-06 | Phase 3 | Pending |
| ROUT-07 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| DOCS-01 | Phase 5 | Pending |
| DOCS-02 | Phase 5 | Pending |
| DOCS-03 | Phase 5 | Pending |
| REPT-01 | Phase 5 | Pending |
| REPT-02 | Phase 5 | Pending |
| REPT-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initial definition*
