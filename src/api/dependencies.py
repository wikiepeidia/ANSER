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

            # KB phải tạo TRƯỚC manager để manager dùng chung embedder của KB
            # (tránh nạp MiniLM 2 lần lên VRAM — xem SemanticRouter(embedder=...)).
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
        """
        Async, lock-guarded vision initialization.

        Vision model (Qwen2-VL-2B) nay nằm TRONG ModelEngine -> VisionAgent chỉ là
        lớp mỏng dùng chung engine đó. Vì vậy phải đảm bảo engine sẵn sàng trước,
        rồi mới tạo VisionAgent(self.engine). (Đã bỏ Florence-2 tự-load.)
        """
        if self.vision:
            return

        async with _vision_load_lock:
            if self.vision:
                return
            if RUNTIME_PROFILE == "text-only":
                self.vision_error = "Vision runtime disabled by RUNTIME_PROFILE=text-only"
                return

            # Engine sở hữu model vision -> tạo engine nếu chưa có (ModelEngine là singleton)
            if not self.engine:
                try:
                    from src.core.engine import ModelEngine
                    self.engine = ModelEngine()
                except Exception as exc:
                    self.engine = None
                    self.engine_error = str(exc)
                    self.vision_error = self.engine_error
                    logger.error("Engine init (for vision) failed: %s", exc)
                    return

            try:
                from src.agents.vision import VisionAgent
                self.vision = VisionAgent(self.engine)   # <-- truyền engine vào (trước đây VisionAgent())
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
    """
    Làm sạch output của model trước khi trả về Body.

    Bản Ngày 7 — sửa 3 lỗi của bản cũ:
      1. Regex <think>.*?</think> cần THẺ ĐÓNG. Khi model lặp tới hết token
         budget nó không kịp viết </think> -> regex không khớp -> toàn bộ nội
         suy lọt ra màn hình. Nay cắt cả trường hợp thẻ không đóng.
      2. Không chống lặp. Model lặp nguyên câu 12 lần vẫn đi thẳng ra ngoài.
      3. Trả chuỗi rỗng khi output toàn <think> -> Body hiện bong bóng trống.
    """
    if not text:
        return _EMPTY_FALLBACK

    # 1) Cắt khối <think> có đóng thẻ đầy đủ
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 2) Cắt <think> KHÔNG đóng thẻ (bị cắt giữa chừng vì hết token budget)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 3) Cắt </think> mồ côi (model quên mở thẻ)
    text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    text = _dedupe_lines(text)

    return text.strip() or _EMPTY_FALLBACK


_EMPTY_FALLBACK = (
    "Xin lỗi, tôi chưa tạo được câu trả lời cho câu này. "
    "Bạn thử hỏi lại ngắn gọn hơn giúp tôi nhé."
)

# Câu ngắn hơn ngưỡng này được phép lặp (ví dụ "Cảm ơn bạn.", dấu phân cách)
_DEDUPE_MIN_LEN = 40


def _dedupe_lines(text: str) -> str:
    """
    Bỏ dòng dài bị lặp. Giữ nguyên thứ tự, chỉ giữ lần xuất hiện đầu tiên.

    Không đụng tới output JSON (nhánh TECHNICAL) vì JSON có thể có dòng giống
    nhau hợp lệ.
    """
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return text

    seen = set()
    out = []
    for line in text.split("\n"):
        key = line.strip()
        if len(key) >= _DEDUPE_MIN_LEN:
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return "\n".join(out)


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