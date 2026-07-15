# ANSER — Project Overview

**ANSER** (Automated Nimble Software Easing Relaxation) is an AI-powered automation platform for retail businesses. It reads invoices automatically, predicts inventory and sales trends, lets you chat with an AI agent to manage operations, and connects to your existing tools (Google Drive/Sheets/Gmail, n8n, Make.com) through drag-and-drop workflows.

**Status:** Stable — v1.2 (Security & Ownership Hardening) shipped 2026-07-05, fully tested.

---

## What it does

- **Invoice automation (OCR)** — upload an invoice photo/PDF, the system reads and extracts the data automatically (>90% field accuracy target).
- **Sales & inventory forecasting (AI/LSTM)** — predicts future stock needs and sales trends from historical data.
- **AI chat assistant** — a conversational agent that can look up data, answer questions, and trigger actions in the app.
- **Workflow automation** — build custom automations (e.g. "new invoice → update inventory → notify on Slack") using n8n and Make.com webhook integrations, no code required.
- **Sales, inventory, customer & reporting management** — core retail back-office: products, sales records, customers, scheduled reports, wallet/subscription billing.
- **Google Workspace integration** — sign in with Google, sync to Drive/Sheets, send email via Gmail, pull traffic stats from Analytics.
- **Multi-user accounts with data ownership** — every user only sees and edits their own sales, products, customers, reports, and automations (enforced as of v1.2).

---

## How it's built

### Frontend / UI-UX

- Server-rendered pages (Jinja2 HTML templates in `ui/templates/`) with JavaScript for interactivity (`static/js/`) and CSS styling (`static/css/`).
- Includes a customer dashboard, admin panels (users, subscriptions, warehouses), workflow builder, and AI chat interface.
- No separate single-page-app framework — pages are rendered by the Flask backend and enhanced with fetch-based JS.

### Backend

- **Main app** (`app.py`) — Python/Flask, organized as Routes → Services → Database layers for maintainability.
- Handles authentication (email/password + Google OAuth), sales/inventory/customer APIs, reporting, billing/wallet, and workflow orchestration.
- Background job queue (Redis + RQ) handles slow tasks (like AI chat responses) without blocking the app.

### AI / Machine Learning

- **Deep Learning service** — a separate model server for OCR (invoice reading) and LSTM-based forecasting (inventory/sales predictions).
- **AI Agent service** — a separate multi-agent server (manager, coder, researcher, vision agents) that powers the conversational assistant, using a self-hosted LLM.

### Database

- **PostgreSQL** in production, **SQLite** for local development — same codebase supports both.
- Schema changes tracked with Alembic migrations (`migrations/`).

### Integrations

- Google (OAuth login, Drive, Sheets, Docs, Gmail, Analytics)
- n8n (self-hosted workflow automation, via Docker)
- Make.com and generic outbound webhooks (with SSRF protection — blocks requests to internal/private network addresses)

### Security (hardened in v1.2, 2026-07-05)

- Secure cookies, HTTPS/HSTS, and rate limiting enabled automatically outside local development.
- Every user's data (sales, products, customers, reports, automations) is scoped to its owner — no cross-account data leaks.
- CSRF protection on all authenticated actions (except genuine third-party webhooks).
- File upload size/type limits; sanitized error messages (no internal details leaked to clients).
- Verified with a full automated test suite (171+ tests passing).

---

## Where things live (for reference)

| Area | Location |
| --- | --- |
| Main web app | `app.py`, `routes/`, `core/` |
| Frontend templates & assets | `ui/templates/`, `static/` |
| Database access & migrations | `core/db/`, `database/`, `migrations/` |
| AI chat agent service | `ai_agent_service/` |
| OCR / forecasting service | `dl_service/` |
| Automated tests | `tests/`, `dl_service/test/` |

*Full technical documentation for developers lives in `.planning/codebase/` (architecture, stack, conventions, testing, known issues).*

---

*Last updated: 2026-07-08*

link local: http://127.0.0.1:8791/