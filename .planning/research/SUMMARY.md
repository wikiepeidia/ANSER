# Milestone v3.0 Backend Refactor Research Summary

Scope: app.py/backend refactor plus backend tests only.
Date: 2026-04-14
Inputs: .planning/research/STACK.md, .planning/research/FEATURES.md, .planning/research/ARCHITECTURE.md, .planning/research/PITFALLS.md

## 1) Stack additions/changes (concise)

- Keep current runtime and platform: Flask app factory pattern, current SQLite/PostgreSQL compatibility layer, existing core integrations.
- Add dev-only backend test stack:
  - pytest (primary runner)
  - pytest-cov (coverage gating)
  - pytest-mock (dependency mocking)
  - pytest-timeout (hang protection)
  - requests-mock (HTTP integration doubles)
- Add minimal test tooling files for this milestone:
  - requirements-dev.txt
  - pytest.ini
  - .coveragerc
- Structural refactor target (no platform migration):
  - app.py becomes composition-only (bootstrap, extension setup, blueprint registration)
  - routes/ holds thin blueprint handlers
  - services/ holds business logic and DB transactions (no Flask globals/context objects)
  - dependencies resolved through app-scoped extension getters
- Explicit out-of-scope stack changes:
  - No framework switch
  - No ORM/database redesign
  - No Celery/Redis or infra expansion

## 2) Feature table stakes vs differentiators

| Type | Capability | Milestone expectation |
|---|---|---|
| Table stake | app.py as composition root | No business SQL/branching in app.py at completion |
| Table stake | Domain route extraction | Main endpoints moved into domain blueprints with stable paths/methods |
| Table stake | Service layer extraction | Route handlers stay thin; logic moved to service functions |
| Table stake | Backward compatibility | Critical endpoint contracts (auth/workflow/AI/billing/DL proxy) preserved |
| Table stake | Automated backend tests | Pytest service unit tests plus critical route smoke tests |
| Table stake | Branch ownership boundaries | Backend refactor changes isolated from frontend UI work |
| Differentiator | Architecture guard test | Fails if new app-level route decorators return to app.py |
| Differentiator | API contract snapshots | Locks JSON shape for highest-risk endpoints |
| Differentiator | Extraction map doc | Old app.py handlers mapped to new route/service modules |
| Differentiator | Incremental migration flags | Domain rollback toggles for safer integration |
| Differentiator | Structured backend logging | Faster diagnosis during mixed-branch convergence |

## 3) Architecture integration strategy and recommended phase order

Integration strategy:

- Use a strangler refactor, not a rewrite: preserve endpoint contracts while moving code in controlled waves.
- Keep initialization order stable in create_app() and preserve auth/session/security behavior.
- Migrate domain-by-domain with tests after each wave.

Recommended phase order:

1. Baseline lock: export route inventory, add critical smoke/contract tests before moving code.
2. Composition hardening: keep create_app() as the bootstrap entry and establish dependency getter pattern.
3. Service extraction in place: move business logic out of route bodies while routes still live in app.py.
4. Blueprint migration: move thin handlers to routes/ modules and register in controlled order.
5. Duplicate route canonicalization: resolve overlapping URL+method handlers intentionally.
6. Final composition-only app.py: remove remaining business logic and keep startup/registration only.

Why this order:

- Tests and route inventory must come first to detect contract drift early.
- Service extraction before blueprint migration reduces routing churn and import complexity.
- Canonicalization follows migration because duplicates are easier to resolve after isolation.

## 4) Top pitfalls and prevention actions

1. Route contract drift from overlapping endpoints.
Action: lock endpoint inventory and response baselines first; add contract tests for critical APIs.

2. Hidden global dependency coupling.
Action: move mutable runtime dependencies behind app extensions/dependency getters; ban route imports from app.py globals.

3. Import-time side effects causing nondeterministic startup/tests.
Action: enforce pure app factory usage in tests and lazy-load external integrations.

4. Refactor without regression safety.
Action: write characterization/smoke tests before extraction; gate merges on backend suite.

5. Flask context leaking into services.
Action: define service boundary contract (plain inputs/outputs only) and add a check that services do not import Flask.

6. SQLite-only validation masking PostgreSQL breakage.
Action: run critical smoke checks against both DB modes for high-risk write paths.

## 5) Recommended requirement categories for milestone v3.0

- Architecture decomposition requirements:
  - app.py composition-only
  - domain blueprint registration
  - service-layer boundaries
- Compatibility requirements:
  - URL/method stability
  - payload/status-code parity for critical flows
- Testability and regression requirements:
  - mandatory pytest unit+smoke baseline
  - coverage threshold and trend tracking
- Security/middleware parity requirements:
  - auth redirects vs API 401/403 behavior
  - CSRF/rate-limit/unauthorized handler parity after migration
- Data and async reliability requirements:
  - DB transaction behavior parity
  - AI job lifecycle integrity (pending/processing/completed/failed)
- Delivery safety requirements:
  - wave-based migration gates
  - rollback toggles per domain
  - backend/frontend branch ownership rules

## 6) Roadmap drafting hints (phase boundaries + dependency notes)

Suggested phase boundaries:

- Phase A: Baseline and guardrails (inventory, smoke tests, contract snapshots).
- Phase B: Dependency and app composition hardening.
- Phase C: Service extraction by domain (read-heavy first, write-heavy next).
- Phase D: Blueprint migration by domain with preserved endpoint names.
- Phase E: Duplicate resolution, final cleanup, parity verification.

Dependency notes:

- Phase A is a hard prerequisite for safe migration.
- Phase B must finish before large-scale module extraction.
- Phase C should complete per-domain before moving that domain into Phase D.
- High-risk domains (billing, OAuth, AI async) should be migrated after low-risk read-only domains.
- Final milestone close should require two consecutive full smoke passes and explicit rollback readiness.

Ready for requirements: yes - research is specific, aligned on backend scope, and provides clear ordering, risks, and acceptance categories for milestone v3.0.
