# Group Project AI/ML - USTH GEN14

## What This Is

A Flask-based AI/ML web application built as a university group project (USTH GEN14). It provides AI chat, deep learning services (OCR via VietOCR, forecasting via LSTM), drag-and-drop workflows, wallet/subscription billing, and Google OAuth authentication. The team failed the initial jury presentation and is preparing for a retake in 1-2 weeks.

## Core Value

Demonstrate clean, well-architected AI/ML integration through a working web application with proper separation of concerns — convincing the jury that the engineering and methodology are sound.

## Requirements

### Validated

- Google OAuth login/callback and session management — existing
- AI chat with background task processing — existing
- DL proxy to OCR (VietOCR) and forecasting (LSTM) services — existing
- Wallet system (topup, withdraw, transactions) — existing
- Subscription system (upgrade, auto-renew, expiry check) — existing
- Drag-and-drop workflow builder — existing
- SQLite database with user, wallet, subscription, workflow tables — existing

### Active

- [ ] Refactor app.py (3514 lines "God Object") into services/routes architecture per APP-PY-renew.md proposal
- [ ] Create Flask Blueprints for routes: auth, billing, workflows, ai, dl_proxy
- [ ] Extract business logic into services/: wallet_service, subscription_service, ai_worker_service, workflow_service, dl_proxy_service
- [ ] Slim app.py to <100 lines (app factory pattern)
- [ ] Create documentation .md files for each module (e.g., workflow.md for workflow.py)
- [ ] Set up branching strategy: main (production/post-test), dev (canary testing), demo (jury presentation)
- [ ] Add unit tests for the new service layer
- [ ] Fix report issues flagged by jury: missing sections, wrong figures, evaluation methodology, informal language
- [ ] Fix presentation/report mismatches

### Out of Scope

- Mobile app — web-first, not relevant for retake
- Real-time chat/websockets — not needed for jury demo
- Migration away from SQLite — sufficient for demo scale
- CI/CD pipeline — team can deploy manually for retake

## Context

- **Jury feedback (failed first attempt):** Missing useful sections, wrong system architecture figure, missing captions, evaluation needs redo, informal language, LSTM figure wrong, no description of execution engine, unclear UI methodology
- **Team size:** 4+ members, merge conflicts are a real concern (hence branching strategy)
- **Current state:** Single 3514-line app.py handling everything — routing, business logic, DB queries, background threads
- **Existing proposal:** DOCUMENTS/backend/APP-PY-renew.md already details the refactoring plan with examples
- **Report requirement (anser.md):** Must document HOW app.py was split — this is part of the retake deliverable

## Constraints

- **Timeline**: 1-2 weeks until jury retake presentation
- **Team**: 4+ members, need clear branch separation to avoid conflicts
- **Tech stack**: Flask, SQLite, Python — no framework changes
- **Backwards compatibility**: All existing features must continue working after refactor
- **Jury focus**: Clean architecture + working demo equally important; jury checks report and presentation more than UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Flask Blueprints for routing | Standard Flask pattern, proven, well-documented | -- Pending |
| Services layer for business logic | Separation of concerns, testable, matches APP-PY-renew.md proposal | -- Pending |
| 3-branch strategy (main/dev/demo) | 4+ team members, need stable demo for jury while dev continues | -- Pending |
| SQLite stays | No time to migrate, sufficient for demo | -- Pending |
| Report fixes alongside code refactor | Jury cares about report quality as much as code | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after initialization*
