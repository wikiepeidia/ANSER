# Retail Import Forecasting — Integration Summary

## 1. End-to-End Workflow

1. **Invoice Capture**  
   - User uploads up to three invoice images through the React/Flask shell.  
   - Files are normalized to PNG, tagged with upload metadata, and saved into `/uploads/`.
2. **Invoice Understanding (Model 1 stack)**  
   - **YOLOv8 Invoice Grid Detector** replaces the earlier MobileNetV2 CNN.  
     - Detects product rows, totals grid, and stamp regions.  
     - Outputs bounding boxes plus class labels in `invoice_grid.json`.  
   - **Pebble OCR pipeline**  
     - Crops YOLO regions, applies adaptive thresholding, and runs Pebble OCR (Vietnamese-friendly).  
     - Produces structured product lines `{name, quantity, unit_price, line_total}` with confidence scores.  
   - **Post-processing**  
     - Matches OCR product names against `data/product_catalogs.json`.  
     - Normalizes VND prices, calculates invoice totals, and writes Y1 to `database/invoices.db`.
3. **Time-Series Forecasting (Model 2 stack)**  
   - **ImportForecastLSTM** consumes:  
     - Historical imports `data/import_in_a_timescale.csv` (01/10/2025–01/11/2025).  
     - Historical sales `data/sale_in_a_timescale.csv` (same window).  
     - Structured invoice lines from Model 1 (Y1).  
   - Builds 30-day, 7-feature sequences (`quantity, price, total_amount, num_products, max_product_qty, day_of_week, is_weekend`).  
   - Predicts recommended import quantity plus trend classification for each SKU (Y2).  
   - Persists results and confidence scores to `database/forecasts.db`, exposed via `/api/model2/forecast`.
4. **Presentation Layer**  
   - Frontend renders detected invoice tables, trend badges, total import recommendation, and confidence gauge.  
   - Users can export JSON/CSV for downstream ERP ingestion.

## 2. Application Components

| Layer | Key Files | Notes |
| --- | --- | --- |
| **Frontend** | `templates/index.html`, `static/script.js`, `static/style.css` | Upload UX, OCR tables, forecast triggers. |
| **API** | `api/model1_routes.py`, `api/model2_routes.py`, `api/history_routes.py` | Blueprint separation for detection, forecasting, and audit history. |
| **Services** | `services/model_loader.py`, `services/invoice_service.py`, `services/forecast_service.py` | Model lifecycle, OCR orchestration, feature engineering, LSTM inference. |
| **Models** | `models/cnn_model.py` (legacy), `models/lstm_model.py`, `models/OCR.py` | YOLO weights tracked separately (`saved_models/yolo_invoice.pt`). |
| **Data** | `data/generated_invoices/*`, `data/import_in_a_timescale.csv`, `data/sale_in_a_timescale.csv`, `data/dataset_product.csv` | Synthetic invoices plus historical time-series. |
| **Persistence** | `database/invoices.db`, `database/forecasts.db` | SQLite stores structured invoices and forecasts. |

## 3. Model Details

### Model 1 — YOLOv8 + Pebble OCR

- **Purpose:** Convert messy invoice images into structured line items.  
- **Pipeline:**  
  1. YOLOv8 (fine-tuned on synthetic invoice grids) → bounding boxes for rows, totals, metadata.  
  2. Pebble OCR (Vietnamese language pack) → text extraction per cell.  
  3. Alignment heuristics → map text to `{product_name, qty, unit_price}`.  
- **Outputs:** JSON block (Y1) with per-product data, invoice confidence, and processing time.  
- **Integration hooks:** `/api/model1/detect` returns JSON to the frontend and writes to `database/invoices.db`.

### Model 2 — ImportForecastLSTM

- **Architecture:** Three stacked LSTM layers (128 → 64 → 32 units) with dense head and ReLU output to enforce non-negative predictions.  
- **Features:** `quantity, price, total_amount, num_products, max_product_qty, day_of_week, is_weekend`.  
- **Window:** 30-day lookback, stride 1, sliding per SKU.  
- **Training assets:** `saved_models/lstm_text_recognizer.weights.h5` plus scaler `saved_models/lstm_text_recognizer.weights_scaler.pkl`.  
- **Outputs (Y2):** Recommended import quantity, trend label, textual explanation, per-product confidence.

## 4. Feature Highlights & Differentiators

- **Dual-model brain:** Vision (YOLOv8 + Pebble OCR) plus temporal reasoning (stacked LSTM) gives both immediate digitization and forward-looking recommendations.  
- **Invoice-native UX:** Multi-upload wizard, per-page invoice carousel, and instant JSON/CSV export keep finance teams in flow.  
- **Confidence transparency:** Every stage emits per-line and aggregate confidence so ops can gate low-trust outputs.  
- **Synthetic-first training:** Generator in `data/generated_invoices/` lets the team expand coverage without waiting for sensitive real invoices.  
- **Blueprinted APIs:** `/api/model1`, `/api/model2`, `/api/history` mirror microservice boundaries for easier downstream wiring.  
- **SQLite time travel:** Persisted invoices + forecasts enable replays, audit trails, and “what happened last week?” questions without reprocessing images.  
- **Evaluation suite:** `evaluate_models.py` regenerates training curves and summary text, keeping demo decks honest.

## 5. Inputs & Outputs at a Glance

| Stage | Key Inputs | Primary Outputs |
| --- | --- | --- |
| **Model 1 — YOLOv8 + Pebble OCR** | Invoice images (PNG/JPG → 224×224 RGB), catalog context, preprocessing config | Structured products `{product_name, quantity, unit_price, line_total}`, invoice totals, `confidence`, processing time |
| **Model 2 — ImportForecastLSTM** | 30-day windows from `import_in_a_timescale.csv`, `sale_in_a_timescale.csv`, Y1 products, calendar features | `predicted_import_quantity`, `trend`, textual rationale, SKU-level confidence, portfolio-level recommendation |
| **Frontend/UI** | API JSON payloads, cached invoice history, user actions | Tables, badges, download payloads, manual overrides |

- **Input validation:** Frontend caps uploads at three files, backend enforces MIME checks and window completeness before inference.  
- **Output contracts:** Every response embeds `model_version`, `timestamp`, and trace IDs so the broader platform can reconcile logs.

## 6. Data Assets & Synthetic Generation

- **Historical CSVs:**  
  - `data/import_in_a_timescale.csv` and `data/sale_in_a_timescale.csv` cover 01/10/2025–01/11/2025 with semicolon-separated Vietnamese headers; loaders in `services/forecast_service.py` normalize thousand separators and coerce ints.  
  - `data/dataset_product.csv` injects `initial_stock`, `import_price`, `retail_price` per SKU for feature engineering.  
- **Invoice corpora:** `data/generated_invoices/train|valid|test` (280/80/40 PNGs) plus matching `*_metadata.json` come from `data/generate_invoice.py`, keeping YOLO fine-tuning reproducible without NDAs.  
- **Model artifacts:**  
  - Layout: `saved_models/layout_detector/weights/best.pt` + `training_metrics.json` (mAP50 / mAP50-95) consumed by `services/layout_service`.  
  - Forecast: `saved_models/lstm_text_recognizer.weights.h5` with scaler sidecar `.pkl`; `config.py` enforces lookback/features counts for both training (`train_lstm_model.py`) and inference.  
.  
- **Evaluation tooling:** `evaluate_models.py` (curves + text), `train_cnn_models.py` (YOLO prep despite legacy file name), and README walkthrough ensure anyone can regenerate weights end-to-end.

## 7. API Surface & Frontend Flow

| Method | Path | Handler | Notes |
| --- | --- | --- | --- |
| `POST` | `/api/model1/detect` | `api/model1_routes.py::detect_invoice` | Accepts `image`/`file`, validates via `utils/validators`, runs `process_invoice_image`, saves to DB, returns Y1 + metrics. |
| `POST` | `/api/model2/forecast` | `api/model2_routes.py::forecast` | Takes `products` array (preferred) or `invoice_data` text, lazy-loads LSTM, calls `forecast_quantity`, persists to `forecasts`. |
| `POST` | `/api/ocr/` | `api/ocr_routes.py::ocr_image` | Standalone OCR endpoint (same backend stack) for testing new scans. |
| `GET` | `/api/history` | `history_routes.py::get_history` | Returns recent invoices (DB first, memory fallback). |
| `GET` | `/api/history/database` | `history_routes.py::get_database_history` | Paginated invoices + forecasts direct from SQLite. |
| `POST` | `/api/history/clear` | `history_routes.py::clear_history` | Clears memory, optional `?database=true` purge. |
| `GET` | `/api/statistics` | `history_routes.py::get_stats` | Aggregates counts, sums, averages straight from DB. |
| `GET` | `/api/models/info` | `history_routes.py::models_info` | Surfaces YOLO/LSTM readiness, weights, lookback, history count. |

- **`static/script.js` niceties:** drag/drop uploader with duplicate detection, per-file thumbnails, auto-pagination of recognized invoices, metrics dashboard fed by response payload, and `model2Input` auto-populated from Y1 so users rarely type manual data.  
- **User gestures:** Ctrl+Enter submits Model 2 text box, pagination buttons call `renderInvoicePage`, and `updateRecognizedSummary` keeps batch stats + running invoice counts aligned with backend history size.  
- **Latency guardrails:** Buttons disable while awaiting responses, spinners show progress, and catch blocks push fatal errors to the UI with red messaging.

## 8. Observability, Storage & Safety Nets

- **Logging:** `utils/logger.py` wires console + rotating file handlers (`logs/app.log`, `error.log`, `api.log`); `log_api_request` logs every call with method, status, and duration.  
- **Metrics in-flight:** `services/invoice_service.py` tracks per-invoice layout + OCR precision plus rolling averages (`accuracy_stats`), exposed back to the UI metrics cards; YOLO training metrics are auto-read from `training_metrics.json`.  
- **Persistence:** `utils/database.py` seeds `database/invoices.db` with `invoices` + `forecasts` tables (JSON blobs for products), exposes CRUD + stats helpers; `MAX_INVOICE_HISTORY` (config) caps in-memory cache at 300 to avoid bloating RAM.  
- **Validation & safety:** `utils/validators.py` enforces 16 MB upload cap, extension whitelist, manual invoice syntax, quantity ranges, and store keys; `invoice_service` auto-falls back to layout-mode products and sets default `0.75` confidence if YOLO fails.  
- **Model management:** `services/model_loader.py` initializes YOLO via `layout_service` (auto-detect GPU vs CPU) and LSTM with scaler; lazy getters recover from failure by rebuilding models, printing ASCII-clean warnings.  
- **OCR fallbacks:** `services/ocr_service.py` tries PaddleOCR (GPU/CPU toggled via env), then EasyOCR, then Tesseract—every response tags `backend` + confidence to aid debugging.  
- **History APIs:** `/api/history/database`, `/api/history/clear`, and `/api/statistics` plus SQLite ensure every prediction run is auditable long after the Flask process restarts.

## 9. Giggles, Gotchas & Quick Wins

- **Giggles:** Only true invoices were locked behind NDAs, so we spun up a “Vietnam retail multiverse” with synthetic stamps, scribbles, and weekend spikes—demo friendly and legally clean.  
- **Gotchas:** Confidence currently averages ~75%; without the optional threshold gate, a 30% OCR read can still sneak into LSTM—highlighted in the defense deck for transparency.  
- **Quick wins:** Batch upload endpoint + GPU-backed YOLO service would cut tri-invoice turnaround from ~3.6s to sub-second; adding a 0.7 confidence gate + human-in-loop flag reduces bad auto-orders.  
- **Trivia bite:** Forecast labels (“Steady”, “Increasing”, “Cool-down”) map to trend heuristics inside `services/forecast_service.py`, so PMs can rename them without touching the LSTM weights.

## 10. Deployment & Ops Notes

- **Bootstrap:** `app.py` loads models via `initialize_models()`, registers Flask blueprints, and configures UTF-8 logging.  
- **Model hot-loading:** `services/model_loader.py` caches YOLO, Pebble OCR adapters, and LSTM instances to avoid reload per request.  
- **Dataset maintenance:**  
  - `data/generate invoice.py` refreshes YOLO training data when the catalog grows.  
  - Import/sale CSVs should extend beyond 2025-10/11 for better seasonality.  
- **Monitoring:** `/api/history` exposes processed invoices; `evaluate_models.py` produces training curve PNGs and text reports.

## 11. Integration Guidance for Main Platform

1. **Service boundaries:** Keep detection and forecasting endpoints isolated (`/api/model1`, `/api/model2`) so other microservices can call them independently.  
2. **Event pipeline:** Publish Y1 payloads to a queue/topic after detection so fulfillment, inventory, and BI services can react immediately.  
3. **Model registry:** Store YOLO, Pebble OCR configs, and LSTM weights in a central artifact repository; include `model_version` in responses.  
4. **Confidence policies:** Enforce minimum thresholds before auto-ordering; sub-70% predictions should route to human review.  
5. **Data contracts:** Define protobuf/JSON schemas for Y1 and Y2 so the main platform can consume predictions without touching Flask internals.  
6. **Scaling plan:** Move YOLO + OCR to GPU-backed inference service; keep LSTM on CPU-friendly autoscaling tier.  
7. **Future upgrades:** Plug in real invoices (scanned PDFs), enrich LSTM features with promotion flags/store location/supplier lead time, and explore transformer-based forecasting.

## 12. TL;DR

- **Workflow:** Invoice upload → YOLO grid detection → Pebble OCR → Y1 JSON → LSTM forecasting → Y2 recommendation.  
- **App:** Flask + JS frontend, modular APIs, SQLite persistence, evaluation tooling.  
- **Models:** YOLOv8 (layout detection) + Pebble OCR (text) + stacked LSTM (imports).  
- **Integration outlook:** Ready to plug into the larger retail platform once service boundaries, schemas, and confidence policies are finalized.
