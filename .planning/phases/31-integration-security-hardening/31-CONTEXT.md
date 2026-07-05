# Phase 31: Integration Security Hardening - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning
**Mode:** Autonomous from TODO.MD

<domain>
## Phase Boundary

Harden Google OAuth persistence, webhook outbound requests, CSRF exemptions, and upload entry points.

</domain>

<decisions>
## Implementation Decisions

- Repository methods own Google user/workspace persistence.
- Webhook URLs must resolve only to public IP addresses before requests are sent.
- Authenticated state-changing routes use normal CSRF protection; frontend already injects `X-CSRFToken`.
- Upload routes validate extension, MIME type, and configured size before reading or saving files.

</decisions>

