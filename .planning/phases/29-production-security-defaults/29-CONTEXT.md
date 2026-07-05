# Phase 29: Production Security Defaults - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning
**Mode:** Autonomous from TODO.MD

<domain>
## Phase Boundary

Make production-like runtime defaults safe outside local `dev`/`test`: secure session cookies, rate limiting, HTTPS redirects, HSTS, and upload size caps.

</domain>

<decisions>
## Implementation Decisions

- Treat `FLASK_ENV=development`, `APP_ENV=dev`, and test config as local runtimes.
- Default security flags to enabled outside local runtimes, with env overrides for deployment flexibility.
- Keep Flask-Limiter disabled under `TESTING=True` to preserve parity tests while enabling it in production-like runtime.

</decisions>

