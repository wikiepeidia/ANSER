"""
Shared dependencies for all API routes.
Contains RuntimeState, auth helpers, and text utilities.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("projecta.api")

API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "").strip()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
RUNTIME_PROFILE = os.getenv("RUNTIME_PROFILE", "full").strip().lower()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: int
    store_id: int
    message: str


# ---------------------------------------------------------------------------
# Concurrency Guards
# ---------------------------------------------------------------------------

# Prevents TOCTOU race when multiple concurrent requests trigger
# model loading simultaneously.  The lock is reentrant-safe: if
# _initialize completes (or raises), the lock is always released.
_model_load_lock = asyncio.Lock()
_vision_load_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Runtime State (lazy-loaded singletons)
# ---------------------------------------------------------------------------

@dataclass
class RuntimeState:
    memory: Optional[object] = None
    engine: Optional[object] = None
    kb: Optional[object] = None
    manager: Optional[object] = None
    coder: Optional[object] = None
    vision: Optional[object] = None
    engine_error: Optional[str] = None
    kb_error: Optional[str] = None
    vision_error: Optional[str] = None

    async def ensure_text_runtime(self) -> None:
        """Async, lock-guarded model initialization."""
        # Fast path: already loaded — no lock needed
        if self.manager and self.coder and self.memory:
            return

        async with _model_load_lock:
            # Double-check after acquiring lock (another coroutine may have finished)
            if self.manager and self.coder and self.memory:
                return

            if not self.memory:
                from src.core.memory import MemoryManager
                self.memory = MemoryManager()

            if RUNTIME_PROFILE == "minimal":
                self.engine_error = "Text runtime disabled by RUNTIME_PROFILE=minimal"
                return

            try:
                from src.core.engine import ModelEngine
                self.engine = self.engine or ModelEngine()
            except Exception as exc:
                self.engine = None
                self.engine_error = str(exc)
                logger.error("Engine initialization failed: %s", exc)

            try:
                if not self.kb:
                    from src.core.knowledge import KnowledgeBase
                    self.kb = KnowledgeBase()
            except Exception as exc:
                self.kb = None
                self.kb_error = str(exc)
                logger.warning("Knowledge base initialization failed: %s", exc)

            if self.engine:
                from src.agents.coder import CoderAgent
                from src.agents.manager import ManagerAgent
                self.manager = self.manager or ManagerAgent(self.engine, self.memory, kb=self.kb)
                self.coder = self.coder or CoderAgent(self.engine, self.memory)

    async def ensure_vision_runtime(self) -> None:
        """Async, lock-guarded vision model initialization."""
        if self.vision:
            return

        async with _vision_load_lock:
            if self.vision:
                return
            if RUNTIME_PROFILE == "text-only":
                self.vision_error = "Vision runtime disabled by RUNTIME_PROFILE=text-only"
                return
            try:
                from src.agents.vision import VisionAgent
                self.vision = VisionAgent()
            except Exception as exc:
                self.vision = None
                self.vision_error = str(exc)
                logger.error("Vision initialization failed: %s", exc)


# Global singleton
runtime = RuntimeState()


# ---------------------------------------------------------------------------
# Auth & Identity Helpers
# ---------------------------------------------------------------------------

def require_api_token(x_api_token: Optional[str]) -> None:
    if not API_AUTH_TOKEN:
        return
    if x_api_token != API_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def resolve_identity(
    req: ChatRequest, x_user_id: Optional[str], x_store_id: Optional[str]
) -> tuple[int, int]:
    if x_user_id and x_store_id:
        try:
            return int(x_user_id), int(x_store_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid identity headers") from exc
    return req.user_id, req.store_id


# ---------------------------------------------------------------------------
# Text Utilities
# ---------------------------------------------------------------------------

def clean_output(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def extract_user_content(full_text: str) -> str:
    match = re.search(r"\[USER REQUEST\]\s*(.*?)(?=\[|$)", full_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return full_text


def web_search_fallback(query: str, max_results: int = 3) -> str:
    logger.info("Web fallback search started", extra={"query": query[:120]})
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, region="vn-vi"))
        if not results:
            return ""
        formatted_results = ""
        for i, res in enumerate(results):
            title = res.get("title", "No Title")
            body = res.get("body", "No snippet")
            formatted_results += f"[{i+1}] {title}\nSnippet: {body}\n\n"
        return formatted_results
    except Exception as exc:
        logger.warning("Web fallback search failed: %s", exc)
        return ""
