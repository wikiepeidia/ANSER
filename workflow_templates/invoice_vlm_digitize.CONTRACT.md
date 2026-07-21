# Body ↔ Brain HTTP Contract — Invoice VLM Digitization

## Overview

This document is the contract that `workflow_templates/invoice_vlm_digitize.json`'s HTTP
Request nodes encode. Brain's `/api/invoice/digitize` endpoint does not exist in this
checkout, so this is a documented-first contract — written to match exactly what the n8n
workflow's nodes reference — not a live-tested integration. Per this milestone's scope
(see `.planning/PROJECT.md` § Out of Scope), Brain's model/engine code and
`routes/dl_routes.py`/`dl_client.py` are out of scope; building the actual endpoints this
doc describes is a teammate's parallel, separate effort.

## Config / Env Vars

| Var | Purpose |
|-----|---------|
| `BRAIN_URL` | Brain's base origin (e.g. `https://xxxx.ngrok-free.app`). Mirrors the `N8N_ORIGIN` pattern in `core/config.py` lines 34-37, but must be set as an **n8n runtime environment variable** — e.g. added to `docker-compose.yml`'s n8n service `environment:` block — not a Python `.env` var, since the workflow reads it via n8n's `$env.BRAIN_URL` expression syntax at execution time, not Flask's `Config` class. |
| `BRAIN_TOKEN` | Brain auth token sent via the `X-API-Token` header on the digitize call. Recommend it holds the same value already used for Body's existing Brain integration (see the `HF_TOKEN`/`X-API-Token` pattern in `core/services/ai_chat_service.py` lines 160-166), so operators manage one Brain credential, not two. Also set as an n8n environment variable (`$env.BRAIN_TOKEN`), never committed to the workflow JSON itself. |

## Request Contract (n8n -> Brain)

**Endpoint:** `POST {BRAIN_URL}/api/invoice/digitize`

This is a **proposed** path, not confirmed against Brain's actual router since Brain isn't
in this checkout, per `01-CONTEXT.md`'s "Brain Endpoint Shape" decision. The workflow calls
ONE encapsulated endpoint, not Tier 1 and Tier 2 separately — Brain is expected to sequence
its own Tier 1 (Qwen2-VL-2B image→JSON) and Tier 2 (Qwen2.5-7B verify/match/action) logic
internally and return a single combined result.

- **Content-Type:** `multipart/form-data`
- **Body fields:**
  - `invoice_image` (binary file, JPEG/PNG) — the uploaded invoice image, sent as
    `formBinaryData` from the incoming webhook's binary payload.
  - `source` (string, optional) — provenance tag such as `discord_forward` or
    `scan_station`; defaults to `n8n` when the caller omits it.
- **Header:** `X-API-Token: {BRAIN_TOKEN}`
- **Timeout:** 120000ms (120s), matching the workflow node's `options.timeout`.

## Response Contract (Brain -> n8n)

Brain's `/api/invoice/digitize` response is expected to take one of three shapes:

**(a) `needs_manual_review`** — Tier 1's `quick_sanity_check()` failed (unparseable,
no line items, `overall_confidence < 0.5`, missing required fields, or a line's
confidence `< 0.4`). This shape IS fully specified per the source doc:

```json
{"status": "needs_manual_review", "issues": [...], "raw": "<original Tier-1 text>"}
```

**(b) `pending_review`** — Tier 2's result, i.e. whatever `AgentMiddleware` returns after
parsing Tier 2's JSON action. Per `SYSTEM_D`'s explicit safety rule
(`ANSER_Brain_Ke_hoach_Tong_hop.pdf` §3.4): status from Tier 2 is **never** `"completed"`,
always at best `"pending_review"`. The exact envelope of the proposed-action payload is
Brain-internal and not specified in either source doc (it's the output of
`AgentMiddleware.process_ai_response()`) — the workflow only depends on the top-level
`status` field to branch, and passes the full response body through to the write-back call
untouched. **This shape needs Brain-team confirmation once their endpoint exists.**

For reference, the Tier 1 `VLM_INVOICE_PROMPT` schema fields the eventual result is
expected to be derived from:

```
supplier_name, invoice_code, invoice_date,
items[]: { line, name, quantity, unit, unit_price, amount, confidence },
subtotal, vat_rate, vat_amount, total_amount, overall_confidence
```

**(c) HTTP error** — non-2xx, timeout, or connection failure (e.g. the Brain ngrok tunnel
being down, flagged in `ANSER_AI_SPEC.md` §8.2 item 6 as a single-point-of-failure risk).
The workflow's Brain-call node has `continueOnFail: true`, so a failure produces
`{"error": "<message>"}` on the item instead of killing the execution, and is treated
identically to `needs_manual_review` for notification purposes — both route to the same
Discord path.

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
