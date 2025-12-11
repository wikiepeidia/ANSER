# Deep Learning App Integration Plan

## 1) What the deep-learning app already does (from `backup/deep learning models/app.py`)

- Flask service exposes blueprints: `model1_routes` (YOLO layout + OCR invoice detection), `model2_routes` (LSTM quantity forecast), `ocr_routes` (raw OCR), and `history_routes` (view/clear invoice history).
- Key endpoints (as printed on startup):
  - `POST /api/model1/detect` — upload invoice image, runs layout detector + OCR pipeline, returns structured invoice fields.
  - `POST /api/model2/forecast` — quantity forecast (takes prepared series/features).
  - `POST /api/ocr/` — upload image (`image` or `file`) for OCR only.
  - `GET /api/history`, `POST /api/history/clear` — basic history.
- Models load at startup via `services/model_loader.initialize_models()`, database initialized via `utils.database.init_database()`; static/templates live under that package (demo UI at `/`).

## 2) Integration approach (keep DL app as sidecar/microservice)

- Run the DL Flask app as its own process/container inside the same VNet/VPC; expose an internal base URL (e.g., `http://dl-service:5001`).
- Add a lightweight proxy layer in our main app to call DL APIs, handle auth, timeouts, and translate payloads to our domain objects.
- Keep model weight loading isolated in the DL service; main app only sends files/data and receives JSON.

## 3) Backend wiring in our app

- Create a gateway module (e.g., `core/services/dl_client.py`) with functions:
  - `detect_invoice(image_bytes, filename)` → calls `/api/model1/detect` (multipart form) and returns parsed fields + bounding boxes.
  - `run_ocr(image_bytes, filename)` → calls `/api/ocr/` for text-only OCR.
  - `forecast_quantity(series_payload)` → calls `/api/model2/forecast`.
- Add config keys: `DL_BASE_URL`, `DL_TIMEOUT`, `DL_API_KEY` (if we gate the service), and retry/backoff settings.
- Centralize error handling: classify `5xx` as retryable, surface friendly messages to UI, log correlation IDs.

## 4) Workflow Builder node ("OCR Invoice" → "Forecast" → downstream)

- Add a new integration node type `invoice_ocr` (category: integration):
  - Inputs: image URL/upload ref (from previous node), optional vendor hints.
  - Outputs: structured invoice JSON (fields, line items) and extracted plain text.
- Add a node type `invoice_forecast`:
  - Inputs: invoice JSON or product time series, optional historical context node ID.
  - Outputs: forecast result with confidence/ood flags.
- Node behavior: when executed, backend calls `dl_client.detect_invoice` then optionally `forecast_quantity`; pass results to next node in the workflow.
- Validation: block execution with a clear warning if DL service unreachable.

## 5) Import page hooks

- Use the same DL proxy to support a drag-and-drop uploader on Import page:
  - On file drop: POST to our backend `POST /import/invoice` → backend streams file to `/api/model1/detect` and returns structured data.
  - Show preview (detected fields, totals) and allow user corrections before saving into our DB.
  - Surface OOD/low-confidence signals from DL response (e.g., highlight low-confidence fields in amber).

## 6) Export page hooks

- Add an "Export structured invoice" action that pulls the cleaned invoice JSON and lets users:
  - Download CSV/JSON.
  - Push to downstream systems via existing export channels (Slack/email/webhook nodes).
- Include forecast outputs (quantity + confidence) when available; stamp the DL model version and timestamp for audit.

## 7) Minimal API contracts we should enforce

- `POST /import/invoice` (our backend): `multipart/form-data` with `file`; response: `{ invoice: {...}, text: "...", ood_score?: number, confidence?: number }`.
- `POST /workflow/node/invoice_ocr` (internal): accepts `{ fileRef | url, vendorHint? }`; bridges to DL `/api/model1/detect`.
- `POST /workflow/node/invoice_forecast`: accepts `{ timeseries: [...], meta? }`; bridges to DL `/api/model2/forecast`.

## 8) Deployment & ops checklist

- Run DL app with GPU if available; otherwise pin CPU threads to avoid starvation.
- Health check: add `/health` in DL app (simple 200) and wire liveness/readiness in orchestrator.
- Observability: log request IDs end-to-end (main app → DL app), capture latency and error rates.
- Security: restrict DL service to private network; require an internal token header from our backend.

## 9) Next steps (concrete TODOs)

- [ ] Stand up DL service locally on `:5001` using the copied DL service folder (see move list below).
- [ ] Add `core/services/dl_client.py` proxy with tests (mock DL responses).
- [ ] Define new workflow node types `invoice_ocr` and `invoice_forecast` in builder JS + backend execution engine.
- [ ] Wire Import page upload to `dl_client.detect_invoice`; display editable preview.
- [ ] Wire Export page to download/push cleaned invoice + forecast outputs.
- [ ] Add env configs (`DL_BASE_URL`, `DL_API_KEY`, timeouts) and per-env overrides.

## 10) Files to move into our project (do not depend on `backup/` at runtime)

Place under a new folder, e.g., `dl_service/` at repo root:

- `app.py` (Flask entrypoint) → `dl_service/app.py`
- `config.py` → `dl_service/config.py`
- `services/` → `dl_service/services/` (keep `model_loader.py`, `forecast_service.py`, `invoice_service.py`, `layout_service.py`, `ocr_service.py`)
- `api/` → `dl_service/api/` (keep `model1_routes.py`, `model2_routes.py`, `ocr_routes.py`, `history_routes.py`)
- `utils/` → `dl_service/utils/` (keep `database.py`, `logger.py`, `ood_detection.py`, and helpers used by services)
- `models/` → `dl_service/models/` (YOLO/OCR/LSTM artifacts and code; exclude large weights if already in `saved_models/`)
- `saved_models/` → `dl_service/saved_models/` (model weights)
- `static/` + `ui/templates/` if you need the demo UI; otherwise optional
- `requirement/requirements.txt` → consolidate into root `requirements.txt` or a dedicated `dl_service/requirements.txt`
