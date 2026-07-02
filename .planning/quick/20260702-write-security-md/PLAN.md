---
title: Write project-specific SECURITY.md
date: 2026-07-02
slug: write-security-md
status: in-progress
---

# Quick Task: Write SECURITY.md for GitHub

## Description

The repository's `SECURITY.MD` is still the default GitHub template
(generic 5.1.x version table and empty "Reporting a Vulnerability" stub).
Replace it with a project-specific policy that reflects ANSER's actual
stack and security model so contributors and security researchers know
how to report issues.

## Scope

- Replace `SECURITY.MD` with a tailored policy.
- Cover: supported versions, reporting flow, what counts as in-scope,
  out-of-scope, and the security-relevant integration surface
  (Google APIs, Make.com webhooks, OCR uploads, secrets, SECRET_KEY).
- Update `.planning/STATE.md` "Quick Tasks Completed" table on completion.

## Out of Scope

- Renaming the file to lowercase `SECURITY.md` (GitHub recognizes both,
  but the existing file is `SECURITY.MD` — keeping the same casing to
  avoid touching unrelated git history).
- Implementing any actual security controls (this is a docs-only change).
- Adding issue templates or CODEOWNERS.

## Verification

- File exists at repo root, is valid Markdown, and no longer contains
  the placeholder "Use this section to tell people..." boilerplate.
- Mentions ANSER by name, lists real integrations, includes a concrete
  reporting channel and expected response window.

## Commit

Single atomic commit on the current branch (`mixed`):
`docs(security): replace placeholder SECURITY.MD with ANSER-specific policy`