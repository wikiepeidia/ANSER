"""anser/mock-brain — giả lập ANSER Brain (VLM/LLM) cho dev/test.

Trả response cố định, KHÔNG gọi model thật — để build/test luồng automation
mà không cần Colab/ngrok. Nối Brain thật (BRAIN_BASE_URL) khi sẵn sàng.

Domain: CÔNG TY TNHH TRÀ NGỌC DUY (trà/cao atiso Đà Lạt). Giá bán = PUBLIC từ
ngocduygroup.com ngày 2026-07-11; giá thu mua nông hộ = ASSUMED.

Endpoints (khớp ANSER_AI_SPEC + PDF automation V2):
  POST /upload               → OCR chứng từ theo scenario (hóa đơn/đơn A/phiếu cân)
  POST /mcp/validate-invoice → tính lại tổng bằng "code thuần" (deterministic)
  POST /chat                 → sinh text (caption/giải thích/suy luận SL) giả lập
  GET  /health
"""
from fastapi import FastAPI, Request
from typing import Any

app = FastAPI(title="ANSER mock-brain", version="0.2.0")

# Hóa đơn nhập hàng THƯƠNG MẠI (retail QT5) — tổng KHỚP để nhánh is_valid=true chạy
SAMPLE_INVOICE = {
    "supplier": "NCC Trà Thái Nguyên",
    "items": [
        {"sku": "TRA-TN80", "name": "Trà Thái Nguyên 80gr", "qty": 100, "unit_price": 12000},
        {"sku": "LINH-400", "name": "Linh chi lát 400gr",   "qty": 50,  "unit_price": 200000},
    ],
    "total": 100 * 12000 + 50 * 200000,   # 11,200,000
}

# Đơn đặt hàng từ khách A — đại lý đặc sản Đà Lạt (manuf QT1)
SAMPLE_ORDER = {
    "doc_type": "customer_order",
    "doc_no": "A-PO-2001",
    "customer_code": "DL-DAILY-01",
    "region": "Đà Lạt",
    "deadline": "2026-08-30",
    "items": [{"sku": "TRA-TL50", "name": "Trà atiso túi lọc (50 túi)",
               "qty": 500, "unit_price": 87000}],
    "total": 500 * 87000,                 # 43,500,000
}

# PHIẾU CÂN nông hộ/HTX (manuf E2) — cân tại chỗ, KHÔNG có HĐĐT chuẩn.
# Tiền trả nông hộ = kg cân × đơn giá thu mua (ASSUMED 18.000đ/kg bông tươi).
SAMPLE_WEIGHSLIP = {
    "doc_type": "weigh_slip",
    "farmer": "HTX Thuận Phát",
    "region_grown": "Đà Lạt - Xuân Thọ",
    "part": "bông",
    "form": "tuoi",
    "gacp_cert": "GACP-LD-2025-17",
    "items": [{"sku": "BONG-TUOI", "name": "Bông atiso tươi",
               "qty": 300, "unit": "kg", "unit_price": 18000}],
    "total": 300 * 18000,                 # 5,400,000
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-brain", "version": "0.2.0"}


@app.post("/upload")
async def upload(request: Request):
    """OCR giả lập theo scenario:
    ok|mismatch                 → hóa đơn nhập hàng thương mại (retail QT5)
    order|order_mismatch        → đơn đặt hàng từ khách A (manuf QT1)
    weighslip|weighslip_mismatch→ phiếu cân nông hộ/HTX (manuf E2)
    """
    scenario = request.query_params.get("scenario", "ok")
    if scenario.startswith("order"):
        doc = {**SAMPLE_ORDER}
    elif scenario.startswith("weighslip"):
        doc = {**SAMPLE_WEIGHSLIP}
    else:
        doc = {**SAMPLE_INVOICE}
    if scenario.endswith("mismatch"):
        doc = {**doc, "total": 999999}   # tổng OCR sai → nhánh pending_review
    return {"ok": True, **doc}


@app.post("/mcp/validate-invoice")
async def validate_invoice(request: Request):
    """Deterministic-first: tính lại tổng từ items bằng code, so với total OCR."""
    body: dict[str, Any] = await request.json()
    items = body.get("items", [])
    calculated = sum(int(i.get("qty", 0)) * float(i.get("unit_price", 0)) for i in items)
    ocr_total = float(body.get("total", 0))
    diff = round(ocr_total - calculated, 2)
    return {
        "is_valid": abs(diff) < 1,          # khớp trong sai số 1đ
        "calculated_total": calculated,
        "ocr_total": ocr_total,
        "difference": diff,
    }


@app.post("/chat")
async def chat(request: Request):
    """LLM giả lập. 2 chế độ structured (giống Brain thật trả JSON trong text):
    - context.infer_production.items → suy luận SL cần SX (QT1): qty×1.02 (buffer 2% NG)
    - context.estimate_bom {product_code, qty} → ước lượng DS NVL khi thiếu BOM (QT2 3b)
    """
    body: dict[str, Any] = await request.json()
    prompt = str(body.get("prompt", body.get("message", "")))[:150]
    ctx = body.get("context") or {}

    if isinstance(ctx.get("infer_production"), dict):
        import math
        items = ctx["infer_production"].get("items", [])
        inferred = [{"sku": i.get("sku"), "qty_ordered": int(i.get("qty", 0)),
                     "qty_to_produce": math.ceil(int(i.get("qty", 0)) * 1.02),
                     "note": "buffer 2% theo NG lịch sử"} for i in items]
        return {"text": f"[mock-brain] Suy luận SL SX (buffer 2%): {inferred}",
                "inference": {"items": inferred}}

    if isinstance(ctx.get("estimate_bom"), dict):
        eb = ctx["estimate_bom"]
        qty = int(eb.get("qty", 0))
        # Ước lượng thô cho SP chưa có BOM (độ tin cậy thấp — bắt buộc người duyệt).
        # TRA-GUNG: trà xanh ướp gừng — ước 0.08kg trà xanh khô + 0.005kg gừng/hộp.
        materials = [
            {"material_code": "TRA-XANH", "material_name": "Trà xanh khô (ước lượng)",
             "need": round(qty * 0.08, 1), "on_hand": 0,
             "to_buy": round(qty * 0.08, 1), "unit": "kg khô"},
            {"material_code": "GUNG", "material_name": "Gừng tươi Đà Lạt (ước lượng)",
             "need": round(qty * 0.005, 2), "on_hand": 0,
             "to_buy": round(qty * 0.005, 2), "unit": "kg"},
            {"material_code": "TUI-LOC", "material_name": "Túi lọc",
             "need": qty * 50, "on_hand": 0, "to_buy": qty * 50, "unit": "cái"},
        ]
        return {"text": f"[mock-brain] Ước lượng NVL cho {eb.get('product_code')} x{qty} (confidence thấp)",
                "estimation": {"materials": materials, "confidence": 0.55}}

    return {"text": f"[mock-brain] Phản hồi giả lập cho: {prompt}",
            "route": body.get("route", "GENERAL")}
