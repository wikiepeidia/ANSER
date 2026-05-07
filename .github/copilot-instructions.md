# Project Guidelines

> **Current Mode**: Collaborative development with GSD-assisted workflows.
> **Status**: Active refactor, stabilization, onboarding, and normal teammate-facing development. New features, fixes, docs, and cleanup are allowed when explicitly requested.

## Working Context
- This repository is actively managed with GSD artifacts in `.planning/`.
- At the start of a new session, read `.planning/STATE.md` first.
- If the task depends on scope, history, or milestone direction, also read `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, and the relevant section of `.planning/ROADMAP.md`.
- Write explanations and docs for collaborating developers and friends, not jury reviewers or academic evaluators.

## Teammate Support
- Assume some contributors are new to Git, branching, or GSD. Explain the next step in plain language when the user seems unsure.
- If the user asks to run GSD or does not know which workflow or agent to use, inspect the available local GSD assets and pick the smallest correct path.
- Prefer safe, incremental work. Summarize risky or branch-affecting operations before you do them.

## Git Safety
- Check the current branch before branch-affecting work.
- Only push, merge, rebase, reset, checkout, or sync branches when the user explicitly asks.
- Treat `main` and `demo` as protected or stable branches unless the user explicitly instructs otherwise.
- Prefer non-destructive operations. Do not force-push or rewrite history unless the user explicitly requests it and understands the impact.

## Code Style
- Languages: Python, HTML, CSS, JavaScript, and Markdown.
- Python uses 4 spaces and should stay close to the existing project style.
- Use UTF-8 compatible edits for Windows and OneDrive safety.
- Utility functions and classes should have docstrings when they introduce shared behavior.
- For Flask UI work, keep JavaScript and CSS in separate files when practical instead of embedding large blocks inside HTML templates.

## Architecture
- Main web app: `app.py`
- Shared logic and integrations: `core/`
- Ongoing route split and cleanup: `routes/`
- AI agent service: `ai_agent_service/`
- Deep learning service: `dl_service/`
- Database support: `core/database.py` and `database/`
- Templates and static assets: `templates/`, `ui/templates/`, and `static/`

## Run and Test
- Main app: `python app.py`
- AI agent service: `python ai_agent_service/main.py`
- DL service: `python run_dl_service.py` or `python dl_service/model_app.py`
- Prefer the narrowest relevant verification: nearby standalone scripts in `tests/`, `dl_service/test/`, or targeted service checks.

## Project Conventions
- Priorities now are stability, cleanup, onboarding, documentation, and teammate-friendly workflows.
- OCR, LSTM, and workflow execution are still high-value areas and should stay runnable.
- Shared utilities belong in `core/`.
- Google integrations live in `core/google_integration.py`.
- Make.com webhook integration lives in `core/make_integration.py`.
- Do not commit secrets from `secrets/` or environment-specific credentials.

<!-- GSD Configuration — managed by get-shit-done installer -->
# Instructions for GSD

- This is a GSD-managed repository. Use `.planning/` as the live source of truth.
- At the start of a fresh session or before the first GSD action, read `.planning/STATE.md`. Read `.planning/PROJECT.md` and `.planning/ROADMAP.md` when you need milestone, phase, or scope context.
- Treat `/gsd:...`, `/gsd-...`, and `gsd-*` as GSD invocations.
- For GitHub Copilot work, local GSD assets live under `.github/skills`, `.github/agents`, and `.github/get-shit-done/`.
- Equivalent GSD installs may also exist under `.agent/`, `.claude/`, `.codex/`, `.cursor/`, and `.gemini/`; check those folders when helping users of those tools.
- When the user asks for GSD, first inspect the available local GSD workflow, skill, or agent and choose the closest match.
- Do not force a full GSD workflow onto every task. Use it when the user explicitly asks for GSD or when the task is specifically about planning, roadmap, state, or workflow artifacts.
- Help first-time users: briefly explain what workflow you picked, what it does, and what the next sensible step is.
- After completing any `gsd-*` request or any deliverable produced through GSD, offer the next sensible step instead of stopping abruptly.
<!-- /GSD Configuration -->

