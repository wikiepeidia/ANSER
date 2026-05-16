# Requirements: ANSER v3.1 — Post-Refactor Stabilization and Collaborative Development

Defined: 2026-05-07
Milestone: v3.1
Core value: keep the refactored codebase stable, testable, and easy for the team to work on.

## Active Requirements

### Stability

- [ ] **STAB-01**: New bug work starts from a reproduced failing behavior, failing test, or failing command.
- [ ] **STAB-02**: Auth, workflow, AI, Smart Import/Export, wallet, and DL integration behavior remain stable after fixes.
- [ ] **STAB-03**: Route registration and middleware behavior remain stable when extracted route modules change.

### Testing

- [ ] **TEST-01**: Add or update focused pytest coverage for touched route and service slices.
- [ ] **TEST-02**: Keep characterization/parity coverage around critical flows when ownership boundaries move.
- [ ] **TEST-03**: No touched refactor surface is considered done without a narrow executable validation step.

### Documentation and Planning

- [x] **DOC-01**: Top-level `.planning` docs reflect the current engineering milestone instead of archived academic-delivery work.
- [ ] **DOC-02**: Route/service ownership notes remain current enough for teammates to navigate the codebase.
- [ ] **DOC-03**: Team-facing context docs call out current branch and collaboration expectations.

### Collaboration

- [ ] **COLLAB-01**: Work is sliced into reviewable, branch-safe changes.
- [ ] **COLLAB-02**: Public route contracts are preserved unless a coordinated change is intentional.
- [ ] **COLLAB-03**: Major architecture changes require a newly scoped milestone before implementation.

## Completed Baseline from v3.0

- [x] **BASE-01**: `app.py` is a composition/bootstrap root rather than a domain route dump.
- [x] **BASE-02**: Extracted route modules own the current domain route split.
- [x] **BASE-03**: High-risk business logic was moved into explicit service boundaries.
- [x] **BASE-04**: Contract, parity, and coverage gates exist for the refactored backend.
- [x] **BASE-05**: Security, data, and async parity were verified before close-out.

## Out of Scope

- Historical academic delivery work. Archived context only; not active engineering scope.
- Major architecture rewrite. v3.0 refactor is the accepted baseline for now.
- Unrelated feature sprawl. Stabilization and safe collaboration come first.
- Forced infrastructure migration. No concrete need right now.

## Archived Historical Context

- v2.0 academic-delivery planning is archived and no longer active.
- v2.1 Smart Import demo-fix planning is archived and no longer active.
- Detailed historical artifacts remain in `.planning/phases/` for traceability.

## Traceability

- Phase 16: `DOC-01`
- Phase 17: `STAB-01`, `STAB-02`, `STAB-03`
- Phase 18: `TEST-01`, `TEST-02`, `TEST-03`, `DOC-02`, `DOC-03`
- Phase 19: `COLLAB-01`, `COLLAB-02`, `COLLAB-03`

Coverage:

- Active v3.1 requirements: 11 total
- Mapped to phases: 11/11

Last updated: 2026-05-07 after top-level planning context refresh.
