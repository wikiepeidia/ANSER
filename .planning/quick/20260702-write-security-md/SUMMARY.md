---
title: Write project-specific SECURITY.md
date: 2026-07-02
slug: write-security-md
status: complete
---

# Summary: Write SECURITY.md for GitHub

## What was done

Replaced the placeholder `SECURITY.MD` (default GitHub template) with a
policy tailored to ANSER's actual stack and security model.

## Files touched

- `SECURITY.MD` — fully rewritten (146 lines).
- `.planning/STATE.md` — added Quick Tasks Completed entry and bumped
  `last_updated` / `last_activity` to 2026-07-02.
- `.planning/quick/20260702-write-security-md/PLAN.md` — task plan.
- `.planning/quick/20260702-write-security-md/SUMMARY.md` — this file.

## Commit

`b737308 docs(security): replace placeholder SECURITY.MD with ANSER-specific policy`

## What the new policy covers

- Project context (ANSER, Flask + OCR/LSTM + Google APIs + Make.com).
- Supported versions table — only `main` and the latest release get fixes.
- Reporting flow — GitHub Security Advisories preferred, with email
  fallback; concrete checklist of what to include.
- Response window table — 5 / 10 / 30 / 90 day targets.
- In-scope targets — Flask app, DL service, AI agent service, workflow
  engine, webhooks, upload pipeline, auth, config.
- Out-of-scope — third-party deps, social engineering, DoS, self-XSS,
  stale branches.
- Operator hardening notes — `secrets/` hygiene, `SECRET_KEY`, env
  vars for credentials, OCR upload restrictions, service isolation.

## Verification

- File at repo root, valid Markdown, 146 lines.
- Placeholder text "Use this section to tell people..." is gone
  (`grep -c` returned 0).
- Mentions ANSER by name and lists real integrations.
- Committed atomically on branch `mixed`.