# Phase 11: Baseline Contract Guardrails - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 11-Baseline Contract Guardrails
**Areas discussed:** Critical endpoint baseline scope

---

## Critical endpoint baseline scope

| Option | Description | Selected |
|--------|-------------|----------|
| Core refactor-critical set only | Auth + workflow execution + AI chat/status + Smart Import/Export APIs; lowest overhead and fastest to unblock Phase 12 | ✓ |
| Core set plus billing/admin | Adds wallet/subscription/admin analytics baseline in Phase 11 | |
| Near-full API surface | Maximum early coverage with highest setup cost before extraction | |

**User's choice:** Core refactor-critical set only
**Notes:** Keep baseline narrow for Phase 11 delivery speed.

| Option | Description | Selected |
|--------|-------------|----------|
| Track presence/status only for key pages | Track route/method and expected status for `/`, `/dashboard`, `/imports`, `/exports` | ✓ |
| Full HTML snapshot assertions | Deep UI snapshot checks for selected pages | |
| Exclude UI routes from Phase 11 baseline | Baseline only JSON API routes now | |

**User's choice:** Track presence/status only for key pages
**Notes:** Include key UI page stability without brittle snapshot burden.

| Option | Description | Selected |
|--------|-------------|----------|
| Method+path+status and minimal response-shape checks | Balanced contract checks for initial guardrails | ✓ |
| Strict response-body key/value assertions | Stronger regression detection with higher maintenance | |
| Method+path inventory only (no response checks) | Fastest setup, weakest behavioral signal | |

**User's choice:** Method+path+status and minimal response-shape checks
**Notes:** Prioritize actionable drift detection with moderate implementation cost.

| Option | Description | Selected |
|--------|-------------|----------|
| Versioned manifest file in .planning plus generated snapshot | Explicit curated source + auto-generated comparison artifact | ✓ |
| Generated snapshot only | Auto-discovery based source with less explicit curation | |
| Manual checklist in markdown only | Human-readable but not robust for automated enforcement | |

**User's choice:** Versioned manifest file in .planning plus generated snapshot
**Notes:** Prefer reviewable baseline plus automated drift checks.

## the agent's Discretion

- Manifest schema details and assertion implementation details remain open for planning.

## Deferred Ideas

- Endpoint inventory artifact representation specifics (within Phase 11)
- Extended guardrail strictness beyond minimal response shape (within Phase 11)
- Detailed migration wave/rollback policy definition (within Phase 11)
