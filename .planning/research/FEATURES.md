# Feature Expectations: Milestone v3.0 App.py and Backend Refactor

**Scope:** New milestone capabilities only (backend refactor and testability)
**Researched:** 2026-04-14
**Confidence:** HIGH (based on .planning/PROJECT.md, .planning/ROADMAP.md, app.py, routes/, services/, and branch topology)

Current baseline from code inspection:
- app.py is 3524 lines with 110 app-level route decorators.
- Only 2 auth blueprint routes exist, so extraction is partial.
- routes/ and services/ at repository root are effectively empty for the main app.
- Existing reusable backend services are minimal (for example core/services/dl_client.py and core/services/analytics_service.py).
- Active branches already split work by concern (backend, frontend, mixed), so contract-first coordination is required.

## Table Stakes

Capabilities that should be treated as mandatory for milestone acceptance.

| Capability | What must be true at v3.0 completion | Why this is table stakes | Branch coordination implication |
|---|---|---|---|
| App.py as composition root | app.py handles app factory, extension wiring, config, blueprint registration, and startup only. No business SQL blocks and no app-level route bodies remain. | This is the core milestone goal and the biggest maintainability bottleneck. | Backend branch owns app.py restructuring. Frontend branch should not edit app.py except conflict resolution in mixed. |
| Route extraction into domain modules | Main application endpoints are grouped by domain in route modules and registered via blueprints. | 110 inline routes in app.py is the primary architecture risk. | Route signatures and endpoint names must be frozen before mixed merge to avoid frontend breakage. |
| Service layer extraction | Route handlers become thin adapters (auth, input, output). Business logic and DB transactions move to service modules without Flask request/session objects. | Refactor without service extraction only relocates complexity, it does not reduce it. | Backend branch publishes stable service contracts so future UI/API adjustments do not reopen large merge conflicts. |
| Backward-compatible API behavior | Existing URL paths, methods, response JSON shape, and auth behavior remain compatible for critical flows (auth, workflow, AI, Smart Import/Export entry points). | Defense demo reliability depends on behavior parity, not just code cleanliness. | Frontend branch can continue safely if backend preserves API contract and shared response fields. |
| Automated backend tests (pytest) | A runnable backend suite exists with service-unit tests plus lightweight route smoke tests for critical flows. | Refactor risk is too high without regression protection. | Mixed branch merge gate should require backend tests green before frontend integration. |
| Refactor ownership boundary | Clear file ownership is enforced: backend branch focuses on app.py, route modules, service modules, backend tests; frontend branch focuses templates/static/ui scripts. | Prevents merge churn and hidden cross-branch coupling. | Mixed branch integration becomes predictable and reviewable with low conflict risk. |

## Differentiators

Capabilities that are not strictly required to finish v3.0, but meaningfully improve quality and merge safety.

| Capability | Added value | Relative complexity | Branch coordination impact |
|---|---|---|---|
| Architecture guard test | Add a test that fails if new app-level route decorators reappear in app.py. | Low | Prevents regression when both backend and frontend branches keep evolving. |
| API contract snapshot checks | Snapshot key response payloads for high-risk endpoints (wallet, subscription, workflow, ai chat status). | Medium | Gives frontend branch a stable integration contract during merge windows. |
| Extraction map document | One short mapping table from old app.py handlers to new module/function locations. | Low | Speeds conflict resolution and onboarding during backend-frontend merge. |
| Incremental migration flags | Temporary compatibility wrappers so high-risk routes can be moved in small batches safely. | Medium | Reduces long-lived divergence between backend and frontend branches. |
| Structured backend logging | Consistent request/route/service error logging after extraction. | Medium | Makes mixed branch debugging faster when integration defects appear. |

## Anti-features (explicitly avoid)

Work that should not enter v3.0 because it increases risk without serving milestone outcomes.

| Anti-feature | Why to avoid in v3.0 | Safer alternative |
|---|---|---|
| New product features or new endpoints | Expands scope and invalidates parity testing. | Freeze feature surface; refactor existing behavior only. |
| UI redesign or UI behavior rewrites in backend branch | Collides with frontend branch mandate and creates noisy conflicts. | Keep backend branch UI-touch minimal and compatibility-only. |
| Database schema redesign or migration strategy changes | Raises migration/test burden and delays refactor completion. | Keep existing schema stable; refactor access logic only. |
| Replacing runtime architecture (Celery, new queue system, framework migration) | Too risky for current timeline and defense prep. | Keep current async pattern; isolate it behind service interfaces. |
| Large non-targeted test expansion | High effort, low milestone-specific return. | Focus tests on extracted services and critical endpoint smoke paths. |
| Reopening old narrative work (report/presentation/LSTM scope) | Not part of this milestone capability target. | Keep v3.0 strictly backend architecture and integration safety. |

## Complexity/Dependencies

| Milestone capability slice | Complexity | Depends on | Main risk | Mitigation |
|---|---|---|---|---|
| Define extraction boundaries and module ownership | Low | Current route inventory from app.py | Missing hidden coupling between handlers | Start with route inventory and dependency mapping per domain |
| Move read-heavy routes first (list/get endpoints) | Medium | Blueprint skeletons + service stubs | Inconsistent response schema | Lock response contract with smoke assertions |
| Move write/transaction-heavy routes (wallet/subscription/import-export/workflow mutations) | High | Stable service transaction helpers | Subtle behavioral regressions | Add focused unit tests around transaction outcomes and edge cases |
| Isolate external integrations (Google OAuth/API, DL proxy, AI background jobs) behind services | High | Service interfaces + config discipline | Timeouts, token flow, and threading side effects | Keep endpoint behavior unchanged; test with integration doubles/mocks |
| Final app.py slimming and bootstrap hardening | Medium | All blueprint migrations complete | Residual side effects in import time | Keep startup-only logic in app factory and entrypoint |
| Backend-frontend branch convergence to mixed | Medium | Passing backend suite + API contract freeze | Merge conflicts and hidden UI dependency drift | Gate merge on backend tests and contract checklist, then fast-follow frontend validation |

Dependency ordering for this milestone:
1. Route inventory and ownership map.
2. Blueprint and service skeleton creation.
3. Read-path migration.
4. Write-path migration.
5. Test suite stabilization.
6. app.py final slimming.
7. Backend to mixed merge, then frontend integration validation.

Prioritized requirement selection:
1. Enforce app.py composition-root-only scope with full route extraction.
2. Require service-layer extraction for business and transaction logic.
3. Require pytest-based backend regression baseline (service + smoke).
4. Enforce backend/frontend branch ownership boundaries and merge gate in mixed.
5. Add architecture guard test (no route decorators returning to app.py).
6. Add API contract snapshots for the highest-risk endpoints if time remains.
