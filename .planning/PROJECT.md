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

## Current Milestone: v1.1 Tech Debt Completion

**Goal:** Finish all outstanding TODO items — clear remaining circular import issues, fix the automation engine schema bug, clean up DL service logging, and polish code hygiene.

**Target features:**
- Fix `app.py` module-level `create_app()`, create `wsgi.py`, remove `dl_client` sys.path hack and set `use_local=False`
- Fix `automation_engine.py` schema mismatch (missing `suppliers` table and `import_price` column in SQLite)
- Replace `print()` with `get_logger()` in `dl_client` and DL service; validate OCR end-to-end
- Code hygiene: `analytics_service` logger/Config.GA_PROPERTY_ID, `google_integration` escape fix, `utils.py` tuple→named column

### Completed Milestones

#### Deadline Rush: Backend Cleanup (June 2026)
Successfully resolved critical technical debt including circular imports, logic duplication in authentication, environment isolation, and implemented async task infrastructure (Redis/RQ) for performance.

## Active Requirements
- CIRC-01: Remove module-level `app = create_app()` from `app.py`
- CIRC-02: Create `wsgi.py` entry point for gunicorn
- CIRC-03: Remove `sys.path.insert` from `core/services/dl_client.py`; set `use_local=False` default
- AUTO-01: Fix `automation_engine.py` to not reference non-existent `suppliers` table or `import_price` column
- AUTO-02: Align SQLite schema (or automation logic) so low-stock and scheduled import run without exception
- DL-01: Replace all `print()` in `dl_client.py` and `dl_service/` with `get_logger()`
- DL-02: Validate OCR end-to-end (upload → detect → invoice_data JSON)
- DL-03: Confirm `dl_service` starts independently via `python run_dl_service.py`
- HYG-01: Fix `analytics_service.py` — logger, remove duplicate except, read `GA_PROPERTY_ID` from `Config`
- HYG-02: Fix `google_integration.py` list_files single-quote escape
- HYG-03: Fix `utils.py` `format_workspace_tree` — named column access instead of tuple index

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
*Last updated: 2026-06-13 (v1.1 Tech Debt Completion milestone started)*
