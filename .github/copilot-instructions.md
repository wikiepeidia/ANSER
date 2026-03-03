# Project Guidelines
> Main part: Deal with Q&A Juries.
## Report files 
- **Location**: Generated reports are saved in the `DOCUMENTS/reports` directory.
- Project mostly been completed and focus on Presentation, Defense q&A. If we found bug we will fix it and update the codebase, but we will not add new features.
- the main report is DOCUMENTS\reports\THE_FINAL_REPORT.md and this is sent already to the reviewer, so it is NOT possible to change anything here as it is fixed.

## Presentation
- presentation files are located on DOCUMENTS\reports\presentation 
- It consisting of files: 
DOCUMENTS\reports\presentation\q&a\emergency file traveller.md : Emergency file traveller to reduce time navigating when teacher ask like "Show me where you did the OCR part?" or "Show me where you did the workflow execution part?"... 
DOCUMENTS\reports\presentation\main.tex : prsentation, completed and ready to show Juries
DOCUMENTS\reports\presentation\q&a\report q&a.md : Q&A for Report, teachers tended to ask all kinds of question on report.
DOCUMENTS\reports\presentation\q&a\diagram q&a.md : Q&A for diagram, teachers may ask about the architecture diagram, how the components interact, and design choices.

DOCUMENTS\reports\presentation\THE_FINAL_REPORT.md The report itself, quite bad in term of formatting but it is the one we sent to the teacher, so we have to stick with it. who cares 

## WARNINGS
- *Reviewer* in presentation: will heavily want to test the the Workflow sections, besure all node run OK, especilly the OCR, LTSM nodes
- Q&A: be ready to explain the architecture, design choices, and how to run the project.Focus on Report, we  have to explain everything in it including Method, Approaches,and so on.  Focus on the integration points and how the components interact, things such as Preprocessing data,ALGORITHMS (Kahn algorithm for workflow execution,etc 

## Code Style
- **Languages**: Python (primary), HTML/CSS/JS (UI).
- **Formatting**:
  - Python: 4 spaces indentation. Follow PEP 8 generally.
  - See [app.py](app.py) and [core/database.py](core/database.py) for examples.
  - No strict linter config exists; rely on standard IDE formatting.
- **Encoding**: Ensure UTF-8 encoding is used, especially for Windows compatibility (see [dl_service/model_app.py](dl_service/model_app.py#L12-L16)).
- **Docstrings**: Use docstrings for utility functions and classes.

## Architecture 
- **Components**:
  - **Management System**: [app.py](app.py) is the main entry point, a Flask app handling UI, Auth, and Google Integration. (Templates in [ui/templates/](ui/templates/)).
  - **AI Agent Service**: [ai_agent_service/](ai_agent_service/) contains the autonomous agent logic (Qwen model, RAG).
  - **DL Service**: [dl_service/](dl_service/) is a separate Flask microservice for Deep Learning tasks (OCR, LSTM forecasting).
- **Database**: 
  - Dual support for SQLite and PostgreSQL.
  - Abstraction layer in [core/database.py](core/database.py) using `PGShimCursor`.
  - Configured in [core/config.py](core/config.py).
  - PostgreSQL container defined in [docker-compose.yml](docker-compose.yml).
- **Frontend**:
  - Server-side rendered **Flask** + **Jinja2**.
  - Templates located in `ui/templates/`.
  - No separate frontend build step (no React/Vue/npm).

## Build and Test
- **Run**:
  - Main App: `python app.py`
  - AI Agent: `python ai_agent_service/main.py`
  - DL Service: `python dl_service/model_app.py`
  - Database: `docker-compose up db`
- **Dependencies**:
  - Root (Main App): No `requirements.txt` in root (check imports in [app.py](app.py)).
  - AI Agent: [ai_agent_service/requirements.txt](ai_agent_service/requirements.txt)
  - Common Libs: `flask`, `requests`, `pandas`, `numpy`, `torch`.
- **Tests**: 
  - Tests are standalone scripts in the [test/](test/) directory.
  - Run manually: `python test/test_ai_service.py` or `python test/test_db_connection.py`.
  - No `pytest` runner is currently configured.

## Project Conventions
- **Core Logic**: Shared utilities and business logic reside in `core/` (e.g., [core/auth.py](core/auth.py), [core/workflow_engine.py](core/workflow_engine.py)).
- **Secrets**: Store secrets in `secrets/` (e.g., `google_oauth.json`, `database.json`). Do not commit these.
- **AI Models**: 
  - **LLM**: 8-bit quantized models (Qwen) used in `ai_agent_service` (requires `bitsandbytes`, `accelerate`).
  - **DL**: TensorFlow/Keras & Scikit-learn used in `dl_service` (e.g., LSTM for forecasting).

## Integration Points
- **Google**: [core/google_integration.py](core/google_integration.py) handles Drive, Sheets, Gmail, and Analytics APIs.
- **Make.com**: [core/make_integration.py](core/make_integration.py) provides utilities (`trigger_webhook`) to trigger external automation scenarios via HTTP POST/GET.
- **Deep Learning**: The main app consumes `dl_service` APIs (defined in [dl_service/model_app.py](dl_service/model_app.py)).

## Security
- **Authentication**: Managed by [core/auth.py](core/auth.py) (Local & Google OAuth).
- **Secrets**: Loaded from JSON files in `secrets/` or environment variables (see [core/config.py](core/config.py)).

