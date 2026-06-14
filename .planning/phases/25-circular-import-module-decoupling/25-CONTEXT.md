# Phase 25: Circular Import & Module Decoupling - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Remove module-level `app = create_app()` from app.py, introduce a proper wsgi.py entry point, and eliminate all sys.path hacks in core/ so the module graph is clean and importable without side effects.

**Scope:**
- `app.py`: move `app = create_app()` from module level into `if __name__ == '__main__':` block
- `wsgi.py`: create at project root, export `application = create_app()` for gunicorn
- `core/services/dl_client.py`: remove `sys.path.insert` hack; change `use_local` default to `False`; lazy-import local DL service only when `use_local=True` is explicitly passed

**Out of scope:** Changes to Flask routes, DL model logic, or any other files.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Specific known state (from code audit):
- `app.py` line 243: `app = create_app()` at module level — move into `if __name__ == '__main__':` block
- `wsgi.py` does not exist — create it
- `core/services/dl_client.py` lines ~17-26: `sys.path.insert(0, dl_service_path)` and `use_local=True` default — remove sys.path hack, change default to `use_local=False`, guard local imports inside the method with lazy import
- `requirements-base.txt`, `requirements-ml.txt`, `requirements-dev.txt` already exist (done in Phase 22) — do not recreate

</decisions>

<code_context>
## Existing Code Insights

### Known Issues (from audit)
- `app.py:243`: `app = create_app()` at module level causes any `import app` to spin up the server
- `core/services/dl_client.py:17`: `use_local=True` default routes all calls through local in-process import
- `core/services/dl_client.py:~22-26`: `sys.path.insert(0, dl_service_path)` — brittle path hack

### Integration Points
- `wsgi.py` will import `create_app` from `app` (the factory function, not the module-level instance)
- `dl_client.py` HTTP path calls `self.base_url` (DL_SERVICE_URL env var) — already wired, just needs to be default

</code_context>

<specifics>
## Specific Ideas

- wsgi.py should follow gunicorn convention: `from app import create_app; application = create_app()`
- dl_client lazy import: inside methods that need `use_local=True`, do `from services.invoice_service import ...` inside the method body, not at module top

</specifics>

<deferred>
## Deferred Ideas

None — phase scope is narrow and well-defined.

</deferred>
