# Project A Backend

Project A is a Python/FastAPI backend for an AI retail assistant. It routes user requests to
specialized agents for consulting, retrieval, automation workflow generation, and image analysis.

## Current Architecture

- API entrypoint: `src/server.py`
- Manager/routing agent: `src/agents/manager.py`
- Workflow generator agent: `src/agents/coder.py`
- Vision/OCR agent: `src/agents/vision.py`
- Memory and DB access: `src/core/memory.py`
- RAG knowledge layer: `src/core/knowledge.py`
- Model runtime config: `src/core/config.py` and `src/core/engine.py`

## Main Endpoints

- `POST /chat`: routes requests by intent and returns assistant response.
- `POST /upload`: analyzes uploaded images with the vision agent.
- `POST /ocr`: extracts OCR text from uploaded images.

## Quick Start

1. Create and activate a virtual environment.
2. Install runtime dependencies:
   - `pip install -r requirements.txt`
3. Set required environment variables:
   - `DATABASE_URL`
4. Optional:
   - `NGROK_AUTHTOKEN` if using `launch_demo.py`
   - `DEEPSEEK_API_KEY` for `src/evaluate_system.py`
5. Run API:
   - `uvicorn src.server:app --host 0.0.0.0 --port 8000`

## Development Quality Gates

- Install developer tooling:
  - `pip install -r requirements-dev.txt`
- Run checks:
  - `ruff check src/core/tools.py src/core/memory.py src/core/context.py tests`
  - `mypy src/core/tools.py src/core/memory.py src/core/context.py`
  - `pytest -q`

CI runs these checks on every push and pull request via `.github/workflows/ci.yml`.
