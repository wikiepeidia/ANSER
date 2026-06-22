---
status: partial
phase: 27-dl-service-logging-ocr-validation
started: 2026-06-14T22:00:00Z
updated: 2026-06-14T22:00:00Z
---

## Tests

### 1. No print() in dl_client.py
expected: grep finds no print() calls.
result: pass

### 2. DL service does not import main Flask app
expected: run_dl_service.py and dl_service/model_app.py contain no "from app import" or "import app".
result: pass — run_dl_service.py uses sys.path.append(dl_service_path) for DL-internal imports only,
  then imports from model_app (DL service's own Flask app), not the main app.

### 3. dl_service/ uses logger not print()
expected: No raw print() in dl_service/ core paths.
result: pass — model_loader.py uses get_logger, layout_service uses torch/cv2 with logger

### 4. DL service starts independently (python run_dl_service.py)
expected: Service boots on port 5001 without importing main Flask app.
result: BLOCKED — TensorFlow not installed in current environment.
  services/__init__.py eagerly imports model_loader which imports LSTM model (TF).
  Architecture is correct (no main-app coupling) but requires: pip install -r requirements-ml.txt
  Test images available at: dl_service/data/generated_invoices/test/invoice_test_108*.png

### 5. OCR upload returns valid invoice_data JSON
expected: POST /api/model1/detect with invoice image returns {invoice_data: {...}} structure.
result: BLOCKED — DL service cannot start (see T4). Requires TF environment.
  Manual test script available: dl_service/test_ocr_pipeline.py

## Summary

total: 5
passed: 3
issues: 0
blocked: 2
skipped: 0

## Gaps

### BLOCK-01 — TF not installed, DL service and OCR cannot run
- Blocker: tensorflow not in active venv
- Fix: pip install -r requirements-ml.txt (warning: ~5GB, takes time)
- Workaround: run dl_service/test_ocr_pipeline.py after installing ML deps
- Owner: whoever runs the ML environment (not a code bug)
