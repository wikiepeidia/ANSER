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
  "validation": {"is_valid": true, "calculated_total": 0, "difference": 0},
  "needs_manual_review": false
}
```

`needs_manual_review` is a top-level boolean field — there is no status-string field
anywhere in Brain's real response (unlike v1.0's speculative `status` string).

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

**Endpoint:** `POST http://host.docker.internal:5000/api/n8n/internal/invoice-import-draft`

**This endpoint does not exist yet.** It is Body-side backend work, out of scope for this
milestone (a teammate's parallel effort), matching the naming convention of the 3 existing
`/api/n8n/internal/*` GET endpoints in `routes/n8n_api.py` (lines 304-369: `/warehouses`,
`/low-stock`, `/iot-events`).

Request body the workflow sends:

```json
{
  "status": "pending_review",
  "brain_response": "<full Brain response body>",
  "source": "<source>",
  "received_at": "<ISO timestamp>"
}
```

**Safety invariant:** this call must never carry `status: "completed"` — its only job is
to create a pending-review draft, never to finalize an import. The workflow enforces this
by hardcoding the literal string `pending_review` in the write-back node's `jsonBody`
expression, rather than passing Brain's status field through.

## Auth Notes

- The Brain call uses the `X-API-Token` header, matching Body's existing Brain-auth
  mechanism in `core/services/ai_chat_service.py`.
- The Body write-back call and the 3 existing `/api/n8n/internal/*` GET endpoints have
  **no auth check** — verified directly against `routes/n8n_api.py`. This branch has no
  `ANSER_WEBHOOK_TOKEN`-equivalent (unlike `anser-san-xuat`, which has one).
- This is a known, pre-existing gap, not fixed this milestone — new auth scope is
  explicitly deferred (see `01-CONTEXT.md` § Deferred Ideas).

## Notification Contract

The Discord webhook URL is read from the incoming webhook request body's `discord_url`
field (`$('Nhận hóa đơn').first().json.body.discord_url`), matching
`notify_discord.json`'s existing `webhookBody.discord_url` pattern exactly — see its
`Tạo Discord Embed` code node — not a stored per-warehouse profile. The caller triggering
the workflow must supply `discord_url` in their POST body for notifications to be
deliverable; if omitted, the Discord send node will POST to an empty URL and fail silently
within its own branch (does not affect the write-back path).

## Open Questions for Brain Team

- Exact JSON shape of `AgentMiddleware.process_ai_response()`'s Tier 2 return value —
  currently undocumented, Brain-internal.
- Confirm the `/api/invoice/digitize` path against Brain's actual router once it exists.
- Confirm whether Brain expects `invoice_image` as a multipart file field (as this
  contract assumes) or a base64-encoded JSON field instead.
