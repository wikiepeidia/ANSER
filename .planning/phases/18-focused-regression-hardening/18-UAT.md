---
status: testing
phase: 18-focused-regression-hardening
source: [18-01-SUMMARY.md]
started: 2026-06-14T21:30:00Z
updated: 2026-06-14T21:30:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running server. Run: python app.py
  Server should boot without errors.
  Open http://127.0.0.1:5000 — login page or dashboard loads (no 500, no import error).
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: App boots cleanly with `python app.py`. No import errors, no AttributeError on startup. http://127.0.0.1:5000 loads.
result: pending

### 2. Login Works
expected: Go to http://127.0.0.1:5000/login. Enter valid credentials. You reach the dashboard — no 500 error, no "AttributeError: 'sqlite3.Row' object has no attribute 'get'".
result: pending

### 3. User List Loads (Admin)
expected: Go to http://127.0.0.1:5000/admin/users (or the admin panel). User list renders with names and emails visible — no 500, no crash.
result: pending

### 4. Create Import Transaction
expected: Navigate to the Imports page. Submit a new import (product + quantity + price). Response shows success — no 500, transaction appears in list.
result: pending

### 5. Create Export Transaction
expected: Navigate to the Exports page. Submit a new export. Response shows success — no 500, transaction appears in list.
result: pending

### 6. AI Chat Still Works
expected: Navigate to the AI chat page. Send a message. You get a job ID back immediately (async). Polling shows "completed" eventually — no crash, no 500.
result: pending

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0

## Gaps

[none yet]
