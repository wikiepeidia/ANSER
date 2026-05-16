# Phase 12: Service Boundary Extraction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves alternatives considered.

**Date:** 2026-04-16
**Phase:** 12-service-boundary-extraction
**Areas discussed:** Extraction Priority Order, Service Contract Style, Handler Extraction Map Format, Unit Test Scope, Data Access Boundary

---

## Extraction Priority Order

| Option | Description | Selected |
|--------|-------------|----------|
| Critical domains first | Extract workflow, AI, and import/export logic before lower-risk CRUD | x |
| CRUD first | Start with simpler handlers to warm up extraction flow | |
| Big-bang migration | Move all major domains before testing | |

**User's choice:** Critical domains first (recommended default selected autonomously)
**Notes:** Maintains highest-risk reduction earliest and aligns with existing Phase 11 contract guardrails.

---

## Service Contract Style

| Option | Description | Selected |
|--------|-------------|----------|
| Plain Python inputs + typed service exceptions | Routes map exceptions to HTTP responses; no Flask objects in services | x |
| Flask-aware services | Pass request/session directly into service layer | |
| Hybrid per-handler | Allow mixed signatures per migrated handler | |

**User's choice:** Plain Python contracts with route-level HTTP mapping (recommended default selected autonomously)
**Notes:** Preserves testability and keeps Flask coupling at route layer.

---

## Handler Extraction Map Format

| Option | Description | Selected |
|--------|-------------|----------|
| Phase-local markdown map | Table includes source handler, target service, status, and test link | x |
| Spreadsheet-only tracking | External sheet for migration tracking | |
| Inline comments in app.py | Track extraction progress in code comments only | |

**User's choice:** Phase-local markdown extraction map (recommended default selected autonomously)
**Notes:** Keeps migration state versioned with the phase artifacts and visible to downstream agents.

---

## Unit Test Scope (TEST-02)

| Option | Description | Selected |
|--------|-------------|----------|
| High-risk service logic first | Add service unit tests for extracted critical domains before expanding | x |
| Full-domain test coverage first | Attempt broad service coverage before incremental extraction | |
| Keep only contract tests | Do not add dedicated service-layer tests in Phase 12 | |

**User's choice:** High-risk service logic first (recommended default selected autonomously)
**Notes:** Phase 11 contracts remain the parity gate while Phase 12 adds focused unit safety nets.

---

## Data Access Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse current DB abstraction | Use `core/database.py` directly from extracted services in this phase | x |
| Introduce repository layer now | Add new DAO/repository abstraction during extraction | |
| Per-service ad-hoc DB wrappers | Let each service define custom DB access style | |

**User's choice:** Reuse current DB abstraction (recommended default selected autonomously)
**Notes:** Avoids scope creep and keeps Phase 12 focused on service boundary extraction.

---

## the agent's Discretion

- Service module split strategy by domain size.
- Exception class hierarchy for service-to-route error mapping.
- Fixture structure for service tests.

## Deferred Ideas

- Repository/DAO abstraction redesign.
- Blueprint relocation and final composition-root refactor (Phase 13).
- Full low-risk CRUD migration before critical-path extraction.
