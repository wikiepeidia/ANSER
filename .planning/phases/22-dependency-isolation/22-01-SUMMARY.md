---
phase: 22-dependency-isolation
plan: 01
subsystem: Infrastructure
tags: [dependencies, refactor, optimization]
requires: []
provides: [modular-requirements]
affects: [installation-workflow]
tech-stack: [python, pip, flask]
key-files: [requirements-base.txt, requirements-ml.txt, requirements-dev.txt, requirements.txt, README.md]
decisions:
  - Splitting requirements into base, ml, and dev tiers to reduce default environment bloat.
  - Root requirements.txt now redirects to requirements-base.txt for compatibility.
metrics:
  duration: 15m
  completed_date: "2026-06-08"
---

# Phase 22 Plan 01: Dependency Isolation Summary

Successfully refactored the project's dependency management by splitting the bloated `requirements.txt` into modular, tier-based files. This reduces the default installation size for the web application and prepares the ML components for complete isolation.

## Key Accomplishments

- **Modularized Requirements:**
  - Created `requirements-base.txt` containing only the core dependencies needed to run the Flask web application (approx. 25 packages).
  - Created `requirements-ml.txt` containing heavy Machine Learning and Deep Learning dependencies (torch, tensorflow, paddleocr, etc.).
  - Updated `requirements-dev.txt` with development tools, including the addition of `ruff` for linting.
- **Improved Installation Workflow:**
  - Updated the root `requirements.txt` to include `-r requirements-base.txt`, ensuring that standard `pip install -r requirements.txt` now installs only the lean base environment.
  - Updated `README.md` with clear instructions for each dependency tier (Base, ML, Dev).

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Verified that `requirements-base.txt` and `requirements-ml.txt` contain the correct package distributions based on the `package/requirements.txt` source.
- Verified that `requirements-dev.txt` includes `ruff`.
- Verified that `requirements.txt` correctly redirects to `requirements-base.txt`.
- Manual inspection of `app.py` confirms that the main application does not have direct, hard dependencies on the ML packages moved to `requirements-ml.txt` (it uses proxy clients or external APIs).

## Threat Flags

None introduced. All dependencies are sourced from the same original list in `package/requirements.txt`.

## Self-Check: PASSED
- [x] requirements-base.txt exists
- [x] requirements-ml.txt exists
- [x] requirements-dev.txt updated
- [x] requirements.txt updated
- [x] README.md updated
- [x] Commits 89bd5ae, 61a2752, 2d6fba6 exist
