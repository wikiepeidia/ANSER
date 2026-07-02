# Security Policy

Thank you for taking the time to help keep **ANSER** (*Automated Nimble Software
Easing Relaxation*) and its users safe. ANSER is an AI/ML-integrated retail
automation platform built on Flask, with OCR-based invoice processing, LSTM
forecasting, an AI chat agent, a drag-and-drop workflow engine, and integrations
with Google services and Make.com webhooks. This page explains how to report a
security issue and what to expect from us.

---

## Supported Versions

ANSER is an active academic and team development project. We only provide
security fixes for the **current development branch** and the **most recent
released tag**. Older snapshots are not patched.

| Branch / Tag      | Supported          |
| ----------------- | ------------------ |
| `main`            | :white_check_mark: |
| Latest release    | :white_check_mark: |
| Older releases    | :x:                |
| Feature branches  | :x:                |

If you are running ANSER from a clone that is more than one minor version
behind `main`, please upgrade before reporting, or note the commit hash in
your report.

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security problems.** Public
issues let attackers find the bug before users can patch.

### Preferred channel: GitHub private vulnerability reporting

1. Go to the **Security** tab of this repository.
2. Click **"Report a vulnerability"** to open a private advisory draft that is
   only visible to the maintainers.
3. Include everything listed in *What to include* below.

### Fallback channel: email

If you cannot use the GitHub Security Advisories flow, email the maintainers at
the address listed in [`MAINTAINERS.md`](./MAINTAINERS.md) (or, if that file is
absent, the address in the repository's commit history). Encrypt sensitive
details with our PGP key if one is published in that file.

### What to include

A good report saves everyone time. Please include as much of the following as
you can:

- A clear **title** and short **summary** of the issue.
- The **affected component** (route, service, file) and the commit/tag you
  reproduced it against.
- **Steps to reproduce**, including any required configuration or fixtures.
- The **impact** you observed, and the worst-case impact you suspect.
- Whether the issue exposes **another user's data**, our secrets, or only
  your own data.
- Screenshots, payloads, or sanitized logs (redact tokens, passwords, and
  OAuth refresh tokens before attaching).

### What to expect

We are a small student and contributor team, so our response window is best
effort:

| Stage                                | Target window       |
| ------------------------------------ | ------------------- |
| First acknowledgement                | within 5 business days |
| Triage and severity assessment       | within 10 business days |
| Patch for critical issues            | as soon as feasible; we will coordinate a disclosure date with you |
| Patch for high / medium issues       | within 30 days of triage |
| Public disclosure                    | after a fix is released, or 90 days after acknowledgement, whichever comes first |

If we cannot reproduce the issue we will ask follow-up questions before
deciding to close it.

---

## In-Scope Targets

The following areas are part of ANSER's security boundary and are in scope
for reports:

- The Flask web application (`app.py`, `wsgi.py`, `routes/`, `core/`,
  `templates/`, `static/`).
- The deep-learning OCR / forecast service (`dl_service/`, `run_dl_service.py`).
- The AI agent service (`ai_agent_service/`, `worker.py`).
- Database access paths through `core/database.py` and `database/`.
- The workflow automation engine (`core/automation_engine.py`,
  `core/workflow_engine.py`).
- Webhook and HTTP integrations (`core/make_integration.py`,
  `core/google_integration.py`).
- File upload handling, especially the OCR invoice pipeline.
- Authentication, session, and `SECRET_KEY` handling.
- Configuration loading and `.env` parsing (`core/config.py`).

## Out-of-Scope Targets

The following are **not** part of this policy:

- Vulnerabilities in **third-party packages** that ANSER depends on. Please
  report those upstream (PyPI, GitHub) and open a regular issue here so we
  can bump the version.
- Issues that require a user to **already have shell access**, the
  `SECRET_KEY`, or other production credentials.
- **Social engineering** of project maintainers or contributors.
- **Volumetric / denial-of-service** attacks against demo deployments.
- **Self-XSS** that does not affect another user.
- Reports against **stale branches or forks** that have not been merged
  into `main`.

---

## Hardening Notes for Operators

If you run ANSER in production, please review the following before going
live. These are the most common sources of incidents we have seen:

- **Never commit anything under `secrets/`**. The folder holds Google
  service-account JSON files, OAuth tokens, and database dumps. Rotate any
  credential that has appeared in a public commit.
- **Set `SECRET_KEY` to a fresh, high-entropy value** via environment
  variable. The default in `core/config.py` is intentionally a placeholder
  that the app refuses to start with in production mode.
- **Set `POSTGRES_URL`, `REDIS_URL`, and Make.com / Google OAuth
  credentials through environment variables or a secret manager**, not in
  source files.
- **Restrict the OCR upload endpoint** (size, MIME type, rate) — uploaded
  files are processed by an ML service and can be a vector for SSRF or
  resource exhaustion.
- **Run `dl_service/` and `ai_agent_service/` as separate processes** with
  the narrowest possible network permissions; do not expose them on the
  public internet.

---

## Recognition

We are happy to credit reporters in the release notes (with your
permission). If you would prefer to stay anonymous, just say so in the
report.

Thank you for helping make ANSER safer for everyone who relies on it.