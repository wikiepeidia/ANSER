"""
src/api/routes/chat.py — Chat endpoint và task polling.

Bản Ngày 7. Thay đổi so với bản cũ:

1. Ba nhánh GENERAL / RETRIEVAL / DATA_INTERNAL không còn dùng chung
   `manager.consult()`. Mỗi nhánh gọi method riêng với prompt riêng.
   Đây là fix cho lỗi model lặp vô hạn bảng "4 loại giao thức".

2. Nhánh TECHNICAL validate JSON TRƯỚC KHI trả về. Nếu model sinh JSON hỏng
   (ngoặc lệch, expression sai) thì retry 1 lần với feedback cụ thể; vẫn hỏng
   thì trả thông báo tiếng Việt thay vì đẩy rác xuống Body.

3. Log kèm score/margin của router để đo chất lượng định tuyến.

Ghi chú: nhánh FINANCIAL đã gỡ — validate hoá đơn đi qua /ocr (documents.py).
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

# Thông báo khi không sinh nổi workflow hợp lệ
_WORKFLOW_FAILED_MSG = (
    "Tôi chưa dựng được quy trình hợp lệ cho yêu cầu này. "
    "Bạn mô tả rõ hơn giúp tôi 3 điểm: chạy vào lúc nào, "
    "lấy dữ liệu từ đâu, và gửi kết quả đi đâu."
)


def _get_saas():
    global _saas
    if _saas is None:
        from src.core.saas_api import SaasAPI
        _saas = SaasAPI()
    return _saas


def _extract_json_block(text: str):
    """
    Tách object JSON đầu tiên trong text bằng cách đếm ngoặc.
    Trả về (dict, None) nếu hợp lệ, hoặc (None, lý_do_lỗi).

    Dùng đếm ngoặc thay vì regex vì workflow JSON lồng nhiều tầng.
    """
    if not text:
        return None, "empty output"

    start = text.find("{")
    if start == -1:
        return None, "no JSON object found"

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate), None
                except json.JSONDecodeError as exc:
                    # Thử json_repair cho lỗi nhẹ (dấu phẩy thừa...)
                    try:
                        from json_repair import repair_json
                        repaired = repair_json(candidate, return_objects=True)
                        if isinstance(repaired, dict) and repaired:
                            return repaired, None
                    except Exception:
                        pass
                    return None, f"JSONDecodeError: {exc.msg} tại vị trí {exc.pos}"

    return None, "unbalanced braces (thiếu dấu })"


def _validate_workflow(obj: dict):
    """Kiểm tra workflow tối thiểu. Trả về (ok: bool, lý_do: str)."""
    if not isinstance(obj, dict):
        return False, "output không phải object"
    if obj.get("action") != "create_workflow":
        return False, 'thiếu "action":"create_workflow"'

    payload = obj.get("payload")
    if not isinstance(payload, dict):
        return False, "thiếu payload"

    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False, "payload.nodes rỗng hoặc không phải mảng"

    node_ids = set()
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            return False, f"node[{idx}] không phải object"
        nid = node.get("id")
        if not nid:
            return False, f"node[{idx}] thiếu id"
        node_ids.add(nid)
        if not node.get("type"):
            return False, f"node {nid} thiếu type"
        pos = node.get("position")
        if pos is not None and (not isinstance(pos, list) or len(pos) != 2):
            return False, f"node {nid} có position sai định dạng (phải là [x, y])"

    edges = payload.get("edges", [])
    if not isinstance(edges, list):
        return False, "payload.edges không phải mảng"
    for edge in edges:
        if not isinstance(edge, dict):
            return False, "edge không phải object"
        for side in ("from", "to"):
            ref = edge.get(side)
            if ref and ref not in node_ids:
                return False, f'edge trỏ tới node không tồn tại: "{ref}"'

    # Chặn SQL ghi dữ liệu
    blob = json.dumps(obj, ensure_ascii=False).upper()
    for danger in ("DROP TABLE", "TRUNCATE", "DELETE FROM", "ALTER TABLE"):
        if danger in blob:
            return False, f"workflow chứa lệnh nguy hiểm: {danger}"

    return True, ""


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
        logger.info(
            "Route selected: %s (score=%.2f margin=%.3f method=%s)",
            cat,
            decision.get("score", 0.0),
            decision.get("margin", 0.0),
            decision.get("method", "?"),
            extra={"request_id": request_id, "route": cat},
        )

        resp = ""

        # ------------------------------------------------------------------
        # TECHNICAL — sinh workflow n8n, validate trước khi trả
        # ------------------------------------------------------------------
        if cat == "TECHNICAL":
            plan = await runtime.manager.plan_or_ask(req.message)

            if "[PLAN]" not in plan:
                # Model hỏi lại cho rõ yêu cầu -> trả nguyên câu hỏi
                resp = clean_output(plan)
            else:
                raw = await runtime.coder.write_code(user_msg, plan)
                obj, err = _extract_json_block(raw)

                ok = False
                if obj is not None:
                    ok, err = _validate_workflow(obj)

                if not ok:
                    # Retry đúng 1 lần, đưa lỗi cụ thể làm feedback
                    logger.warning(
                        "Workflow JSON không hợp lệ (%s) — thử lại",
                        err, extra={"request_id": request_id},
                    )
                    feedback = (
                        f"Lần trước JSON bị lỗi: {err}. "
                        "Sửa lại và chỉ xuất JSON hợp lệ, không thêm chữ nào khác."
                    )
                    raw = await runtime.coder.write_code(user_msg, plan, feedback=feedback)
                    obj, err = _extract_json_block(raw)
                    if obj is not None:
                        ok, err = _validate_workflow(obj)

                if ok:
                    # Trả JSON đã chuẩn hoá — Body parse chắc chắn được
                    resp = json.dumps(obj, ensure_ascii=False)
                    logger.info(
                        "Workflow hợp lệ: %d node",
                        len(obj["payload"]["nodes"]),
                        extra={"request_id": request_id},
                    )
                else:
                    logger.error(
                        "Workflow vẫn hỏng sau retry: %s",
                        err, extra={"request_id": request_id},
                    )
                    resp = _WORKFLOW_FAILED_MSG

        # ------------------------------------------------------------------
        # DATA_INTERNAL — dữ liệu thật từ DB cửa hàng
        # ------------------------------------------------------------------
        elif cat == "DATA_INTERNAL":
            saas = _get_saas()
            try:
                products = saas.lookup_product(user_msg, workspace_id=store_id)
                sales = saas.get_sales_report(workspace_id=store_id, period="today")
                db_context = (
                    f"[SẢN PHẨM KHỚP TRUY VẤN]\n{products}\n\n"
                    f"[DOANH SỐ HÔM NAY]\n{json.dumps(sales, ensure_ascii=False)}"
                )
            except Exception as exc:
                logger.warning(
                    "Truy vấn DB thất bại: %s", exc,
                    extra={"request_id": request_id},
                )
                db_context = "(không lấy được dữ liệu từ cơ sở dữ liệu)"

            resp = await runtime.manager.answer_data(user_msg, context=db_context)

        # ------------------------------------------------------------------
        # RETRIEVAL — RAG tài liệu nội bộ, fallback web
        # ------------------------------------------------------------------
        elif cat == "RETRIEVAL":
            context_docs = ""
            found_internal = False

            if runtime.kb:
                try:
                    results = runtime.kb.search(user_msg, top_k=2)
                    if results:
                        context_docs = f"[TÀI LIỆU NỘI BỘ]\n{results}"
                        found_internal = True
                        logger.info(
                            "Tìm thấy tài liệu nội bộ",
                            extra={"request_id": request_id},
                        )
                except Exception as exc:
                    logger.warning(
                        "KB search lỗi: %s", exc,
                        extra={"request_id": request_id},
                    )

            if not found_internal:
                web_results = web_search_fallback(user_msg)
                if web_results:
                    context_docs = f"[KẾT QUẢ TÌM KIẾM]\n{web_results}"
                else:
                    # Không có tài liệu -> để trống, prompt sẽ bảo model
                    # dùng kiến thức sẵn có thay vì than phiền thiếu context
                    context_docs = ""

            resp = await runtime.manager.answer_retrieval(user_msg, context=context_docs)

        # ------------------------------------------------------------------
        # GENERAL — hội thoại, tính toán, giải thích
        # ------------------------------------------------------------------
        else:
            resp = await runtime.manager.answer_general(user_msg)

        cleaned = clean_output(resp)

        chat_response = RetailChatResponse(answer=cleaned, sources=None)

        # Proactive Webhook Dispatcher
        callback_url = os.getenv("BODY_CALLBACK_URL")
        if callback_url:
            try:
                from src.core.utils import HttpClientPool

                # Chỉ parse JSON nếu output THỰC SỰ là JSON (nhánh TECHNICAL).
                # Bản cũ repair_json mọi output, kể cả văn xuôi -> tạo rác.
                parsed, _ = _extract_json_block(cleaned)
                payload = {"task_id": task_id, "result": parsed or cleaned}

                api_token = os.getenv("API_AUTH_TOKEN", "default-secret")
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Token": api_token,
                    "X-Task-ID": task_id,
                }

                client = HttpClientPool.get_client()
                await client.post(callback_url, json=payload, headers=headers)
                logger.info("Webhook dispatched for task %s", task_id)
            except Exception as exc:
                logger.error("Webhook dispatch failed for task %s: %s", task_id, exc)

        return chat_response.model_dump()

    background_tasks.add_task(runtime.engine.background_worker, task_id, process_chat)
    return {"task_id": task_id, "status": "processing"}