# ANSER

> A solution to Retail Stores.

## Quick steps

- `python app.py` to start the main management service.
- `python ai_agent_service/main.py` for the agent server (Qwen + vision).
- `python dl_service/model_app.py` to launch the deep learning service (OCR, forecasting).
- `docker-compose up db` if you need the PostgreSQL container described in `core/config.py`.

## Useful folders

- `core/` : shared helpers (auth, config, workflow engine).
- `dl_service/` : DL REST APIs (OCR chain, LSTM forecasting, saved models).
- `ai_agent_service/` : the autonomous agent glue (Qwen chat + VisionAgent).
- `DOCUMENTS/reports/` : final paper + presentation; nothing in the README beats that.
- `test/` : sanity checks (OCR chain, LSTM forecast) that can be run manually.
