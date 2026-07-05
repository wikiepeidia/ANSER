# Project: ANSER

ANSER (Automated Nimble Software Easing Relaxation) is an AI/ML-integrated automation platform designed for retail management and workflow automation. It combines OCR for invoice processing, LSTM-based forecasting, AI-driven chat agents, and a flexible drag-and-drop workflow engine to streamline business operations.

## Core Value
To provide a unified, intelligent platform that automates repetitive retail tasks (invoicing, inventory, forecasting) through a modular and extensible architecture, enabling business owners to focus on strategic growth rather than manual data entry.

## High-Level Goals
1. **Intelligent Automation**: Automate invoice data entry using high-accuracy OCR and AI parsing.
2. **Predictive Analytics**: Provide reliable inventory and sales forecasting using LSTM models.
3. **Conversational Interface**: Enable users to manage operations through an AI agent chat interface.
4. **Flexible Workflows**: Allow users to build custom automation DAGs (Directed Acyclic Graphs) connecting Google services, webhooks, and AI models.
5. **Robust Foundations**: Maintain a stable, refactored backend that supports collaborative development and scalable integrations.

## Target Audience
- Retail business owners and managers.
- Internal operations teams seeking to automate document processing.
- Developers building modular AI-integrated automation tools.

## Success Metrics
- **Accuracy**: >90% accuracy in automated invoice field extraction.
- **Efficiency**: >50% reduction in time spent on manual inventory updates.
- **Stability**: <1% error rate in scheduled workflow executions.
- **Developer Velocity**: New features can be added via isolated service/route modules without impacting the core monolith.

## Current Milestone: v1.2 Security & Ownership Hardening

**Goal:** Execute the remaining `TODO.MD` backlog that closes backend security gaps, enforces tenant ownership boundaries, and finishes deployment/runtime consistency work before the next feature push.

**Target features:**
- Harden production-sensitive config, webhook/network validation, CSRF coverage, upload constraints, and client-facing error responses
- Enforce per-owner or per-workspace data scoping across sales, products, customers, reports, and automation rules
- Align Google-auth password hashing, remaining database access patterns, repository usage, and worker deployment checks

### Completed Milestones

#### Deadline Rush: Backend Cleanup (June 2026)
Successfully resolved critical technical debt including circular imports, logic duplication in authentication, environment isolation, and implemented async task infrastructure (Redis/RQ) for performance.

#### v1.1: Tech Debt Completion (June 2026)
Resolved circular import cleanup, automation schema drift, DL runtime logging/OCR validation, and deferred code hygiene bugs across the backend.

## Active Requirements
- SEC-01: Production-sensitive cookie, rate-limit, HTTPS, and HSTS flags are enabled by default outside `dev`/`test`, while local development remains unblocked
- OWN-01: Users cannot delete sales they do not own
- OWN-02: Product and customer list/update/delete operations enforce creator/role ownership boundaries
- OWN-03: Reports, scheduled reports, and automation rules are scoped to the owning user or workspace
- AUTH-06: Google-created accounts use `AuthManager.hash_password`/bcrypt so password setup and password login remain consistent
- SEC-02: User-configured webhooks reject destinations resolving to private or link-local IP ranges
- SEC-03: Authenticated state-changing routes keep CSRF protection unless they are true third-party webhooks
- SEC-04: Global and route-level error handlers stop exposing raw exception details to clients and return traceable error identifiers instead
- SEC-05: File upload endpoints enforce size and type restrictions with clear validation errors
- PLAT-01: Remaining routes stop importing module-level database globals and use `current_app.extensions['database']`
- PLAT-02: Google OAuth persistence paths use repository abstractions instead of route-level raw SQL
- PLAT-03: Deployment/runtime documentation and checks confirm an RQ worker is present for queued AI jobs

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-05 (v1.2 Security & Ownership Hardening milestone started from TODO.MD backlog)*
