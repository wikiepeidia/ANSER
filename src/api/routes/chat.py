"""
src/api/routes/chat.py — Chat endpoint and task polling.
Fully async. Uses native await for webhook dispatch.

Ghi chú: nhánh FINANCIAL ĐÃ GỠ — validate hóa đơn nay đi qua /ocr (documents.py)
bằng ảnh, đúng use case OCR. Router không trả 'FINANCIAL' nên khối cũ là dead code.
"""

import json
import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from typing import Optional

from src.api.dependencies import (
    ChatRequest, runtime, require_api_token, resolve_identity,
    clean_output, extract_user_content, web_search_fallback,
)
from src.core.engine import TASK_REGISTRY
from src.core.schemas import RetailChatResponse

logger = logging.getLogger("projecta.api.chat")

router = APIRouter()

# SaasAPI singleton nhẹ (tạo engine 1 lần) — dùng cho route DATA_INTERNAL
_saas = None


def _get_saas():
    global _saas
    if _saas is None:
        from src.core.saas_api import SaasAPI
        _saas = SaasAPI()
    return _saas


@router.get("/api/v1/task/{task_id}")
async def get_task_status(task_id: str):
    task = TASK_REGISTRY.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.pop("_created_at", None)
    return task


@router.post("/chat")
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_token: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    x_store_id: Optional[str] = Header(None),
):
    require_api_token(x_api_token)
    user_id, store_id = resolve_identity(req, x_user_id, x_store_id)
    await runtime.ensure_text_runtime()
    if not runtime.manager or not runtime.coder:
        raise HTTPException(status_code=503, detail="Text runtime unavailable")

    user_msg = extract_user_content(req.message)
    request_id = request.state.request_id
    logger.info(
        "Chat request received",
        extra={"request_id": request_id, "user_id": user_id, "store_id": store_id},
    )

    task_id = str(uuid.uuid4())

    async def process_chat():
        decision = await runtime.manager.analyze_task(user_msg)
        cat = decision.get("category", "GENERAL")
        logger.info("Route selected", extra={"request_id": request_id, "route": cat})

        resp = ""
        if cat == "TECHNICAL":
            plan = await runtime.manager.plan_or_ask(req.message)
            if "[PLAN]" in plan:
                resp = await runtime.coder.write_code(user_msg, plan)
            else:
                resp = plan

        elif cat == "DATA_INTERNAL":
            # Tra dữ liệu THẬT từ DB thay vì context giả "[DB Data]"
            saas = _get_saas()
            products = saas.lookup_product(user_msg, workspace_id=store_id)
            sales = saas.get_sales_report(workspace_id=store_id, period="today")
            db_context = (
                f"[PRODUCTS MATCHING QUERY]\n{products}\n\n"
                f"[SALES TODAY]\n{json.dumps(sales, ensure_ascii=False)}"
            )
            resp = await runtime.manager.consult(user_msg, context=db_context, history="")

        elif cat == "RETRIEVAL":
            logger.info("Retrieval route active", extra={"request_id": request_id})
            context_docs = ""
            found_internal = False

            if runtime.kb:
                results = runtime.kb.search(user_msg, top_k=2)
                if results:
                    context_docs = f"[INTERNAL DOCUMENTS]:\n{results}"
                    found_internal = True
                    logger.info("Internal docs found", extra={"request_id": request_id})

            if not found_internal:
                web_results = web_search_fallback(user_msg)
                if web_results:
                    context_docs = f"[WEB SEARCH RESULTS]:\n{web_results}"
                else:
                    context_docs = "[INFO]: No internal documents or web results found."

            resp = await runtime.manager.consult(user_msg, context=context_docs, history="")

        else:
            resp = await runtime.manager.consult(user_msg, context="", history="")

        cleaned = clean_output(resp)

        # Schema enforcement: wrap response in RetailChatResponse
        # confidence để None (chưa đo) thay vì 1.0 giả
        chat_response = RetailChatResponse(answer=cleaned, sources=None)

        # Proactive Webhook Dispatcher — natively awaited, no thread hacks
        callback_url = os.getenv("BODY_CALLBACK_URL")
        if callback_url:
            try:
                from json_repair import repair_json
                from src.core.utils import HttpClientPool

                parsed_json = repair_json(cleaned, return_objects=True)
                payload = {"task_id": task_id, "result": parsed_json}

                api_token = os.getenv("API_AUTH_TOKEN", "default-secret")
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Token": api_token,
                    "X-Task-ID": task_id,
                }

                client = HttpClientPool.get_client()
                await client.post(callback_url, json=payload, headers=headers)
                logger.info(f"Webhook dispatched for task {task_id}")
            except Exception as e:
                logger.error(f"Webhook dispatch failed for task {task_id}: {e}")

        return chat_response.model_dump()

    # Dispatch via the async background worker
    background_tasks.add_task(runtime.engine.background_worker, task_id, process_chat)
    return {"task_id": task_id, "status": "processing"}