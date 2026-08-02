"""
src/api/routes/validate.py — POST /mcp/validate-invoice.

Genuinely standalone reconciliation endpoint: pre-extracted {items, total}
JSON in, no image, no OCR/vision call. Reuses ManufacturingInvoicePayload
(schemas.py) and MCPServer.validate_invoice_total (mcp_server.py) completely
unmodified -- same deterministic-first principle as /ocr/manufacturing, just
without the VLM extraction step in front of it. See 11-CONTEXT.md for the
"genuinely separate standalone endpoint" and "no response-field rename layer"
decisions this module implements.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from src.api.dependencies import require_api_token
from src.core.mcp_server import MCPServer
from src.core.schemas import ManufacturingInvoicePayload

logger = logging.getLogger("projecta.api.validate")
router = APIRouter()

# Defensive bound local to this route only (T-11-02) -- not a change to the
# shared ManufacturingInvoicePayload schema, which stays untouched.
_MAX_VALIDATE_ITEMS = 500


@router.post("/mcp/validate-invoice")
async def validate_invoice_endpoint(
    request: Request,
    x_api_token: Optional[str] = Header(None),
):
    """
    Reconcile a caller-supplied {items, total} against MCPServer's
    deterministic recompute. No image, no OCR -- items/total are already
    extracted by the caller (Phase 13: San Xuất's n8n "Merge OCR +
    Validation" second HTTP node).
    """
    require_api_token(x_api_token)

    try:
        raw = await request.json()
    except Exception:
        raw = None

    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=400,
            detail="Thiếu hoặc sai định dạng dữ liệu JSON để đối chiếu hoá đơn",
        )

    try:
        invoice = ManufacturingInvoicePayload(**raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"schema_invalid: {exc}")

    if len(invoice.items) > _MAX_VALIDATE_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"Quá nhiều dòng hàng (tối đa {_MAX_VALIDATE_ITEMS})",
        )

    # Remap unit_price -> price, MCPServer chỉ biết đọc key "price" (same
    # pattern as /ocr/manufacturing, documents.py).
    mcp_items = [
        {"name": it.name, "price": it.unit_price, "qty": it.qty}
        for it in invoice.items
    ]

    try:
        validation = MCPServer.validate_invoice_total(mcp_items, invoice.total)
    except (ArithmeticError, OverflowError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Dữ liệu số không hợp lệ để đối chiếu: {exc}",
        )

    # AI-OCR-03-style honesty bar (verbatim from /ocr/manufacturing): a
    # trivially-valid empty submission (0 == 0) must still be flagged.
    needs_manual_review = (not validation["is_valid"]) or (len(invoice.items) == 0)

    return {
        "success": True,
        "validation": validation,
        "needs_manual_review": needs_manual_review,
    }
