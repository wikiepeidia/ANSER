# Roadmap: ANSER — Collaborative Development

## Status Snapshot

### Archived Historical Milestones

- v1.0 Code Refactoring — early planning, later superseded.
- v2.0 Academic Delivery — archived historical milestone.
- v2.1 Smart Import Demo Fix — archived historical hotfix milestone.

### Completed Engineering Baseline

- v3.0 App.py and Backend Refactor — completed through Phases 11–15. Route extraction, service boundaries, coverage gate, and parity verification are the accepted engineering baseline.

### Current Milestone

- v3.1 Post-Refactor Stabilization and Collaborative Development — active.

## Current Milestone: v3.1 Post-Refactor Stabilization and Collaborative Development

Milestone goal:
Keep the refactored backend stable, make incremental engineering improvements, and support normal team collaboration without reintroducing stale planning context or architecture drift.

### Planned Phases

- [x] **Phase 16: Planning Context Refresh** — align top-level `.planning` docs with current engineering reality and archive stale academic-delivery framing.
- [ ] **Phase 17: Post-Refactor Stabilization** — investigate and fix reproduced bugs in refactored backend surfaces.
- [ ] **Phase 18: Focused Regression Hardening** — add/update targeted tests and ownership docs around touched route/service slices.
- [ ] **Phase 19: Normal Incremental Development** — resume small collaborative bug-fix and feature work on stable foundations.

## Working Rules for v3.1

- Start from a concrete failing behavior, narrow maintenance task, or clear ownership/documentation gap.
- Keep changes reviewable and branch-safe for teammates.
- Preserve route contracts unless a coordinated change is intentional.
- Prefer focused validation over broad unscoped refactors.

## Progress

| Phase | Milestone | Status | Notes |
| --- | --- | --- | --- |
| 16 | v3.1 | Complete | Top-level planning context refreshed and normalized. |
| 17 | v3.1 | Not started | Next recommended work: stabilization on a concrete failing behavior. |
| 18 | v3.1 | Not started | Add focused regression coverage and ownership-note refreshes around touched slices. |
| 19 | v3.1 | Not started | Resume normal collaborative bug-fix and small feature work on stable foundations. |

## Archive Note

Historical detail for earlier milestones remains preserved in `.planning/phases/` and older repo documents for traceability, but those artifacts are not the current planning source of truth.

Last updated: 2026-05-07 after roadmap normalization for v3.1 collaborative development.
