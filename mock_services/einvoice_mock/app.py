"""anser/einvoice-mock — giả lập NHÀ CUNG CẤP HĐĐT (NĐ 70/2025) cho dev/test.

Shape TRUNG LẬP (Ngọc Duy chưa chọn NCC): issue / adjust / lookup + mã cơ quan thuế.
Khi chốt NCC thật (MISA meInvoice / VNPT / Viettel S-Invoice) → viết 1 adapter map
field trong rag_service, đổi EINVOICE_API_URL — mock này giữ nguyên làm sandbox test.

Nguyên tắc NĐ 70/2025 mock cũng tuân thủ:
  - KHÔNG có endpoint xóa/hủy hóa đơn — chỉ /api/invoices/adjust (điều chỉnh/thay thế)
  - Mỗi hóa đơn có mã cơ quan thuế (tax_authority_code)
Simulate lỗi NCC: body {"simulate": "fail"} → 503 (test hàng đợi einvoice_pending).
"""
import itertools
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from typing import Any

app = FastAPI(title="ANSER einvoice-mock", version="0.1.0")

_seq = itertools.count(1)
_issued: dict[str, dict] = {}   # invoice_no -> bản ghi (mock in-memory)


@app.get("/health")
def health():
    return {"status": "ok", "service": "einvoice-mock", "version": "0.1.0"}


def _make_invoice(body: dict, adjusts: str | None = None) -> dict:
    n = next(_seq)
    inv = {
        "invoice_no": f"ND26-{n:05d}",
        "tax_authority_code": "CQT-" + uuid.uuid4().hex[:12].upper(),
        "serial": "1C26TND",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "status": "issued",
        "adjusts_invoice_no": adjusts,
        "echo": {k: body.get(k) for k in
                 ("order_no", "buyer_name", "subtotal", "vat_rate", "vat_amount", "total")},
    }
    _issued[inv["invoice_no"]] = inv
    return inv


@app.post("/api/invoices", status_code=201)
async def issue(request: Request, response: Response):
    body: dict[str, Any] = await request.json()
    if body.get("simulate") == "fail":
        response.status_code = 503
        return {"error": "provider_unavailable", "detail": "[mock] NCC HĐĐT bảo trì — thử lại sau"}
    return _make_invoice(body)


@app.post("/api/invoices/adjust", status_code=201)
async def adjust(request: Request, response: Response):
    """Điều chỉnh/thay thế — KHÔNG bao giờ xóa hóa đơn gốc (NĐ 70/2025)."""
    body: dict[str, Any] = await request.json()
    original = body.get("original_invoice_no", "")
    if body.get("simulate") == "fail":
        response.status_code = 503
        return {"error": "provider_unavailable"}
    if original in _issued:
        _issued[original]["status"] = "adjusted"
    return _make_invoice(body, adjusts=original)


@app.get("/api/invoices/{invoice_no}")
def lookup(invoice_no: str, response: Response):
    inv = _issued.get(invoice_no)
    if not inv:
        response.status_code = 404
        return {"error": "not_found"}
    return inv
