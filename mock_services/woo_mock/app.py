"""anser/woo-mock — giả lập WooCommerce REST API cho kênh 'web'.

Bối cảnh: chưa có quyền admin site Woo thật (ngocduygroup.com), site mẫu của user là
WordPress.com gói Free — KHÔNG cài được plugin WooCommerce (cần gói trả phí) nên không
có /wp-json/wc/v3. Mock này nói ĐÚNG shape API Woo thật (orders + auth consumer key):
khi có site thật chỉ đổi WOO_BASE_URL/WOO_KEY/WOO_SECRET trong .env, không sửa code.

Auth mock: consumer_key=ck_demo & consumer_secret=cs_demo (sai → 401 đúng kiểu Woo).
POST /_add {sku,name,qty,price,first_name} → thêm đơn 'processing' mới (demo/test).
"""
import itertools
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from typing import Any

app = FastAPI(title="ANSER woo-mock", version="0.1.0")

CK, CS = "ck_demo", "cs_demo"
_seq = itertools.count(10001)

def _order(oid: int, sku: str, name: str, qty: int, price: float, first_name: str) -> dict:
    """Shape rút gọn nhưng đúng field thật của WooCommerce order (wc/v3)."""
    return {
        "id": oid,
        "status": "processing",
        "currency": "VND",
        "date_created": datetime.now(timezone.utc).isoformat(),
        "total": str(qty * price),
        "billing": {"first_name": first_name, "last_name": "", "email": "khach@example.com"},
        "line_items": [{"id": 1, "name": name, "sku": sku, "quantity": qty,
                        "price": str(price), "total": str(qty * price)}],
    }

# Seed 1 đơn processing sẵn (poller vòng đầu có dữ liệu; các vòng sau dedup WOO-{id})
ORDERS: list[dict] = [_order(next(_seq), "TRA-TL50", "Trà atiso túi lọc (50 túi)", 1, 87000, "Khách Web Seed")]


@app.get("/health")
def health():
    return {"status": "ok", "service": "woo-mock", "version": "0.1.0"}


@app.get("/wp-json/wc/v3/orders")
def list_orders(request: Request, response: Response):
    q = request.query_params
    if q.get("consumer_key") != CK or q.get("consumer_secret") != CS:
        response.status_code = 401
        return {"code": "woocommerce_rest_cannot_view",
                "message": "Sorry, you cannot list resources.", "data": {"status": 401}}
    status = q.get("status", "any")
    per_page = int(q.get("per_page", 10))
    rows = [o for o in ORDERS if status in ("any", o["status"])]
    return rows[-per_page:]


@app.post("/_add", status_code=201)
async def add_order(request: Request):
    """Bơm đơn web mới cho demo/test (thay người mua bấm đặt hàng trên site)."""
    b: dict[str, Any] = await request.json()
    o = _order(next(_seq), b.get("sku", "TRA-TL50"),
               b.get("name", "Trà atiso túi lọc (50 túi)"),
               int(b.get("qty", 1)), float(b.get("price", 87000)),
               b.get("first_name", "Khách Web"))
    ORDERS.append(o)
    return o
