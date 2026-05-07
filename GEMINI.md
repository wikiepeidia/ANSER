# AÁAER  — GEMINI Instructions

> Stack: [e.g., Next.js 14 · TypeScript · PostgreSQL · Prisma · Railway]
> Last updated: [YYYY-MM-DD]

## Project Context

[2–3 sentences: what this product does, who it serves, and the core problem it solves.]

**Tech stack summary**: [Frontend] · [Backend] · [Database] · [Hosting]

---

## Agents Available

**Mandatory delegation — this is not optional.** Every task that falls within a specialist's domain MUST be routed to that agent. Do not implement code, design schemas, write docs, or configure pipelines yourself — delegate. Only handle directly: project-level questions, routing decisions, and tasks explicitly outside all specialist domains.

| Agent | Role | Invoke when... |
|-------|------|----------------|
| `project-manager` | Backlog & coordination | "What's next?", sprint planning, breaking down features, reprioritizing |
| `systems-architect` | Architecture & ADRs | New feature design, tech decisions, system integration |
| `frontend-developer` | UI implementation | Components, pages, client-side state, styling |
| `backend-developer` | API & business logic | Endpoints, auth, background jobs, integrations |
| `ui-ux-designer` | UX & design system | User flows, wireframes, component specs, accessibility |
| `database-expert` | Schema & queries | Migrations, schema design, query optimization |
| `qa-engineer` | Testing (Playwright) | E2E tests, test strategy, coverage gaps |
| `documentation-writer` | Living docs | User guide updates, post-feature documentation |
| `cicd-engineer` | CI/CD & GitHub Actions | Pipelines, deployments, branch protection, release automation |
| `docker-expert` | Containerization | Dockerfiles, docker-compose, image optimization, container networking |
| `copywriter-seo` | Copy & SEO | Landing page copy, marketing content, meta tags, keyword strategy, structured data specs, brand voice |

---

## Critical Rules

These apply to all agents at all times. No exceptions without explicit human instruction.

1. **PRD.md is read-only.** Never modify it. Read it to understand requirements.
2. **TODO.md is the living backlog.** Agents may add items, mark items complete, and move items to "Completed". Preserve section order and existing item priority — do not reorder items within a section unless explicitly asked to reprioritize.
3. **All commits use Conventional Commits format** (see Git Conventions below).
4. **Update the relevant `docs/` file** after every significant change before marking a task complete.
5. **Run tests before marking any implementation task complete.**
6. **Never hardcode secrets, credentials, or environment-specific values** in source code.
7. **Consult `docs/technical/DECISIONS.md`** before proposing changes that may conflict with prior architectural decisions.
8. **Always delegate to the right specialist.** If a task touches frontend, backend, database, UX/design, QA, documentation, CI/CD, Docker, or copy/SEO — invoke the appropriate agent immediately. Do not implement it yourself. The delegation table above is binding, not advisory.

---

## Project Structure

```
src/                    # Application source code
  app/                  # [e.g., Next.js App Router pages]
  components/           # Shared UI components
  lib/                  # Utilities, helpers, shared logic
tests/
  e2e/                  # Playwright E2E tests (*.spec.ts)
docs/
  user/USER_GUIDE.md    # User-facing documentation
  technical/            # Architecture, API, DB, decisions
  content/              # Content strategy, brand voice, keyword targets (owned by @copywriter-seo)
.claude/agents/         # Specialist agent definitions
.claude/templates/      # Blank doc templates (synced from upstream — do not edit)
.tasks/                 # Detailed task files — one per TODO item (owned by @project-manager)
```

---

## Git Conventions

### Commit Format

```
<type>(<scope>): <short description>

[optional body]
[optional footer: Closes #issue]
```

**Types**: `feat` · `fix` · `docs` · `style` · `refactor` · `test` · `chore` · `perf` · `ci`

Examples:

```
feat(auth): add OAuth2 login with Google
fix(api): handle null response from payment provider
docs(user-guide): update onboarding section after flow change
```

### Branch Naming

```
feature/<ticket-id>-short-description
fix/<ticket-id>-short-description
chore/<description>
docs/<description>
refactor/<description>
```

### PR Requirements

- PR title follows Conventional Commits format
- Fill out `.github/PULL_REQUEST_TEMPLATE.md` completely — do not delete sections
- Link to the related issue/ticket (`Closes #XXX`)
- At least one reviewer required before merge
- All CI checks must pass

---

## Code Style

> Fill in when project tooling is set up.

- **Language**: TypeScript (strict mode)
- **Formatter**: [Prettier — config in `.prettierrc`]
- **Linter**: [ESLint — config in `.eslintrc`]
- **Import style**: [absolute imports from `src/`]
- **No `console.log`** in production code — use the project logger utility
- **No commented-out code** committed — delete it or track it in TODO.md

---

## Testing Conventions

> Fill in when test infrastructure is set up.

- **Unit tests**: [Vitest — colocated as `*.test.ts` next to source files]
- **E2E tests**: [Playwright — in `tests/e2e/*.spec.ts`]
- **Run unit**: `[npm test]`
- **Run E2E**: `[npm run test:e2e]`
- **Coverage target**: 80% for new features
- E2E tests use Page Object Model pattern and `data-testid` selectors

---

## Environment & Commands

> Fill in when project is initialized.

- **Node**: [x.x.x] (see `.nvmrc`)
- **Package manager**: [npm / pnpm / yarn]
- `[npm run dev]` — start dev server
- `[npm run build]` — production build
- `[npm test]` — unit tests
- `[npm run test:e2e]` — E2E tests
- `[npm run lint]` — lint check
- `[npm run typecheck]` — TypeScript check

---

## Key Documentation

@docs/technical/ARCHITECTURE.md
@docs/technical/DECISIONS.md
@docs/technical/API.md
@docs/technical/DATABASE.md
@docs/user/USER_GUIDE.md

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Group Project AI/ML - USTH GEN14**

A Flask-based AI/ML web application built as a university group project (USTH GEN14). It provides AI chat, deep learning services (OCR via VietOCR, forecasting via LSTM), drag-and-drop workflows, wallet/subscription billing, and Google OAuth authentication. The team failed the initial jury presentation and is preparing for a retake in 1-2 weeks.

**Core Value:** Demonstrate clean, well-architected AI/ML integration through a working web application with proper separation of concerns — convincing the jury that the engineering and methodology are sound.

### Constraints

- **Timeline**: 1-2 weeks until jury retake presentation
- **Team**: 4+ members, need clear branch separation to avoid conflicts
- **Tech stack**: Flask, SQLite, Python — no framework changes
- **Backwards compatibility**: All existing features must continue working after refactor
- **Jury focus**: Clean architecture + working demo equally important; jury checks report and presentation more than UI
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages

- Python 3.x - Core backend, AI/ML services, workflow automation, model training
- HTML/CSS/JavaScript - Frontend templates in `ui/templates/`
- JSON - Configuration, data serialization, workflow definitions

## Runtime

- Python (version not explicitly specified in lock file)
- Flask WSGI server with Werkzeug
- Node.js (minimal - `package.json` present but minimal dependencies)
- pip (Python packages)
- npm (JavaScript - minimal usage, essentially empty `package.json`)
- No Python lock file detected (requirements.txt used directly)

## Frameworks

- Flask 3.0-3.x - Main web application framework in `app.py`
- FastAPI - Alternative async API framework in `ai_agent_service/` and `package/requirements.txt`
- Uvicorn - ASGI server for FastAPI
- Werkzeug - WSGI utilities, middleware, and request handling
- Flask-Login 0.6+ - User session and authentication management
- Flask-WTF 1.2+ - CSRF protection with CSRFProtect
- Flask-Talisman 1.1+ - Security headers (HSTS, CSP, X-Frame-Options)
- Flask-Limiter 3.5+ - Rate limiting
- authlib 1.x - OAuth2 client integration (`core/google_integration.py`)
- Passlib[bcrypt] - Password hashing with bcrypt algorithm
- torch 2.4.0+ - PyTorch deep learning framework
- transformers 4.46.0+ - Hugging Face transformer models for NLP
- TensorFlow - Deep learning framework for LSTM models
- YOLO (via ultralytics) - Object detection for layout detection and invoice processing
- EasyOCR - Optical character recognition with deep learning
- PaddleOCR 2.6+ - Alternative OCR with PaddlePaddle backend
- PaddlePaddle 2.4.0+ - Core tensor computation for OCR
- pytesseract - Wrapper for Tesseract OCR engine
- timm - PyTorch Image Models for vision transformers
- einops - Einstein summation operations for tensor manipulation
- Florence-2 - Vision language model (components: timm, einops, pillow)
- chromadb - Vector database for RAG (Retrieval-Augmented Generation)
- sentence-transformers - Semantic embedding generation
- sentence-piece - Tokenizer for transformer models
- numpy 1.21.0+ - Numerical computing
- pandas - Data manipulation and analysis
- scikit-learn - Machine learning algorithms for preprocessing and metrics
- opencv-python-headless 4.5.0+ - Image processing (headless for servers)
- Pillow - Python imaging library
- pypdf - PDF document parsing and extraction
- python-docx - Microsoft Word (.docx) document parsing
- pdf2image - PDF to image conversion
- requests - HTTP client for external API calls
- pyngrok - Ngrok tunneling for local development exposure
- nest_asyncio - Async event loop support
- python-multipart - Multipart form data parsing for FastAPI
- SQLAlchemy 2.0+ - SQL ORM for database abstraction in `database/progres.py`
- psycopg2-binary / psycopg[binary] - PostgreSQL adapter for Python
- psycopg - Modern async-capable PostgreSQL driver (alternative)
- alembic - Database migration tool
- sqlite3 (built-in) - Fallback local database via Config.USE_POSTGRES switch
- json_repair - JSON malformed data recovery in `core/integrations.py`
- duckduckgo-search - Search engine API
- lunardate - Lunar calendar calculations
- pytz - Timezone handling
- python-dotenv - Environment variable loading (referenced in requirements)
- google-auth-oauthlib - Google OAuth2 authentication flow
- google-auth-httplib2 - Google API auth transport
- google-api-python-client - Google API client library
- google-analytics-data - Google Analytics Data API v1beta (BetaAnalyticsDataClient)
- addict / easydict - Attribute-accessible dictionaries
- accelerate 1.0.0+ - Distributed training utilities
- bitsandbytes 0.44.1+ - Quantization and low-bit operations
- protobuf - Protocol buffer serialization (required by transformers)

## Configuration

- Configuration via environment variables in `core/config.py`:
- Secrets from JSON files in `secrets/` directory:
- No explicit build configuration detected (Flask runs directly via `app.py`)
- Deep learning service runs via `dl_service/model_app.py` on separate port
- AI agent service runs via `ai_agent_service/server.py` or `main.py`
- Flask templates in `ui/templates/` directory (referenced in `app.py` line 37)

## Platform Requirements

- Python 3.x with pip
- Git for version control
- System libraries:
- Linux server (Ubuntu/Debian recommended for compatibility)
- Python 3.x runtime
- PostgreSQL database (Neon/Railway for cloud, local PostgreSQL for self-hosted)
- Reverse proxy: Nginx or similar (app.py uses ProxyFix middleware)
- Process manager: Gunicorn, uWSGI, or similar WSGI server
- GPU support optional (for accelerated inference)
- Railway or similar cloud platform (hints in recent commits reference Docker compose removal)
- Docker containerization (docker-compose.yml previously present, now deleted)
- Web: Flask/Uvicorn on port 5000 (main app), port 5001 (DL service)

## Key Characteristics

- **Multi-service architecture**: Main Flask app (`app.py`), separate deep learning service (`dl_service/`), separate AI agent service (`ai_agent_service/`)
- **Database flexibility**: Configurable SQLite or PostgreSQL backend via Config
- **OAuth2 integration**: Google authentication with scopes for Drive, Sheets, Gmail, Analytics
- **Computer vision pipeline**: YOLO + OCR + PaddleOCR for invoice/document processing
- **Vector search**: ChromaDB for semantic search and RAG
- **AI agents**: Multi-agent system with memory, knowledge, and tool execution
- **Automation**: Workflow engine for retail/supply chain automation
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Language Patterns

## Naming Patterns

- snake_case for Python files: `base.py`, `engine.py`, `memory.py`
- Lowercase with underscores for modules: `agent_middleware.py`, `invoke_training_data.py`
- API routes use underscores: `model1_routes.py`, `ocr_routes.py`
- Blueprint/service files follow pattern: `invoice_service.py`, `forecast_service.py`
- snake_case: `clean_output()`, `extract_json_block()`, `analyze_task()`
- Private methods prefixed with underscore: `_initialize()`, `_get_active_session()`, `_get_workflow_tools()`
- Description-based naming: `process_invoice_image()`, `validate_image_file()`, `save_invoice_to_db()`
- snake_case for regular variables: `user_input`, `model_engine`, `vision_context`
- Uppercase for constants and config values: `PROJECT_ROOT`, `DATA_DIR`, `SYSTEM_CONTEXT`, `ALLOWED_EXTENSIONS`, `UPLOAD_DIR`
- Environment variables uppercase: `DATABASE_URL`, `HF_BASE_URL`, `HF_TOKEN`, `SECRET_KEY`
- Single letter variables acceptable for iterations: `i`, `m` (in loops)
- PascalCase: `BaseAgent`, `ModelEngine`, `MemoryManager`, `ManagerAgent`, `VisionAgent`, `CoderAgent`
- Service classes: `DLClient`, `AutomationEngine`, `Database`, `Config`
- Blueprint objects lowercase with `_bp` suffix: `model1_bp`, `ocr_routes`
- Not extensively used (older codebase patterns)
- When present, follow Python standard: `def analyze_task(self, clean_text: str):`

## Code Style

- No explicit formatter detected (no .prettierrc, .eslintrc, or setup.cfg)
- Observed style: 4-space indentation (Python standard)
- Line breaks between methods and logical sections
- Comments use `#` (Python standard)
- docstrings use triple quotes: `"""Test & Evaluate OOD Detection..."""`
- Absolute imports from `src.` prefix used: `from src.core.engine import ModelEngine`
- Root-relative imports in some legacy code: `from core.config import Config`
- No explicit path alias configuration file detected

## Error Handling

- Uses custom logger: `logger = get_logger(__name__)` (from `utils.logger`)
- Format: `logger.info()`, `logger.warning()`, `logger.error()`
- Print statements in main/CLI code: `print(f"❌ Error: {e}")`
- Emoji prefixes in user-facing output: `❌`, `✅`, `⚠️`, `👁️`
- Avoid bare `except:` clauses (some exist in legacy code — avoid replicating)
- Always log or print errors, never silently fail
- Use specific exception types when possible

## Logging

- Status messages: `print("✅ Ready.")`
- Errors: `print(f"❌ Error: {e}")`
- Progress: `print("    [Vision] Analyzing...")`
- Section headers: `print("=" * 70)`
- Use f-strings for formatting: `f"Processing {file.filename}"`
- Include timestamps where needed (database updates do CURRENT_TIMESTAMP)
- Log request duration: `duration = (time.time() - start_time) * 1000`

## Comments

- Complex algorithms or non-obvious logic
- Workarounds and fixes: `# FIX: attn_implementation="eager" fixes the _supports_sdpa crash on newer transformers`
- Section headers in long functions: `# --- 0. VISION CHECK ---`
- Configuration explanations: `# Give 50% (40GB) to the 32B model`
- Used for function/class documentation (not consistently)
- Format: triple-quoted strings at top of function
- Not applicable (Python-first codebase)
- No commented-out code should be committed (common pattern: deletion)
- Avoid TODO comments in production code (track in TODO.md instead)

## Function Design

- Range: 10–50 lines typical
- Simple utilities: 5–15 lines
- Complex logic (agents): 30–60 lines acceptable
- Longer functions (100+ lines) found in test suites (intentional)
- 3–5 parameters typical
- Use kwargs for optional parameters: `def generate(self, prompt: str, **kwargs):`
- Dataclass/Pydantic models for multiple parameters
- Single value typical: `return text.strip()`
- Tuple returns for status + data: `status, data = resolver.resolve_login(CURRENT_USER_ID)`
- Dictionary returns for complex results: `return {"category": "TECHNICAL"}`
- Always return something meaningful; avoid silent None returns

## Module Design

- Typically one main class per module
- Example: `base.py` exports `BaseAgent`, `engine.py` exports `ModelEngine`
- Services may have multiple functions: `utils/logger.py` exports `get_logger()`, `log_api_request()`
- Minimal usage (no `__init__.py` with re-exports observed)
- Blueprint registration done in main app: `from api.model1_routes import model1_bp`
- Used for `ModelEngine`: `_instance` class variable with `__new__` override
- Constructor injection common: `def __init__(self, engine: ModelEngine, memory: MemoryManager):`
- Agents receive engine and memory: `manager = ManagerAgent(engine, memory, kb=kb)`
- Agent modules tightly focused: `CoderAgent` handles code generation only
- Service modules: `invoice_service.py` handles invoice processing pipeline
- Utilities isolated: `utils/validators.py`, `utils/logger.py`, `utils/database.py`

## String Formatting

- % formatting (old style)
- Concatenation with `+`

## Configuration Management

- Centralized in `Config` class: `src/core/config.py`, `dl_service/config.py`
- Environment variable loading: `os.getenv("DATABASE_URL", "default_value")`
- URL transformation for database compatibility:
- Constants as class attributes (not dict):
- API keys loaded from env vars: `token = config.get('HF_TOKEN')`
- Secrets in files listed but not accessed: `secrets/google_oauth.json` loaded conditionally
- Feature flags via env: `USE_POSTGRES = getattr(Config, 'USE_POSTGRES', False)`

## Multi-line Strings

## Code Organization by Feature

- Base class: `agents/base.py` - defines interface
- Concrete agents: `agents/manager.py`, `agents/coder.py`, `agents/vision.py`
- Engine shared: `core/engine.py` - passed to agents
- Memory shared: `core/memory.py` - passed to agents
- Blueprint setup: `api/model1_routes.py`
- Service logic: `services/invoice_service.py`
- Utilities: `utils/validators.py`, `utils/database.py`
- Main app: `app.py` or `server.py` registers blueprints

## Common Antipatterns (Avoid)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview

- A main Flask monolith (`app.py`) serving as the web application and orchestration layer
- A separate Deep Learning microservice (`dl_service/model_app.py`) running independently on port 5001
- An AI Agent service (`ai_agent_service/`) that provides autonomous agent capabilities
- Workflow engine for connecting multiple services and automating business processes
- Python-based Flask web application (main entry point)
- Asynchronous job processing with in-memory job store for AI tasks
- Multi-service architecture with HTTP-based communication between services
- Supports both local execution (direct Python imports) and remote HTTP calls
- OAuth2 integration with Google for authentication and API access
- Templated HTML UI with server-side rendering
- Workflow engine for orchestrating multi-step data processing pipelines

## Layers

- Purpose: Serve web UI with server-side rendered templates, handle user sessions, manage authentication
- Location: `ui/templates/` (HTML templates), `app.py` (Flask application setup)
- Contains: Jinja2 templates for admin dashboard, user management, product/customer views, analytics
- Depends on: Authentication layer, database layer, core services
- Used by: Web browsers, API clients (authenticated)
- Purpose: Handle HTTP requests and responses, route requests to appropriate handlers
- Location: Routes defined inline in `app.py` using Flask blueprints (imported but executed in main app)
- Contains: Route handlers for authentication, user management, dashboard, workflows, integrations
- Depends on: Core services, database, authentication managers
- Used by: Frontend templates, external API clients
- Purpose: Implement domain-specific logic - authentication, data processing, workflow execution, analytics
- Location: `core/` directory
- Contains:
- Depends on: Database, external APIs (Google, Make.com webhooks)
- Used by: API layer, workflows
- Purpose: Persistent data storage and retrieval
- Location: `database/` directory with schema and utilities
- Contains:
- Depends on: None
- Used by: All service layers
- Purpose: Computer vision and NLP model inference for document processing
- Location: `dl_service/` directory
- Contains:
- Depends on: TensorFlow, OpenCV, PyTorch
- Used by: Main application via `DLClient`, direct HTTP calls to port 5001
- Purpose: Provide autonomous agent capabilities for complex task automation
- Location: `ai_agent_service/` directory
- Contains:
- Depends on: LLM libraries, tools, data schemas
- Used by: Main application for complex automation workflows
- Purpose: Shared utilities and helpers
- Location: `core/utils.py`, `dl_service/utils/`, error handlers throughout
- Contains: Helper functions for datetime handling, error formatting, data validation
- Depends on: None
- Used by: All layers

## Data Flow

## Key Abstractions

- Purpose: Unified interface for SQLite and PostgreSQL databases
- Examples: `core/database.py` with `Database` class
- Pattern: Cursor-based interface with compatibility shims for different DB engines
- Handles: Connection pooling, schema introspection, query parameter conversion
- Purpose: Abstract away the complexity of calling the DL service
- Examples: `core/services/dl_client.py`
- Pattern: Supports both local execution (direct imports) and remote HTTP calls
- Handles: Request/response serialization, error handling, timeout management
- Purpose: Execute complex multi-step workflows as DAGs (Directed Acyclic Graphs)
- Examples: `core/workflow_engine.py` with `execute_workflow()` function
- Pattern: Topological sort → node iteration → context passing
- Handles: Template variable resolution, node type dispatch, error propagation
- Purpose: Centralized authentication logic
- Examples: `core/auth.py` with `AuthManager` class
- Pattern: Database-backed user credentials, password hashing, session management
- Handles: User registration, login verification, password reset
- Purpose: Encapsulate all Google API interactions
- Examples: `core/google_integration.py`
- Pattern: Functions for each operation (read_sheet, write_doc, send_email, etc.)
- Handles: Token management, API error handling, scope management

## Entry Points

- Location: `app.py`
- Triggers: `python app.py` or `flask run`
- Responsibilities:
- Location: `dl_service/model_app.py` (executed via `run_dl_service.py`)
- Triggers: `python run_dl_service.py`
- Responsibilities:
- Location: `ai_agent_service/main.py` or `ai_agent_service/server.py`
- Triggers: `python ai_agent_service/main.py`
- Responsibilities:

## Error Handling

- Database errors: Log, return 500 with generic message to client
- Validation errors: Return 400 with specific field/issue
- Authentication errors: Return 401 with redirect to login
- DL service unavailable: Fallback to alternate implementation or queue for retry
- OAuth errors: Log, return error message with retry option
- Workflow execution errors: Capture error in execution context, allow partial results
- `app.py` routes wrap business logic in try-except
- `core/database.py` connection errors logged with traceback
- `core/services/dl_client.py` catches `RequestException` and returns error dict
- OAuth callback checks for error parameter from Google

## Cross-Cutting Concerns

- Console output via print() statements (not production-ready)
- File logging to `api_log.txt` in `ai_agent_service/`
- Structured logging for errors with context
- Database schema validation in `Database.init_database()`
- User input validation in route handlers (form data, JSON)
- File type/size validation for uploads
- Workflow template validation before execution
- Session-based via Flask-Login for web UI
- Google OAuth for third-party integration
- API calls require valid session or Google token
- Role-based access control (admin, manager, user roles)
- Flask-Limiter configured with per-day and per-hour limits
- Disabled in development mode (`RATELIMIT_ENABLED=False`)
- Can be customized per-endpoint
- Flask-WTF CSRF protection enabled
- CSRF tokens generated and validated on forms and API calls
- Talisman CSP policy configured (permissive for development)
- Talisman middleware applies security headers
- HSTS enabled
- Frame options set to DENY
- Content-Type sniffing prevented
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
