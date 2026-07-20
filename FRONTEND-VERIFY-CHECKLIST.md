# Frontend UAT Checklist (2026-07-20)

Curl/pytest already proved the backend is correct. This checklist is different: it catches **frontend-only bugs** — broken error handling, unhandled promise rejections, stale UI — that curl can't see because curl never runs the browser's JS.

## What I found before you even start (already fixed)

Phase 2.1 added QC-02 (`/api/bom/calculate` can now return **409** if a required material's batches aren't QC-passed). That endpoint used to **always succeed** — three existing, already-shipped frontend pages called it with **zero error handling**, so a 409 would silently break them:

| File | What broke | Fix applied |
|---|---|---|
| `static/pages/bom.html` | "Tính cho X đơn vị" button — click did nothing, no error shown | Wrapped in try/catch, shows a toast on failure |
| `static/pages/production-order-detail.html` | Entire order detail page stopped rendering past the BOM section (cost, timeline, action buttons all missing) | Isolated the BOM section in its own try/catch — rest of the page still renders |
| `static/pages/production-costs.html` | One QC-blocked order would sink the whole `Promise.all`, blanking the entire report table | Isolated per-order, failed orders show "—" instead of crashing the page |

This is a real regression from Phase 2.1, not the known "frontend never wired" gap — these 3 pages ARE wired to the real backend, they just didn't expect the real backend to ever say no. **Please re-verify these 3 specifically** — the fix is small but I haven't clicked through it myself.

## Part 1 — Re-verify existing (already-shipped) flows still work

These worked before this session; confirm nothing regressed.

- [ ] **1. Production orders list** — open `#production-orders`, list loads, filter by status works.
- [ ] **2. Create + view an order** — create a new order, click into its detail page. Confirm the BOM table, cost, and action buttons ALL render (this is the page I just patched — if it's still broken, tell me exactly what's missing).
- [ ] **3. BOM calculate button** — go to `#bom`, pick a product with a saved BOM, click "Tính cho X đơn vị". Confirm it shows a result table (or, if you've QC'd a batch and it fails, confirm you see a **toast message**, not a silently-dead button).
- [ ] **4. Production costs report** — open the costs/waste report page. Confirm it loads with a table of orders (or "—" for any order it can't cost, not a blank page).
- [ ] **5. Order status transitions** — approve/transition an order through its lifecycle, confirm no console errors.

## Part 2 — Trigger the actual QC-02 gate in the browser (the new behavior)

This proves the fix works, not just that it doesn't crash.

- [ ] **6.** Create a material batch for some material code (via curl/API — no batch-creation UI exists yet, see Part 3). Leave its `qc_status` as `pending` (default — don't QC it).
- [ ] **7.** Find or create a product whose BOM includes that exact material code, with a required quantity greater than what's available.
- [ ] **8.** Go to that product's BOM calculate button (`#bom`) — click "Tính cho X đơn vị" with a quantity that would need more than the pending batch covers. **Expected:** a toast/error message naming the material, NOT a silent failure.
- [ ] **9.** Open a production order for that same product's detail page. **Expected:** the BOM card shows a red warning message inline, but the rest of the page (customer info, status, actions, timeline) still renders normally.

## Part 3 — Honest scope note: what you WON'T see working in the browser yet

The milestone audit already found this and it's tracked as backlog, not a bug — just don't be surprised:

- **Material batches page, QC page, warehouse pages** — these still read/write `localStorage` (the original mock), NOT the real backend. Creating a batch, recording QC, or transferring stock through these pages does **not** touch the real database — only n8n and direct API calls do right now. Clicking through them will "work" (no crashes) but won't reflect real data. This is the known gap from the audit (`.planning/v1.0-MILESTONE-AUDIT.md`), not something to test/report here.

## When done

Tell me pass/fail per numbered item (1-9). For anything in Part 1/2 that fails, paste what you saw (console error, screenshot description, whatever) and I'll fix it.
