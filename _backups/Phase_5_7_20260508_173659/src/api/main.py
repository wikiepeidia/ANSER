"""
src/api/main.py — Application factory.
Assembles FastAPI app with lifespan, middleware, and route modules.
This replaces the monolithic src/server.py.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.dependencies import runtime, RUNTIME_PROFILE

logger = logging.getLogger("projecta.api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — nothing to do (lazy init)
    yield
    # Shutdown — close the shared HTTP client pool
    from src.core.utils import HttpClientPool
    await HttpClientPool.close()


# ---------------------------------------------------------------------------
# App Assembly
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Token", "X-User-Id", "X-Store-Id"],
)


# Middleware: attach request ID
@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", os.urandom(8).hex())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Health endpoint (stays here — it's app-level, not domain-specific)
@app.get("/health")
async def health():
    return JSONResponse(
        {
            "status": "ok",
            "runtime_profile": RUNTIME_PROFILE,
            "degraded": bool(runtime.engine_error or runtime.kb_error or runtime.vision_error),
            "engine_ready": runtime.engine is not None,
            "kb_ready": runtime.kb is not None,
            "vision_ready": runtime.vision is not None,
            "engine_error": runtime.engine_error,
            "kb_error": runtime.kb_error,
            "vision_error": runtime.vision_error,
        }
    )


# Register routers
from src.api.routes.chat import router as chat_router
from src.api.routes.documents import router as documents_router

app.include_router(chat_router)
app.include_router(documents_router)
