# Retail Import Forecasting — Integration Cheat Sheet

## Flow (what happens)

1) Upload up to 3 invoice images → saved under `/uploads/`.
2) Model 1 = YOLOv8 layout + OCR: detect header/table/totals, crop, run OCR, build structured products `{product_name, quantity, unit_price, line_total}`, compute totals/confidence, store Y1 in `database/invoices.db`.
3) Model 2 = ImportForecastLSTM: pull historical imports/sales + Y1 products, build sliding windows, predict import qty + trend per SKU, store Y2 in `database/forecasts.db`.
4) UI shows products, metrics, trends; export JSON/CSV if needed.

## Files to know

- Frontend: `ui/templates/index.html`, `static/script.js`, `static/style.css`.
- APIs: `api/model1_routes.py`, `api/model2_routes.py`, `api/history_routes.py` (+ `api/ocr_routes.py`).
- Services: `services/invoice_service.py` (layout+OCR orchestration), `services/forecast_service.py` (features + LSTM), `services/model_loader.py`, `services/layout_service.py`, `services/ocr_service.py`.
- Models/weights: YOLO weights `saved_models/layout_detector/weights/best.pt` + `training_metrics.json`; LSTM `saved_models/lstm_text_recognizer.weights.h5` + scaler `.pkl`.
- Data: synthetic invoices `data/generated_invoices/*` (+ metadata), catalog `data/product_catalogs.json`, historical CSVs `data/import_in_a_timescale.csv`, `data/sale_in_a_timescale.csv`, `data/dataset_product.csv`.
- Persistence: `database/invoices.db`, `database/forecasts.db` (SQLite).

## Endpoints (contracts in plain English)

- `POST /api/model1/detect`: form-data `image`/`file` (PNG/JPG/PDF). Runs layout+OCR, returns Y1 JSON with products, totals, confidence, and metrics payload (layout confidence, OCR precision, rolling averages, YOLO mAP). Saves invoice to DB.
- `POST /api/model2/forecast`: preferred `products` array from Y1; accepts text fallback. Returns per-SKU predicted import quantity, trend label, confidence, rationale; persists to forecasts DB.
- `POST /api/ocr/`: OCR-only smoke test.
- `GET /api/history`: recent invoices (DB first, memory fallback). `GET /api/history/database`: paginated invoices/forecasts from SQLite. `POST /api/history/clear`: purge memory/DB (opt-in). `GET /api/statistics`: aggregate counts/sums. `GET /api/models/info`: readiness + weights paths + history count.

## Model specifics

- Layout/OCR: YOLOv8 (fine-tuned) → best box per class (header/table/totals) → crops → OCR (Paddle preferred; EasyOCR, Tesseract fallback). Heuristics align to products and VND totals.
- Forecast: 3-layer LSTM (128→64→32, ReLU head). Uses sliding windows over historical imports/sales + calendar features. Output is non-negative import quantity + trend tag.

## Metrics & observability

- Per-invoice + rolling averages tracked in `services/invoice_service.py` (layout confidence, OCR precision). YOLO training mAP loaded from `saved_models/layout_detector/training_metrics.json`. UI metrics panel is driven by the `metrics` payload from `/api/model1/detect`.
- Logging via `utils/logger.py` (app/api/error). Upload validation via `utils/validators.py` (size, extension, ranges). In-memory history capped by `MAX_INVOICE_HISTORY`.

## Run/deploy quickstart

1) Train layout (YOLO): `python train_cnn_models.py` (prepares dataset, trains, copies best.pt, writes training_metrics.json).
2) Train LSTM: `python train_lstm_model.py`.
3) Serve: `python app.py` → <http://localhost:5000>.
4) Upload invoices, confirm products + metrics panel; send products to Model 2 for forecasts.

## Integration guidance

- Keep `/api/model1` and `/api/model2` separate; publish Y1 events for downstream consumers.
- Store weights/artifacts in your registry; include `model_version`/`timestamp` in responses (already documented pattern).
- Apply confidence gates (e.g., <0.7 route to human review) before auto-ordering.
- Define JSON/protobuf schemas for Y1/Y2 when wiring to the main platform.

## Known quirks / quick wins

- Confidence averages ~75%; without a gate, low OCR reads can leak into LSTM.
- GPU-backed YOLO + batch upload would cut tri-invoice latency; add a 0.7 gate + human-in-loop flag to reduce bad orders.
