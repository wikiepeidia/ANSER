---
phase: 27-dl-service-logging-ocr-validation
plan: "01"
subsystem: dl-service
tags:
  - logging
  - ocr
  - forecast
  - service-isolation
requires:
  - phase: 25-circular-import-module-decoupling
    provides: HTTP-first DLClient and clean main app imports
provides:
  - runtime DL logging through get_logger
  - OCR detect and OCR-to-forecast contract coverage
  - lazy DL service launcher import
affects:
  - Phase 28 Code Hygiene
tech-stack:
  added: []
  patterns:
    - Stubbed route contract tests for heavy ML dependencies
    - OCR payload normalization before forecasting
key-files:
  created:
    - tests/test_dl_service_contracts.py
  modified:
    - core/services/dl_client.py
    - run_dl_service.py
    - dl_service/model_app.py
    - dl_service/api/model2_routes.py
    - dl_service/services/invoice_service.py
    - dl_service/services/ocr_service.py
    - dl_service/services/model_loader.py
    - dl_service/services/cpt_ocr.py
    - dl_service/utils/invoice_processor.py
    - dl_service/models/lstm_model.py
key-decisions:
  - "Keep DL as a separate process behind DL_SERVICE_URL; do not re-couple it to the Flask main app."
  - "Use service-local logging inside dl_service and core.logger in core/ launcher code."
  - "Normalize OCR output for forecast by promoting nested invoice_data.products to top-level products."
requirements-completed:
  - DL-01
  - DL-02
  - DL-03
duration: "~12 min"
completed: 2026-06-14
---

# Phase 27 Plan 01: DL Service Logging & OCR Validation Summary

**DL runtime logs now flow through loggers, OCR JSON contracts are tested, and OCR output can feed forecast requests.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-14T10:31:10Z
- **Completed:** 2026-06-14T10:39:32Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Replaced scoped runtime `print()` calls in `core/services/dl_client.py`, `run_dl_service.py`, DL service startup, OCR, invoice, model-loader, and first-party LSTM runtime code.
- Added payload normalization so OCR outputs with nested `invoice_data.products` can be sent directly into forecast.
- Added `tests/test_dl_service_contracts.py` with three fast contract tests covering OCR detect response shape, OCR-to-forecast payload compatibility, and DLClient normalization.
- Made `run_dl_service.py` lazy-load the DL Flask app through `create_dl_app()` so importing the launcher does not pull in the ML stack.

## Task Commits

1. **Task 1-2: runtime logging, OCR/forecast compatibility, and contract tests** - `2183cb1` (fix)

**Plan metadata:** this summary and Phase 27 verification artifacts.

## Files Created/Modified

- `tests/test_dl_service_contracts.py` - Stubbed Flask blueprint contract tests for heavy ML boundaries.
- `core/services/dl_client.py` - Logger usage plus OCR forecast payload normalization.
- `dl_service/api/model2_routes.py` - Accepts nested OCR invoice products.
- `run_dl_service.py` - Lazy app creation and logger usage.
- `dl_service/model_app.py`, `dl_service/services/*`, `dl_service/utils/invoice_processor.py`, `dl_service/models/lstm_model.py` - Runtime prints converted to logger calls.

## Decisions Made

- Real image OCR with 3-5 invoice photos is environment-dependent and requires OpenCV/model dependencies not installed here. The automated coverage verifies the HTTP contract with stubs instead.
- DL remains a separate process; no main Flask `app.py` import is introduced.

## Deviations from Plan

The TODO requested real invoice-image OCR validation. This workspace lacks `cv2`, so route contract tests stubbed image decoding and model execution. This verifies API wiring and JSON shape, but not real model accuracy.

---

**Total deviations:** 1 environment-driven verification adaptation.
**Impact on plan:** Runtime behavior and contracts are covered; real-model OCR accuracy still depends on a fully provisioned DL environment.

## Issues Encountered

- `cv2` is not installed in the current environment, so full `python run_dl_service.py` server launch was not attempted. Launcher import and main-app independence were verified.

## User Setup Required

None for code changes. Real OCR validation requires installing the DL runtime dependencies, including OpenCV and model dependencies.

## Next Phase Readiness

Phase 28 can proceed. TODO Task 3 is covered for runtime logging, OCR response contract, OCR-to-forecast compatibility, and independent launcher wiring.

## Self-Check: PASSED

- Scoped runtime print scan returns no matches.
- Compile check passed for all modified Python files.
- `python -m pytest tests/test_dl_service_contracts.py -v` reports 3 passed.
- `python -c "import run_dl_service; print('run_dl_service import ok')"` exits 0.
- Strict main-app import scan returns no matches.

---
*Phase: 27-dl-service-logging-ocr-validation*
*Completed: 2026-06-14*
