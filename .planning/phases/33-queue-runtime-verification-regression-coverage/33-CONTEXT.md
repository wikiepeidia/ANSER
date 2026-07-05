# Phase 33: Queue Runtime Verification & Regression Coverage - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning
**Mode:** Autonomous from TODO.MD

<domain>
## Phase Boundary

Prevent queued AI chat jobs from silently stalling and preserve the v1.2 hardening work with regression tests.

</domain>

<decisions>
## Implementation Decisions

- Non-greeting AI chat jobs require an active RQ worker unless explicitly overridden by env.
- Documentation must tell operators to run `worker.py`.
- Regression tests cover owner scoping, webhook blocking, upload validation, Google bcrypt, and automation ownership.

</decisions>

