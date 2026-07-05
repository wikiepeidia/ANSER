# Phase 32: Error Handling & Data Access Cleanup - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning
**Mode:** Autonomous from TODO.MD

<domain>
## Phase Boundary

Stop exposing raw exception strings for the named API paths and remove route-level database shortcuts identified in TODO.MD.

</domain>

<decisions>
## Implementation Decisions

- API 500 responses return generic text plus correlation IDs.
- Known validation and not-found errors may still return their controlled messages.
- `sales_routes.py` resolves database access from `current_app.extensions['database']`.
- Google OAuth raw SQL moves into repository methods.

</decisions>

