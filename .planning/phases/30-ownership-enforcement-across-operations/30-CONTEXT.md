# Phase 30: Ownership Enforcement Across Operations - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning
**Mode:** Autonomous from TODO.MD

<domain>
## Phase Boundary

Close cross-user data access gaps for sales, products, customers, reports, scheduled reports, and automation rules.

</domain>

<decisions>
## Implementation Decisions

- Admin users can access all records.
- Non-admin users can access only records where `created_by` or `user_id` matches the current user.
- Unauthorized writes use rowcount checks and return not-found style errors instead of exposing owner existence.

</decisions>

