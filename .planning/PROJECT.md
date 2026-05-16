# ANSER — Automated Nimble Software Easing Relaxation

## What This Is

A Flask-based RPAaaS (Robotic Process Automation as a Service) platform built as a university group project (USTH GEN14). ANSER provides Smart Import, Smart Export, a drag-and-drop workflow builder, AI-assisted workflow generation, Google OAuth, and supporting wallet/subscription flows.

The project is now in normal collaborative development. The active work is engineering-focused: stabilize the refactored backend, fix concrete bugs, and continue small incremental improvements with the team.

## Core Value

Deliver a working workflow automation platform with clear module boundaries so the team can change it safely without turning `app.py` back into a monolith.

## Current Milestone

### v3.1 Post-Refactor Stabilization and Collaborative Development

Goal:
Use the completed v3.0 backend refactor as the baseline, keep the extracted route and service structure stable, and support normal bug-fix and incremental development work.

## Validated Baseline

- Google OAuth login/callback and session management are working.
- AI chat with background task processing is working.
- DL proxy integration for OCR/forecast endpoints is wired.
- Wallet and subscription flows still exist after refactor.
- Drag-and-drop workflow builder and workflow execution engine remain available.
- `app.py` is reduced to bootstrap/composition responsibilities.
- Domain route handlers were extracted into dedicated route modules.
- High-risk business logic moved into explicit service boundaries.
- Backend guardrails, coverage gate, and parity verification exist from v3.0.

## Active Focus

- Keep `app.py` as a composition root and avoid reintroducing mixed responsibilities.
- Fix reproduced bugs in auth, workflow, AI, Smart Import/Export, wallet, and DL integration flows.
- Add focused regression tests around touched route and service slices.
- Keep top-level planning and ownership docs aligned with the live codebase.
- Support small branch-safe changes from teammates without breaking route contracts.

## Out of Scope

- Historical academic delivery work. This is archived context only.
- Major architecture rewrites beyond the completed v3.0 refactor.
- Unrelated feature sprawl that ignores current route/service boundaries.
- Forced infrastructure migrations with no concrete engineering need.

## Context

- v3.0 is the accepted engineering baseline.
- Current work should start from a failing behavior, a narrow code path, or a clear maintenance/documentation task.
- Multiple people may work in parallel, so route contracts and ownership boundaries should stay predictable.
- Historical pre-refactor phases remain archived for traceability, but they are no longer the live planning frame.

## Constraints

- Scope: stabilization, bug fixes, documentation refresh, and incremental team work.
- Compatibility: existing runtime behavior should remain stable unless a breaking change is discussed explicitly.
- Branching: prefer isolated, reviewable changes that do not block parallel teammates.
- Timeline: no demo-driven countdown; prioritize correctness and maintainability.

## Key Decisions

- v3.0 refactor is the accepted baseline.
- Route/service boundaries stay the default pattern.
- SQLite remains the default local data layer.
- Historical academic-planning context is archived, not active.

## Evolution

Update this document when the active milestone changes, when team workflow changes materially, or when the accepted engineering baseline drifts.

Last updated: 2026-05-07 after top-level planning context refresh.
