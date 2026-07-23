# Body ↔ Brain HTTP Contract — Invoice VLM Digitization

## Overview

This document is the contract that `workflow_templates/invoice_vlm_digitize.json`'s HTTP
Request nodes encode. Brain's `/ocr` endpoint's path and request/response shapes have now
been directly verified against Brain's real route/schema source
(`ANSER_AI/src/api/routes/documents.py`, `schemas.py`) this session, so this doc is no
longer purely documented-first on the Brain side — though the pipeline remains untested
end-to-end since Brain itself isn't live in this checkout (see Phase 4 for mock-based
verification). Per this milestone's scope (see `.planning/PROJECT.md` § Out of Scope),
Brain's model/engine code and `routes/dl_routes.py`/`dl_client.py` stay out of scope for
this milestone.

## Config / Env Vars

| Var | Purpose |
|-----|---------|
| `BRAIN_URL` | Brain's base origin (e.g. `https://xxxx.ngrok-free.app`). Mirrors the `N8N_ORIGIN` pattern in `core/config.py` lines 34-37, but must be set as an **n8n runtime environment variable** — e.g. added to `docker-compose.yml`'s n8n service `environment:` block — not a Python `.env` var, since the workflow reads it via n8n's `$env.BRAIN_URL` expression syntax at execution time, not Flask's `Config` class. |
| `BRAIN_TOKEN` | Brain auth token sent via the `X-API-Token` header on the digitize call. Recommend it holds the same value already used for Body's existing Brain integration (see the `HF_TOKEN`/`X-API-Token` pattern in `core/services/ai_chat_service.py` lines 160-166), so operators manage one Brain credential, not two. Also set as an n8n environment variable (`$env.BRAIN_TOKEN`), never committed to the workflow JSON itself. |
| `ANSER_N8N_INTERNAL_TOKEN` | Body's write-back shared secret, checked via `hmac.compare_digest` against the `X-Webhook-Token` header in `routes/n8n_api.py`'s `/api/n8n/internal/invoice-import-draft` handler — same pattern as `BRAIN_TOKEN`: set as an n8n runtime environment variable, never committed to the workflow JSON. |

## Request Contract (n8n -> Brain)

**Endpoint:** `POST {BRAIN_URL}/ocr`

Confirmed directly against Brain's real route (`ANSER_AI/src/api/routes/documents.py`) this
session — no longer "proposed"/unconfirmed. The workflow calls ONE encapsulated endpoint;
Brain is expected to sequence its own internal VLM/verification logic and return a single
combined result.

- **Content-Type:** `multipart/form-data`
- **Body field:** `file` (binary, JPEG/PNG) — the uploaded invoice image, sent as
  `formBinaryData` from the incoming webhook's binary payload. Brain's route signature is
  `file: UploadFile = File(...)`, so this field name is not configurable.
- **Headers:**
  - `X-API-Token: {BRAIN_TOKEN}`
  - `ngrok-skip-browser-warning: true` — Brain is tunneled via ngrok in every deployment
    scenario seen this session (Colab notebook's `ngrok.connect(8000)`); this matches the
    proven fix in `core/services/ai_chat_service.py` lines 160-166 for the ngrok
    interstitial page breaking JSON responses.
- **Timeout:** 120000ms (120s), matching the node's `options.timeout`.

There is no `source` body field on this call — Brain's `/ocr` route signature accepts no
parameters other than `file`. `source` is only meaningful to the write-back call below.

## Response Contract (Brain -> n8n)

Brain's `/ocr` response takes one of three shapes, confirmed directly against
`documents.py`/`schemas.py` this session:

**(a) Success / flagged result:**

```json
{
  "success": true,
  "backend": "...",
  "invoice": {
    "items": [{"name": "...", "price": 0, "qty": 0, "is_reduced_vat": false}],
    "total": 0
  },
  "validation": {
    "is_valid": true,
    "calculated_total": 0,
    "stated_total": 0,
    "difference": 0,
    "tolerance": 0,
    "lines": [{"name": "...", "base": 0, "tax_rate": 0.1, "line_total": 0}]
  },
  "needs_manual_review": false
}
```

`needs_manual_review` is a top-level boolean field — there is no status-string field
anywhere in Brain's real response (unlike v1.0's speculative `status` string).

**Live-confirmed 2026-07-23** against a real running Brain instance (not just read from
source): `validation` has more fields than originally documented from source alone —
`stated_total`, `tolerance`, and a per-line `lines[]` breakdown (`name`, `base`, `tax_rate`,
`line_total`) in addition to `is_valid`/`calculated_total`/`difference`. None of the extra
fields are consumed by Body's write-back endpoint (`_require_clean_invoice()` only checks
`success`/`needs_manual_review`/`invoice.items`/`invoice.total`), so this doesn't change the
integration contract — documented here for completeness. The deterministic-first arithmetic
re-check was also confirmed live: a real mismatch between extracted line totals and the
stated total correctly produced `is_valid: false` and `needs_manual_review: true`.

**(b) Brain business-logic failure** — either:

```json
{"success": false, "backend": "...", "error": "...", "raw": "..."}
```

(VLM extraction failed) or:

```json
{"success": false, "error": "schema_invalid: ...", "raw_json": "..."}
```

(schema validation failed).

**(c) HTTP/connection failure** — non-2xx, timeout, or connection failure (e.g. the Brain
ngrok tunnel being down). The workflow's Brain-call node has `continueOnFail: true`, so a
failure produces `{"error": "<message>"}` on the item instead of killing the execution —
unchanged from before, and still treated as its own branch (checked first in
`iv-normalize`), routed to the same Discord path as a flagged/failed result.

## Body Write-Back Contract (n8n -> Body)

**Endpoint:** `POST http://host.docker.internal:5002/api/n8n/internal/invoice-import-draft`

This endpoint now exists — shipped in Phase 2 as
`core/services/invoice_draft_service.create_invoice_draft()`, wired at
`routes/n8n_api.py`'s `POST /api/n8n/internal/invoice-import-draft` handler (lines
702-740). It is a dedicated insert-only writer, deliberately separate from
`inventory_tx_service.create_import_transaction()`: it always writes
`status='pending_review'` as a literal SQL value, never mutates `warehouse_stock` or
`products.stock_quantity`, and never auto-creates a `products` row for an unmatched line
item.

Request body the workflow sends:

```json
{
  "success": true,
  "needs_manual_review": false,
  "invoice": {"items": [{"name": "...", "price": 0, "qty": 0, "is_reduced_vat": false}], "total": 0},
  "source": "n8n_vlm"
}
```

`supplier_name`, `notes`, `warehouse_id` are optional per Phase 2's contract — this
workflow omits them, since no source value for them is currently available from the
webhook payload.

**Header:** `X-Webhook-Token: {ANSER_N8N_INTERNAL_TOKEN}`

Body's real responses (`routes/n8n_api.py`, `invoice_draft_service.py`):

- **`200`** — `{"success": true, "id": ..., "code": "...", "status": "pending_review", "matched_count": ..., "unmatched_count": ...}`
- **`400`** — `{"success": false, "error": "<validation message>"}` (e.g. missing
  `invoice.items`, `payload.success` not `true`, `needs_manual_review` truthy) — raised by
  `_require_clean_invoice()`.
- **`401`** — `{"success": false, "error": "unauthorized"}` (missing/wrong
  `X-Webhook-Token`).

**Safety invariant:** this call must never carry `success: false` or
`needs_manual_review: true` — its only job is to create a pending-review draft from a
clean, reviewable result. This is enforced by two independent layers: the workflow
hardcodes the literal booleans `success: true` and `needs_manual_review: false` in the
write-back node's `jsonBody` expression (never read from `$json.brain_response`), and
Body's own `_require_clean_invoice()` independently re-validates and rejects
`success !== true` or a truthy `needs_manual_review` server-side.

## Auth Notes

- The Brain call uses the `X-API-Token` header (unchanged), plus the new
  `ngrok-skip-browser-warning` header, matching Body's existing Brain-auth mechanism in
  `core/services/ai_chat_service.py`.
- The Body write-back call now HAS an auth check — `X-Webhook-Token` is compared via
  `hmac.compare_digest` against `Config.ANSER_N8N_INTERNAL_TOKEN` in `routes/n8n_api.py`,
  failing closed (`401 unauthorized`) when the header is missing/wrong or the env var is
  unset.
- The 3 existing unauthenticated `/api/n8n/internal/*` GET endpoints (`/warehouses`,
  `/low-stock`, `/iot-events`) remain unauthenticated — that is an explicit, separate
  scoping decision (v2 `FUTR-03`), not an oversight, and no longer this endpoint's gap.

## Notification Contract

The Discord webhook URL is read from the incoming webhook request body's `discord_url`
field (`$('Nhận hóa đơn').first().json.body.discord_url`), matching
`notify_discord.json`'s existing `webhookBody.discord_url` pattern exactly — see its
`Tạo Discord Embed` code node — not a stored per-warehouse profile. The caller triggering
the workflow must supply `discord_url` in their POST body for notifications to be
deliverable; if omitted, the Discord send node will POST to an empty URL and fail silently
within its own branch (does not affect the write-back path).

## Open Questions for Brain Team

- Exact multipart property name a real trigger source (Discord forward vs. scan-station
  webhook) will actually populate on the incoming webhook — still unconfirmed, since no
  trigger source has been chosen yet. The webhook's own `inputDataFieldName: "data"`
  assumption (`iv-brain-call`'s `bodyParameters`) is untested against a live trigger;
  verify it empirically via n8n's binary-data inspector once a real trigger source is
  chosen, rather than assuming it's correct.

The exact endpoint path and response shape for Brain's `/ocr` call are no longer open
questions — both were confirmed directly against Brain's real route/schema source
(`ANSER_AI/src/api/routes/documents.py`, `schemas.py`) this session; see Request/Response
Contract above.
