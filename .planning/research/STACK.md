# Stack Delta for Milestone v3.0: App.py and Backend Refactor

## Current Stack Snapshot
- Runtime: Python + Flask monolith entry in app.py, with Flask-Login, Flask-WTF, Flask-Limiter, and Flask-Talisman already present in package/requirements.txt.
- Architecture state: create_app() exists, but module import still instantiates app and most route/business logic remains in app.py; routes/ and services/ folders are currently empty.
- Data layer: SQLite by default, optional PostgreSQL via shim in core/database.py.
- Testing state: script-style manual tests in test/ (many call real services), no pytest config file, and no coverage tooling configured.

## Recommended Additions/Changes

### 1) Testing stack decision for v3.0
- Choose pytest as the primary backend test runner for this milestone.
- Keep unittest only for legacy compatibility where already used; do not build new tests around unittest.
- Add dev-only test dependencies:
  - pytest>=8,<9
  - pytest-cov>=5,<6
  - pytest-mock>=3.14,<4
  - pytest-timeout>=2.3,<3
  - requests-mock>=1.12,<2

### 2) Coverage and gate policy
- Add coverage measurement for refactor safety:
  - Initial merge gate for v3.0 backend refactor: --cov-fail-under=55 (raise later after stabilization).
  - Target >=70% on extracted core service modules that replace app.py business logic.
- Scope coverage to backend refactor surface only:
  - include: core, routes, services
  - exclude for this milestone: dl_service, ai_agent_service, test scripts, examples

### 3) Testability-oriented structural changes (no platform change)
- Keep Flask; do not change framework.
- Make app.py composition-only:
  - keep create_app() as bootstrap entry
  - remove import-time side effects (avoid module-level app creation during tests)
- Extract handlers to routes/ blueprints and move business logic to services/ modules.
- Add fixture-driven test setup:
  - app fixture from create_app(test_config)
  - temporary SQLite test database
  - test-mode toggles for CSRF/rate-limit/security middleware when running unit/smoke tests

### 4) Minimal tooling files to introduce
- requirements-dev.txt (or package/requirements-dev.txt) for test-only dependencies.
- pytest.ini for markers and default options.
- .coveragerc to control source/omit and keep coverage focused on refactor scope.

## Version/Tooling Notes
- Keep production dependency file stable; place new test dependencies in a dev-only requirements file.
- Recommended commands for roadmap acceptance checks:
  - pytest -m "unit or smoke" -q
  - pytest --cov=core --cov=routes --cov=services --cov-report=term-missing
- Existing test/ scripts should remain as manual integration/debug scripts; new regression-safe backend tests should live under tests/ and run via pytest.

## What Not To Add This Milestone
- Do not add a framework migration (FastAPI/Quart/etc.) for the main app.
- Do not introduce Flask-SQLAlchemy/ORM migration as part of this refactor.
- Do not add Celery/Redis background infrastructure.
- Do not make CI/CD rollout a blocker for v3.0 completion.
- Do not add frontend/E2E browser testing stack in this backend milestone.

## Decision-ready summary
- Add a small dev-only pytest stack (pytest, pytest-cov, pytest-mock, pytest-timeout, requests-mock).
- Keep Flask + current database approach; change structure, not platform.
- Add pytest.ini and .coveragerc plus app/test fixtures to make refactor measurable and safe.
- Exclude infrastructure/framework expansion so team effort stays on app.py decomposition and backend regression protection.
