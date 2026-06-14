# Phase 27: DL Service Logging & OCR Validation - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace runtime `print()` debugging in the DL client/service path with logger calls, confirm OCR detect returns invoice JSON, confirm OCR output can flow into forecast, and keep `dl_service` independently launchable without importing the Flask main app.

</domain>

<decisions>
## Implementation Decisions

### Logging Boundary
- `core/services/dl_client.py` uses `core.logger.get_logger`.
- DL service modules use `dl_service/utils/logger.py` so the DL service remains independent of the Flask main app.
- Runtime service files are in scope; training scripts, sample data generators, and vendored OCR model code are not modified unless they run in normal API startup/request handling.

### OCR/Forecast Validation
- Validate `/api/model1/detect` contract with stubbed heavy ML dependencies because this local environment lacks `cv2`.
- Validate OCR-to-forecast compatibility by accepting nested `invoice_data.products` payloads in both `DLClient` and `/api/model2/forecast`.

### Deployment Shape
- Keep DL as a separate process behind `DL_SERVICE_URL`; `DLClient` remains HTTP-first by default.
- `run_dl_service.py` lazy-loads the DL Flask app only when starting the service, avoiding eager ML imports during launcher import.

### the agent's Discretion
Implementation details are at the agent's discretion as long as runtime logs use `get_logger`, OCR JSON contract tests pass, and the DL startup path does not import the main Flask `app.py`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core.logger.get_logger` provides JSON logging for the main app.
- `dl_service/utils/logger.py` provides service-local logging and API request logging.
- `dl_service/api/model1_routes.py` already formats OCR responses through `format_invoice_response`.

### Established Patterns
- DL service modules import service-local modules via absolute names (`services.*`, `utils.*`) after `dl_service` is added to `sys.path`.
- Route tests can stub heavy ML modules and register blueprints on a minimal Flask app.

### Integration Points
- `core/services/dl_client.py` sends invoice detection to `/api/model1/detect` and forecast to `/api/model2/forecast`.
- `run_dl_service.py` is the local process entry point for the DL Flask app.

</code_context>

<specifics>
## Specific Ideas

Cover TODO Task 3 by testing OCR detect JSON shape, forecast compatibility with OCR output, and launcher independence from main Flask app import.

</specifics>

<deferred>
## Deferred Ideas

Full real-image OCR validation with 3-5 invoice photos remains environment-dependent because this workspace does not include `cv2`/OpenCV runtime dependencies.

</deferred>
