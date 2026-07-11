"""ANSER rag_service v0.6.0 — DB gateway + RAG cho stack automation (V2 tra/cao atiso).

Vai trò: điểm tích hợp DB ổn định cho n8n (không để workflow nói thẳng SQL).
Nguyên tắc: mọi query tham số hóa (chống SQLi), idempotency cho ingest,
số liệu tính bằng SQL/code (deterministic-first).

Cấu hình DB (ưu tiên POSTGRES_URL cho Neon; fallback PG_* theo PDF 3):
  POSTGRES_URL=postgresql://user:pass@host/db
  hoặc  PG_HOST / PG_DB / PG_USER / PG_PASSWORD
Chroma:
  CHROMA_URL=http://anser-chroma:8000
"""
import os
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import chromadb
import psycopg2
import psycopg2.extras

app = FastAPI(title="ANSER rag_service", version="0.6.0")

# ── Cấu hình ──────────────────────────────────────────────────────────────────
def _build_pg_url() -> str:
    url = os.environ.get("POSTGRES_URL", "")
    if url:
        return url
    host = os.environ.get("PG_HOST")
    if host:
        user = os.environ.get("PG_USER", "postgres")
        pw   = os.environ.get("PG_PASSWORD", "postgres")
        db   = os.environ.get("PG_DB", "postgres")
        port = os.environ.get("PG_PORT", "5432")
        return f"postgresql://{user}:{pw}@{host}:{port}/{db}"
    return ""

POSTGRES_URL = _build_pg_url()
_chroma = urlparse(os.environ.get("CHROMA_URL", "http://anser-chroma:8000"))
client = chromadb.HttpClient(host=_chroma.hostname or "anser-chroma",
                             port=_chroma.port or 8000)

# event_type registry (PDF 3 mục 3.1) + alias tương thích ngược
EVENT_TYPE_ALIAS = {
    "sale_completed": "sale",       # POS cũ gửi sale_completed
    "payment_received": "sale",
    "invoice": "sale",
}

def get_conn():
    if not POSTGRES_URL:
        raise HTTPException(status_code=500, detail="POSTGRES_URL/PG_* chưa cấu hình")
    return psycopg2.connect(POSTGRES_URL)


# ── Models ────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    text: str
    n_results: int = 3

class AddRequest(BaseModel):
    collection: str = "security_context"
    ids: list[str]
    documents: list[str]

class IoTEventRequest(BaseModel):
    device_id: str
    event_type: str
    payload: dict[str, Any] = {}
    timestamp_source: Optional[str] = None
    idempotency_key: Optional[str] = None

class NewCustomerRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class ImportLine(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    qty: int = 0
    unit_price: float = 0

class ImportRequest(BaseModel):
    supplier: Optional[str] = None
    total_amount: float = 0
    source_file: Optional[str] = None
    items: list[ImportLine] = []

class PendingReviewRequest(BaseModel):
    kind: str = "invoice_import"
    reason: str
    ocr_total: float = 0
    calculated_total: float = 0
    raw_payload: dict[str, Any] = {}

class WorkflowErrorRequest(BaseModel):
    workflow_name: str
    node_name: Optional[str] = None
    error_message: str
    execution_id: Optional[str] = None

class PODraft(BaseModel):
    sku: Optional[str] = None
    product_name: str
    predicted_demand: int = 0
    current_stock: int = 0
    reorder_qty: int = 0

class PODraftBatch(BaseModel):
    items: list[PODraft] = []

class SocialPostLog(BaseModel):
    promo_id: Optional[int] = None
    caption: str
    channel: str = "facebook"
    external_post_id: Optional[str] = None

class MarketplaceOrder(BaseModel):
    marketplace: str
    external_order_id: str
    total_amount: float = 0
    items: list[dict[str, Any]] = []       # [{name, qty, price}]

class DebtLog(BaseModel):
    customer_id: int
    channel: str = "zalo"
    message: str

class CompetitorRow(BaseModel):
    sku: Optional[str] = None
    product_name: str
    our_price: float = 0
    competitor_price: float = 0
    source: Optional[str] = None

class CompetitorBatch(BaseModel):
    rows: list[CompetitorRow] = []
    alert_ratio: float = 1.10              # cảnh báo nếu our > competitor * ratio

# ── Bán lẻ V2: C1 (SePay + VietQR) & B1 (HĐĐT) ───────────────────────────────
class OrderLine(BaseModel):
    sku: Optional[str] = None
    name: str
    qty: int = 1
    price: float = 0                        # giá bán lẻ ĐÃ gồm VAT

class OrderCreate(BaseModel):
    items: list[OrderLine]
    customer_name: Optional[str] = None
    channel: str = "store"

class SepayWebhook(BaseModel):
    """Payload webhook SePay thực tế (PDF V2 DEEPDIVE phần C1)."""
    id: int
    gateway: Optional[str] = None
    transactionDate: Optional[str] = None
    content: str = ""
    transferAmount: float = 0
    transferType: str = "in"
    accountNumber: Optional[str] = None
    referenceCode: Optional[str] = None

class EinvoiceIssue(BaseModel):
    order_no: str
    buyer_name: Optional[str] = None
    buyer_tax_code: Optional[str] = None
    simulate: Optional[str] = None          # 'fail' → test hàng đợi einvoice_pending
    issue_date: Optional[str] = None        # test-only: kiểm bảng VAT theo ngày

class EinvoiceAdjust(BaseModel):
    original_invoice_no: str
    reason: str
    new_total: Optional[float] = None
    simulate: Optional[str] = None

# ── A1: đồng bộ tồn kho & đơn đa kênh (FEFO theo lô) ─────────────────────────
class LotInsert(BaseModel):
    sku: str
    lot_code: Optional[str] = None
    expiry_date: str                        # ISO date
    qty: int
    source: str = "manual"
    batch_code: Optional[str] = None

class ChannelOrderSync(BaseModel):
    """Đơn đã CHUẨN HÓA từ kênh (web/shopee/tiktok) — idempotent theo mã đơn kênh."""
    channel: str
    external_order_id: str
    customer_name: Optional[str] = None
    is_gift: bool = False
    items: list[OrderLine]

class ChannelDelivered(BaseModel):
    external_order_id: Optional[str] = None
    order_no: Optional[str] = None


# ── Manufacturing (V2 trà/cao atiso) ─────────────────────────────────────────
class MaterialBatchInsert(BaseModel):
    """E2: lô nguyên liệu từ nông hộ/HTX (cân tại chỗ, mùa vụ)."""
    lot_code: str
    farmer: Optional[str] = None
    region_grown: Optional[str] = None
    part: Optional[str] = None              # bông | lá | thân | rễ
    form: str = "tuoi"                      # tuoi (cửa sổ 24h) | kho
    material_code: str
    qty_kg: float = 0
    unit_cost_vnd: float = 0
    harvest_ts: Optional[str] = None        # ISO; đồng hồ 24h tính từ đây
    gacp_cert: Optional[str] = None
    order_code: Optional[str] = None        # mua theo đơn (nếu có)

class ProcessEvent(BaseModel):
    """F1: sự kiện mẻ chế biến — start | stage | complete."""
    event: str
    batch_code: str
    # start
    order_code: Optional[str] = None
    material_lot_code: Optional[str] = None
    input_material_kg: float = 0
    shift: Optional[str] = None
    source: str = "manual"
    # stage
    stage: Optional[str] = None             # heo|cat|len_men|xao|vo|say|say_lai
    temp_c: Optional[float] = None
    duration_min: Optional[int] = None
    operator: Optional[str] = None
    note: Optional[str] = None
    # complete
    output_units: int = 0
    ng_units: int = 0
    moisture_pct: Optional[float] = None
    material_cost_vnd: float = 0
    labor_cost_vnd: float = 0

class LabResultInsert(BaseModel):
    """F2: kết quả kiểm nghiệm dược liệu — gate cứng trước khi bán."""
    batch_code: str
    cynarin_pct: float = 0
    mold_cfu_g: int = 0
    pesticide_ok: bool = True
    heavy_metal_ok: bool = True
    tested_by: Optional[str] = None

class ProductionReportInsert(BaseModel):
    scope: str
    ref: str
    yield_actual_pct: float = 0
    yield_deviation_pct: float = 0
    ng_pct: float = 0
    cost_vnd: float = 0
    revenue_vnd: float = 0
    profit_pct: float = 0
    ai_explanation: Optional[str] = None

class ProductionOrderInsert(BaseModel):
    order_code: str
    customer_code: Optional[str] = None
    product_code: str
    product_name: Optional[str] = None
    qty_ordered: int = 0
    qty_to_produce: int = 0
    unit_price: float = 0
    region: Optional[str] = None
    deadline: Optional[str] = None

class MaterialLine(BaseModel):
    material_code: str
    material_name: Optional[str] = None
    need: float = 0
    on_hand: float = 0
    to_buy: float = 0
    unit: Optional[str] = None

class MaterialReqInsert(BaseModel):
    order_code: str
    materials: list[MaterialLine] = []
    estimation_method: str = "llm_fallback"
    batches_suggested: Optional[int] = None

# ── Health / RAG ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.6.0"}

@app.post("/query")
def query(req: QueryRequest):
    try:
        col = client.get_collection("security_context")
        results = col.query(query_texts=[req.text], n_results=req.n_results)
        docs = results.get("documents", [[]])[0]
        return {"documents": docs, "found": len(docs)}
    except Exception as e:
        return {"documents": [], "found": 0, "error": str(e)}

@app.post("/init")
def init_collection(req: AddRequest):
    try:
        client.delete_collection(req.collection)
    except Exception:
        pass
    col = client.get_or_create_collection(req.collection, metadata={"hnsw:space": "cosine"})
    col.add(ids=req.ids, documents=req.documents,
            metadatas=[{"source": "mitre_attck"} for _ in req.documents])
    return {"status": "ok", "count": len(req.documents)}


# ── IoT ingest (idempotent) ──────────────────────────────────────────────────
@app.post("/iot-insert", status_code=201)
def iot_insert(event: IoTEventRequest):
    """Insert 1 sự kiện IoT. Idempotent theo idempotency_key (PDF 3 mục 3)."""
    event_type = EVENT_TYPE_ALIAS.get(event.event_type, event.event_type)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                if event.idempotency_key:
                    # dedup: nếu key đã tồn tại → trả row cũ, không insert trùng
                    cur.execute(
                        """
                        INSERT INTO iot_events
                            (device_id, event_type, payload, timestamp_source, idempotency_key)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (idempotency_key) DO NOTHING
                        RETURNING id, created_at
                        """,
                        (event.device_id, event_type, psycopg2.extras.Json(event.payload),
                         event.timestamp_source, event.idempotency_key),
                    )
                    row = cur.fetchone()
                    if row is None:  # conflict → lấy row cũ
                        cur.execute("SELECT id, created_at FROM iot_events WHERE idempotency_key = %s",
                                    (event.idempotency_key,))
                        row = cur.fetchone()
                        conn.commit()
                        return {"status": "duplicate", "id": row[0], "created_at": str(row[1]),
                                "deduped": True}
                else:
                    cur.execute(
                        """
                        INSERT INTO iot_events (device_id, event_type, payload, timestamp_source)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, created_at
                        """,
                        (event.device_id, event_type, psycopg2.extras.Json(event.payload),
                         event.timestamp_source),
                    )
                    row = cur.fetchone()
            conn.commit()
        return {"status": "inserted", "id": row[0], "created_at": str(row[1]), "deduped": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Daily sales (SEC-5: tham số hóa) ─────────────────────────────────────────
@app.get("/daily-sales")
def daily_sales(date: Optional[str] = None):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total_orders,
                           COALESCE(SUM(total_amount), 0) AS total_revenue,
                           COUNT(DISTINCT user_id) AS unique_staff
                    FROM sales
                    WHERE created_at::date = COALESCE(%s::date, CURRENT_DATE)
                """, (date or None,))
                summary = dict(cur.fetchone())
                summary['total_revenue'] = float(summary['total_revenue'])

                cur.execute("""
                    SELECT item->>'name' AS product_name,
                           SUM((item->>'qty')::int) AS qty_sold,
                           SUM((item->>'price')::numeric * (item->>'qty')::int) AS revenue
                    FROM sales, jsonb_array_elements(items::jsonb) AS item
                    WHERE created_at::date = COALESCE(%s::date, CURRENT_DATE)
                    GROUP BY item->>'name'
                    ORDER BY revenue DESC
                    LIMIT 5
                """, (date or None,))
                top_products = [dict(r) for r in cur.fetchall()]
                for p in top_products:
                    p['revenue'] = float(p['revenue'])
        return {"date": date or "today", "summary": summary, "top_products": top_products}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Low stock (per-product threshold — đóng gap G1) ──────────────────────────
@app.get("/low-stock")
def low_stock(threshold: Optional[int] = None):
    """SP dưới ngưỡng RIÊNG của từng SP (low_stock_threshold); ưu tiên thiếu tương đối.
    Có thể override toàn cục bằng ?threshold= (giữ tương thích ngược)."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, code, stock_quantity, low_stock_threshold, price, category
                    FROM products
                    WHERE stock_quantity < COALESCE(%s, low_stock_threshold)
                    ORDER BY (stock_quantity::float / NULLIF(COALESCE(%s, low_stock_threshold),0)) ASC
                    LIMIT 10
                """, (threshold, threshold))
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    it['price'] = float(it['price']) if it.get('price') else 0
        return {"threshold": threshold, "count": len(items), "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Customer insert (bug 'coalesce' đã vá) ───────────────────────────────────
@app.post("/customer-insert", status_code=201)
def customer_insert(req: NewCustomerRequest):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COALESCE(MAX(id),0)+1 AS next_id FROM customers")
                next_id = cur.fetchone()['next_id']
                code = f"KH{next_id:04d}"
                cur.execute("""
                    INSERT INTO customers (code, name, email, phone, address, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    RETURNING id, code, name, email, phone, created_at
                """, (code, req.name, req.email, req.phone, req.address))
                row = dict(cur.fetchone())
                row['created_at'] = str(row['created_at'])
            conn.commit()
        return {"status": "created", **row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Import OCR hóa đơn nhập (QT5 retail) ─────────────────────────────────────
@app.post("/import-insert", status_code=201)
def import_insert(req: ImportRequest):
    """Ghi phiếu nhập kho (transaction: parent + details). Trả import_id."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO import_transactions (supplier, total_amount, source_file)
                    VALUES (%s, %s, %s) RETURNING id, created_at
                """, (req.supplier, req.total_amount, req.source_file))
                parent = dict(cur.fetchone())
                for line in req.items:
                    cur.execute("""
                        INSERT INTO import_details (import_id, sku, name, qty, unit_price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (parent['id'], line.sku, line.name, line.qty, line.unit_price))
                cur.execute("""
                    INSERT INTO audit_log (entity, entity_id, action, details)
                    VALUES ('import_transactions', %s, 'create', %s)
                """, (str(parent['id']), psycopg2.extras.Json({"lines": len(req.items)})))
            conn.commit()
        return {"status": "imported", "import_id": parent['id'],
                "created_at": str(parent['created_at']), "lines": len(req.items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pending-review", status_code=201)
def pending_review(req: PendingReviewRequest):
    """Hóa đơn lệch tổng → chờ người xác nhận, KHÔNG tự ghi kho."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO pending_review (kind, reason, ocr_total, calculated_total, raw_payload)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at
                """, (req.kind, req.reason, req.ocr_total, req.calculated_total,
                      psycopg2.extras.Json(req.raw_payload)))
                row = dict(cur.fetchone())
            conn.commit()
        return {"status": "pending", "id": row['id'], "created_at": str(row['created_at'])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Error handler log (PDF 3 mục 4.3) ────────────────────────────────────────
@app.post("/workflow-error", status_code=201)
def workflow_error(req: WorkflowErrorRequest):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workflow_errors (workflow_name, node_name, error_message, execution_id)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (req.workflow_name, req.node_name, req.error_message, req.execution_id))
                new_id = cur.fetchone()[0]
            conn.commit()
        return {"status": "logged", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products")
def products(limit: int = 100):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id, code, name, price FROM products ORDER BY id LIMIT %s", (limit,))
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    it['price'] = float(it['price']) if it.get('price') else 0
        return {"count": len(items), "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT6: Forecast reorder (moving average — deterministic-first) ─────────────
@app.get("/forecast-reorder")
def forecast_reorder(horizon_days: int = 14, window_days: int = 30):
    """Dự báo bằng trung bình trượt từ lịch sử sales; reorder = max(0, dự báo - tồn).
    KHÔNG dùng LLM (nguyên tắc deterministic-first cho số liệu)."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT p.code, p.name, p.stock_quantity,
                           COALESCE((
                               SELECT SUM((item->>'qty')::int)
                               FROM sales s, jsonb_array_elements(s.items::jsonb) AS item
                               WHERE s.created_at >= now() - (%s || ' days')::interval
                                 AND (item->>'name') = p.name
                           ), 0) AS sold
                    FROM products p
                """, (window_days,))
                rows = cur.fetchall()
        suggestions = []
        for r in rows:
            avg_daily = float(r["sold"]) / max(window_days, 1)
            predicted = round(avg_daily * horizon_days)
            reorder = max(0, predicted - int(r["stock_quantity"]))
            if reorder > 0:
                suggestions.append({"sku": r["code"], "product_name": r["name"],
                                    "predicted_demand": predicted,
                                    "current_stock": r["stock_quantity"], "reorder_qty": reorder})
        return {"horizon_days": horizon_days, "window_days": window_days,
                "count": len(suggestions), "suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/po-draft-insert", status_code=201)
def po_draft_insert(batch: PODraftBatch):
    try:
        ids = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                for it in batch.items:
                    cur.execute("""
                        INSERT INTO purchase_orders_draft
                            (sku, product_name, predicted_demand, current_stock, reorder_qty)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (it.sku, it.product_name, it.predicted_demand, it.current_stock, it.reorder_qty))
                    ids.append(cur.fetchone()[0])
            conn.commit()
        return {"status": "drafted", "count": len(ids), "ids": ids}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT7: promotions + social post log ────────────────────────────────────────
@app.get("/promo-list")
def promo_list():
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id, product_code, product_name, discount_pct FROM promotions WHERE active")
                items = [dict(r) for r in cur.fetchall()]
        return {"count": len(items), "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/social-post-log", status_code=201)
def social_post_log(req: SocialPostLog):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO social_posts (promo_id, caption, channel, external_post_id)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (req.promo_id, req.caption, req.channel, req.external_post_id))
                new_id = cur.fetchone()[0]
            conn.commit()
        return {"status": "logged", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT8: marketplace order (idempotent theo external_order_id) ───────────────
@app.post("/marketplace-upsert", status_code=201)
def marketplace_upsert(order: MarketplaceOrder):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO marketplace_orders (marketplace, external_order_id, raw)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (external_order_id) DO NOTHING
                    RETURNING id
                """, (order.marketplace, order.external_order_id,
                      psycopg2.extras.Json({"items": order.items, "total": order.total_amount})))
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    return {"status": "duplicate", "deduped": True}
                mp_id = row[0]
                # map -> sales + trừ tồn kho theo tên SP
                cur.execute("INSERT INTO sales (user_id, total_amount, items) VALUES (NULL, %s, %s) RETURNING id",
                            (order.total_amount, psycopg2.extras.Json(order.items)))
                sale_id = cur.fetchone()[0]
                for it in order.items:
                    cur.execute("UPDATE products SET stock_quantity = GREATEST(0, stock_quantity - %s) WHERE name = %s",
                                (int(it.get("qty", 0)), it.get("name")))
                cur.execute("UPDATE marketplace_orders SET mapped_sale_id = %s WHERE id = %s", (sale_id, mp_id))
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('marketplace_orders', %s, 'import', %s)""",
                            (str(mp_id), psycopg2.extras.Json({"sale_id": sale_id})))
            conn.commit()
        return {"status": "imported", "sale_id": sale_id, "deduped": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT9: debtors (công nợ quá hạn, opt-in) + debt log ───────────────────────
@app.get("/debtors")
def debtors(overdue_days: int = 30):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, code, name, phone, email, debt_amount, last_payment_date
                    FROM customers
                    WHERE debt_amount > 0
                      AND marketing_opt_in = true          -- chỉ khách đã opt-in (luật marketing)
                      AND (last_payment_date IS NULL OR last_payment_date < CURRENT_DATE - %s)
                    ORDER BY debt_amount DESC
                """, (overdue_days,))
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    it['debt_amount'] = float(it['debt_amount'])
                    it['last_payment_date'] = str(it['last_payment_date'])
        return {"count": len(items), "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debt-log", status_code=201)
def debt_log(req: DebtLog):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO debt_reminders (customer_id, channel, message) VALUES (%s,%s,%s) RETURNING id",
                            (req.customer_id, req.channel, req.message))
                new_id = cur.fetchone()[0]
            conn.commit()
        return {"status": "logged", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Bán lẻ V2 — C1: SePay + VietQR động  |  B1: HĐĐT (NĐ 70/2025)
# ═══════════════════════════════════════════════════════════════════════════
import hashlib
import json as _json
import re as _re
import urllib.parse
import urllib.request
from datetime import date as _date

VIETQR_BANK = os.environ.get("VIETQR_BANK", "MB")
VIETQR_ACC = os.environ.get("VIETQR_ACC", "0000000000")
VIETQR_NAME = os.environ.get("VIETQR_NAME", "CONG TY TNHH TRA NGOC DUY")
EINVOICE_API = os.environ.get("EINVOICE_API_URL", "http://einvoice-mock:8200")
BACKUP_URLS = [u for u in (os.environ.get("BACKUP_URL_1", ""),
                           os.environ.get("BACKUP_URL_2", "")) if u]

# Bảng thuế suất VAT theo ngày hiệu lực (ASSUMED — chờ kế toán Ngọc Duy xác nhận):
# NQ 204/2025 giảm 8% đến hết 31/12/2026, sau đó về 10% chuẩn.
VAT_SCHEDULE = [(_date(2026, 12, 31), 8.0), (_date(9999, 12, 31), 10.0)]

def _vat_rate(d: _date) -> float:
    for end, rate in VAT_SCHEDULE:
        if d <= end:
            return rate
    return VAT_SCHEDULE[-1][1]

def _split_vat(total: float, rate: float):
    """Giá bán lẻ ĐÃ gồm VAT → tách ngược (code thuần, làm tròn 2 số)."""
    subtotal = round(total / (1 + rate / 100), 2)
    return subtotal, round(total - subtotal, 2)

def _http_json(method: str, url: str, body: dict, timeout: int = 15):
    req = urllib.request.Request(url, data=_json.dumps(body).encode(), method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, _json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, _json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


@app.post("/order-create", status_code=201)
def order_create(o: OrderCreate):
    """C1: tạo đơn + sinh VietQR động (nội dung CK nhúng mã đơn 'NGOCDUY DH{id}')."""
    try:
        total = round(sum(l.qty * l.price for l in o.items), 2)   # tiền tính bằng code thuần
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO channel_orders (channel, customer_name, items, total_amount)
                    VALUES (%s,%s,%s,%s) RETURNING id
                """, (o.channel, o.customer_name,
                      psycopg2.extras.Json([l.model_dump() for l in o.items]), total))
                oid = cur.fetchone()[0]
                order_no = f"DH{oid}"
                add_info = f"NGOCDUY {order_no}"
                qr_url = (f"https://img.vietqr.io/image/{VIETQR_BANK}-{VIETQR_ACC}-compact2.png?"
                          + urllib.parse.urlencode({"amount": int(total), "addInfo": add_info,
                                                    "accountName": VIETQR_NAME}))
                cur.execute("UPDATE channel_orders SET order_no=%s, qr_url=%s WHERE id=%s",
                            (order_no, qr_url, oid))
            conn.commit()
        return {"status": "created", "order_no": order_no, "total_amount": total,
                "transfer_content": add_info, "qr_url": qr_url, "payment_status": "unpaid"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sepay-webhook-process", status_code=200)
def sepay_webhook_process(w: SepayWebhook):
    """C1: đối soát CK — khớp mã đơn + đúng tiền → paid; mọi ca lệch → chờ đối soát tay."""
    try:
        if w.transferType != "in":
            return {"action": "ignored", "reason": "không phải tiền vào"}
        m = _re.search(r"DH\s*(\d+)", w.content or "", _re.I)
        order_no = f"DH{m.group(1)}" if m else None
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Idempotent: SePay retry cùng id giao dịch → không xử lý lại
                cur.execute("""SELECT order_no FROM channel_orders WHERE sepay_tx_id=%s
                               UNION SELECT suggested_order FROM payment_pending WHERE sepay_tx_id=%s""",
                            (str(w.id), str(w.id)))
                if cur.fetchone():
                    return {"action": "duplicate", "deduped": True, "sepay_tx_id": w.id}

                order = None
                if order_no:
                    cur.execute("""SELECT id, order_no, total_amount, payment_status
                                   FROM channel_orders WHERE order_no=%s""", (order_no,))
                    order = cur.fetchone()

                def hold(reason, suggested):
                    cur.execute("""
                        INSERT INTO payment_pending (sepay_tx_id, gateway, content, amount, reason, suggested_order)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (sepay_tx_id) DO NOTHING RETURNING id
                    """, (str(w.id), w.gateway, w.content, w.transferAmount, reason, suggested))
                    row = cur.fetchone()
                    conn.commit()
                    return {"action": "review", "reason": reason, "suggested_order": suggested,
                            "pending_id": row["id"] if row else None}

                if order and order["payment_status"] == "unpaid" \
                        and abs(float(order["total_amount"]) - w.transferAmount) < 0.01:
                    cur.execute("""UPDATE channel_orders
                                   SET payment_status='paid', sepay_tx_id=%s, paid_at=now()
                                   WHERE id=%s""", (str(w.id), order["id"]))
                    cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                                   VALUES ('channel_orders', %s, 'paid_sepay', %s)""",
                                (order_no, psycopg2.extras.Json(
                                    {"sepay_id": w.id, "gateway": w.gateway,
                                     "amount": w.transferAmount})))
                    conn.commit()
                    return {"action": "matched", "order_no": order_no,
                            "amount": w.transferAmount, "gateway": w.gateway}

                if order and order["payment_status"] != "unpaid":
                    return hold(f"đơn {order_no} đã thanh toán trước đó", order_no)
                if order:
                    return hold(f"lệch tiền: CK {w.transferAmount:,.0f} ≠ đơn "
                                f"{float(order['total_amount']):,.0f}", order_no)
                # Không đọc được mã đơn → gợi ý đơn unpaid khớp số tiền gần nhất trong 24h
                cur.execute("""SELECT order_no FROM channel_orders
                               WHERE payment_status='unpaid' AND created_at >= now()-interval '24 hours'
                               ORDER BY ABS(total_amount - %s) ASC LIMIT 1""", (w.transferAmount,))
                sug = cur.fetchone()
                return hold("không đọc được mã đơn trong nội dung CK",
                            sug["order_no"] if sug else None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/einvoice-issue", status_code=201)
def einvoice_issue(req: EinvoiceIssue):
    """B1: phát hành HĐĐT qua NCC (mock/thật qua EINVOICE_API_URL).
    Lỗi NCC → hàng đợi einvoice_pending (không để đơn thiếu hóa đơn) + trả 'queued'."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""SELECT order_no, customer_name, items, total_amount
                               FROM channel_orders WHERE order_no=%s""", (req.order_no,))
                order = cur.fetchone()
                if not order:
                    raise HTTPException(status_code=400, detail=f"order_no không tồn tại: {req.order_no}")
                # Idempotent: đơn đã có HĐ hiệu lực → không phát hành trùng
                cur.execute("""SELECT invoice_no FROM einvoices
                               WHERE order_no=%s AND status='issued'""", (req.order_no,))
                dup = cur.fetchone()
                if dup:
                    return {"status": "duplicate", "deduped": True, "invoice_no": dup["invoice_no"]}

                d = _date.fromisoformat(req.issue_date) if req.issue_date else _date.today()
                rate = _vat_rate(d)
                total = float(order["total_amount"])
                subtotal, vat = _split_vat(total, rate)
                provider_req = {"order_no": req.order_no,
                                "buyer_name": req.buyer_name or order["customer_name"] or "Khách lẻ",
                                "buyer_tax_code": req.buyer_tax_code,
                                "items": order["items"], "subtotal": subtotal,
                                "vat_rate": rate, "vat_amount": vat, "total": total,
                                "simulate": req.simulate}
                s, resp = _http_json("POST", f"{EINVOICE_API}/api/invoices", provider_req)
                if s != 201:
                    cur.execute("""INSERT INTO einvoice_pending (order_no, request, error)
                                   VALUES (%s,%s,%s) RETURNING id""",
                                (req.order_no, psycopg2.extras.Json(provider_req),
                                 _json.dumps(resp)[:500]))
                    qid = cur.fetchone()["id"]
                    conn.commit()
                    return {"status": "queued", "pending_id": qid,
                            "reason": f"NCC HĐĐT lỗi (HTTP {s}) — đã vào hàng đợi phát hành lại"}
                payload = {**provider_req, "provider_response": resp}
                payload.pop("simulate", None)
                checksum = hashlib.sha256(
                    _json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                cur.execute("""
                    INSERT INTO einvoices (invoice_no, order_no, buyer_name, buyer_tax_code, items,
                                           subtotal, vat_rate, vat_amount, total, tax_authority_code,
                                           provider, payload, checksum)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (resp["invoice_no"], req.order_no, provider_req["buyer_name"],
                      req.buyer_tax_code, psycopg2.extras.Json(order["items"]),
                      subtotal, rate, vat, total, resp.get("tax_authority_code"),
                      "mock" if "einvoice-mock" in EINVOICE_API else "real",
                      psycopg2.extras.Json(payload), checksum))
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('einvoices', %s, 'issue', %s)""",
                            (resp["invoice_no"], psycopg2.extras.Json(
                                {"order_no": req.order_no, "vat_rate": rate, "total": total})))
            conn.commit()
        return {"status": "issued", "invoice_no": resp["invoice_no"],
                "tax_authority_code": resp.get("tax_authority_code"),
                "vat_rate": rate, "subtotal": subtotal, "vat_amount": vat, "total": total,
                "checksum": checksum}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/einvoice-adjust", status_code=201)
def einvoice_adjust(req: EinvoiceAdjust):
    """B1: NĐ 70/2025 — KHÔNG hủy hóa đơn; sai sót → phát hành HĐ điều chỉnh, lưu vết cả hai."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM einvoices WHERE invoice_no=%s", (req.original_invoice_no,))
                org = cur.fetchone()
                if not org:
                    raise HTTPException(status_code=400,
                                        detail=f"HĐ gốc không tồn tại: {req.original_invoice_no}")
                total = req.new_total if req.new_total is not None else float(org["total"])
                rate = _vat_rate(_date.today())
                subtotal, vat = _split_vat(total, rate)
                s, resp = _http_json("POST", f"{EINVOICE_API}/api/invoices/adjust",
                                     {"original_invoice_no": req.original_invoice_no,
                                      "order_no": org["order_no"], "reason": req.reason,
                                      "subtotal": subtotal, "vat_rate": rate,
                                      "vat_amount": vat, "total": total,
                                      "simulate": req.simulate})
                if s != 201:
                    raise HTTPException(status_code=502, detail=f"NCC HĐĐT lỗi (HTTP {s})")
                payload = {"reason": req.reason, "original": req.original_invoice_no,
                           "provider_response": resp}
                checksum = hashlib.sha256(
                    _json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                cur.execute("""
                    INSERT INTO einvoices (invoice_no, order_no, buyer_name, items, subtotal,
                                           vat_rate, vat_amount, total, tax_authority_code,
                                           status, adjusts_invoice_no, provider, payload, checksum)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'issued',%s,%s,%s,%s)
                """, (resp["invoice_no"], org["order_no"], org["buyer_name"],
                      psycopg2.extras.Json(org["items"]), subtotal, rate, vat, total,
                      resp.get("tax_authority_code"), req.original_invoice_no,
                      org["provider"], psycopg2.extras.Json(payload), checksum))
                # HĐ gốc: đánh dấu 'adjusted' — VẪN TỒN TẠI (không xóa, lưu vết ≥10 năm)
                cur.execute("UPDATE einvoices SET status='adjusted' WHERE invoice_no=%s",
                            (req.original_invoice_no,))
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('einvoices', %s, 'adjust', %s)""",
                            (resp["invoice_no"], psycopg2.extras.Json(
                                {"original": req.original_invoice_no, "reason": req.reason})))
            conn.commit()
        return {"status": "adjusted", "new_invoice_no": resp["invoice_no"],
                "original_invoice_no": req.original_invoice_no,
                "original_status": "adjusted (vẫn lưu vết, không xóa)",
                "tax_authority_code": resp.get("tax_authority_code"), "total": total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/einvoice-backup-run", status_code=200)
def einvoice_backup_run():
    """B1: backup HĐĐT ≥2 đích + checksum (lưu ≥10 năm — không chỉ 1 nơi)."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""SELECT invoice_no, order_no, status, total::float, checksum,
                                      issued_at::text
                               FROM einvoices ORDER BY id""")
                rows = [dict(r) for r in cur.fetchall()]
        export = {"generated_at": str(_date.today()), "count": len(rows), "invoices": rows}
        blob = _json.dumps(export, sort_keys=True, ensure_ascii=False)
        checksum = hashlib.sha256(blob.encode()).hexdigest()
        results = []
        for url in BACKUP_URLS:
            s, _r = _http_json("POST", url, {"filename": f"einvoices-{_date.today()}.json",
                                             "checksum": checksum, "count": len(rows),
                                             "data": export})
            results.append({"target": url.rsplit("/", 1)[-1], "http": s, "ok": 200 <= s < 300})
        ok_n = sum(1 for r in results if r["ok"])
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('einvoices', 'backup', 'backup_run', %s)""",
                            (psycopg2.extras.Json({"count": len(rows), "checksum": checksum,
                                                   "targets_ok": ok_n}),))
            conn.commit()
        if ok_n == 0 and BACKUP_URLS:
            raise HTTPException(status_code=502, detail="cả 2 đích backup đều lỗi")
        return {"status": "backed_up", "count": len(rows), "checksum": checksum,
                "targets": results, "targets_ok": ok_n}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── A1: tồn kho theo LÔ (FEFO) + đồng bộ đơn đa kênh ─────────────────────────
GIFT_EXPIRY_WARN_DAYS = 90   # quà tặng gán lô cận hạn hơn ngưỡng này → cảnh báo (ASSUMED)

def _sync_stock(cur, sku: str):
    """products.stock_quantity = SUM(lô) — 1 nguồn sự thật cho SKU quản theo lô."""
    cur.execute("""UPDATE products
                   SET stock_quantity = COALESCE(
                       (SELECT SUM(qty_on_hand) FROM product_lots WHERE sku = %s), 0)
                   WHERE code = %s""", (sku, sku))


@app.post("/lot-insert", status_code=201)
def lot_insert(l: LotInsert):
    """A1: nhập lô kho bán (hàng thương mại nhập tay; lô sản xuất tự vào qua F2)."""
    try:
        lot_code = l.lot_code or f"LOT-{l.sku}-{_date.today().strftime('%y%m%d')}"
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO product_lots (sku, lot_code, expiry_date, qty_on_hand, source, batch_code)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (lot_code) DO NOTHING RETURNING id
                """, (l.sku, lot_code, l.expiry_date, l.qty, l.source, l.batch_code))
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    return {"status": "duplicate", "deduped": True, "lot_code": lot_code}
                _sync_stock(cur, l.sku)
                cur.execute("SELECT stock_quantity FROM products WHERE code=%s", (l.sku,))
                st = cur.fetchone()
            conn.commit()
        return {"status": "inserted", "lot_code": lot_code, "sku": l.sku, "qty": l.qty,
                "expiry_date": l.expiry_date, "stock_after": st[0] if st else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/channel-order-sync", status_code=201)
def channel_order_sync(o: ChannelOrderSync):
    """A1: đơn đa kênh → trừ tồn theo lô FEFO trong 1 transaction (khóa lô chống oversell).
    Bán thường: lô HSD GẦN xuất trước (FEFO). Quà tặng: gán lô HSD XA + cảnh báo nếu cận hạn.
    Thiếu tồn → oversell_blocked, KHÔNG trừ gì (rollback toàn bộ)."""
    try:
        total = round(sum(l.qty * l.price for l in o.items), 2)
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT order_no FROM channel_orders WHERE external_order_id=%s",
                            (o.external_order_id,))
                dup = cur.fetchone()
                if dup:
                    return {"action": "duplicate", "deduped": True, "order_no": dup["order_no"]}

                allocations, touched, min_expiry = [], set(), None
                order_dir = "DESC" if o.is_gift else "ASC"
                for line in o.items:
                    # FOR UPDATE = khóa lô khi đang xử lý (edge case PDF: 2 kênh cùng lô cuối)
                    cur.execute(f"""SELECT lot_code, expiry_date, qty_on_hand FROM product_lots
                                    WHERE sku=%s AND qty_on_hand > 0
                                    ORDER BY expiry_date {order_dir} FOR UPDATE""", (line.sku,))
                    lots = cur.fetchall()
                    remaining = line.qty
                    for lot in lots:
                        if remaining <= 0:
                            break
                        take = min(remaining, lot["qty_on_hand"])
                        allocations.append({"sku": line.sku, "lot_code": lot["lot_code"],
                                            "qty": take, "expiry_date": str(lot["expiry_date"])})
                        exp = lot["expiry_date"]
                        min_expiry = exp if (min_expiry is None or exp < min_expiry) else min_expiry
                        remaining -= take
                    if remaining > 0:
                        conn.rollback()
                        avail = sum(x["qty_on_hand"] for x in lots)
                        return {"action": "oversell_blocked", "sku": line.sku,
                                "need": line.qty, "available": avail,
                                "reason": f"tồn theo lô không đủ: cần {line.qty}, còn {avail}"}

                cur.execute("""
                    INSERT INTO channel_orders (channel, customer_name, items, total_amount,
                                                external_order_id, is_gift)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
                """, (o.channel, o.customer_name,
                      psycopg2.extras.Json([l.model_dump() for l in o.items]),
                      total, o.external_order_id, o.is_gift))
                oid = cur.fetchone()["id"]
                order_no = f"DH{oid}"
                cur.execute("UPDATE channel_orders SET order_no=%s WHERE id=%s", (order_no, oid))
                for a in allocations:
                    cur.execute("""UPDATE product_lots SET qty_on_hand = qty_on_hand - %s
                                   WHERE lot_code=%s""", (a["qty"], a["lot_code"]))
                    cur.execute("""INSERT INTO lot_allocations (order_no, sku, lot_code, qty)
                                   VALUES (%s,%s,%s,%s)""",
                                (order_no, a["sku"], a["lot_code"], a["qty"]))
                    touched.add(a["sku"])
                new_stock = {}
                for sku in touched:
                    _sync_stock(cur, sku)
                    cur.execute("SELECT stock_quantity FROM products WHERE code=%s", (sku,))
                    r = cur.fetchone()
                    new_stock[sku] = r["stock_quantity"] if r else None
                warn_expiry = bool(o.is_gift and min_expiry
                                   and (min_expiry - _date.today()).days < GIFT_EXPIRY_WARN_DAYS)
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('channel_orders', %s, 'sync', %s)""",
                            (order_no, psycopg2.extras.Json(
                                {"channel": o.channel, "external": o.external_order_id,
                                 "allocations": allocations})))
            conn.commit()
            return {"action": "allocated", "order_no": order_no, "channel": o.channel,
                    "total_amount": total, "is_gift": o.is_gift,
                    "allocations": allocations, "new_stock": new_stock,
                    "warn_expiry": warn_expiry}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/channel-delivered", status_code=200)
def channel_delivered(req: ChannelDelivered):
    """A1: đơn sàn giao thành công → mở phát hành HĐĐT (quyết định: sàn chờ delivered)."""
    if not req.external_order_id and not req.order_no:
        raise HTTPException(status_code=400, detail="cần external_order_id hoặc order_no")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""UPDATE channel_orders SET fulfillment_status='delivered'
                               WHERE (order_no=%s OR external_order_id=%s)
                               RETURNING order_no, channel, total_amount""",
                            (req.order_no, req.external_order_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="đơn không tồn tại")
            conn.commit()
        return {"status": "delivered", "order_no": row["order_no"], "channel": row["channel"],
                "total_amount": float(row["total_amount"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stock-snapshot")
def stock_snapshot(skus: Optional[str] = None):
    """A1: tồn theo lô (đồng bộ ngược lên kênh + giám sát HSD)."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if skus:
                    cur.execute("""SELECT sku, lot_code, expiry_date::text, qty_on_hand
                                   FROM product_lots WHERE sku = ANY(%s) ORDER BY sku, expiry_date""",
                                (skus.split(","),))
                else:
                    cur.execute("""SELECT sku, lot_code, expiry_date::text, qty_on_hand
                                   FROM product_lots ORDER BY sku, expiry_date""")
                rows = [dict(r) for r in cur.fetchall()]
        out: dict[str, Any] = {}
        for r in rows:
            out.setdefault(r["sku"], {"stock": 0, "lots": []})
            out[r["sku"]]["stock"] += r["qty_on_hand"]
            out[r["sku"]]["lots"].append(r)
        return {"skus": out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Manuf E2: nhập lô nguyên liệu từ nông hộ/HTX (idempotent theo lot_code) ──
PROCESSING_WINDOW_H = 24     # cửa sổ chế biến giữ cynarin (PDF V2 Manuf, đặc thù #2)
URGENT_UNDER_H = 6           # còn <6h → khẩn cấp đưa vào sản xuất ngay

def _window_status(hours_since: Optional[float], form: str):
    """Trạng thái cửa sổ 24h cho lô TƯƠI (code thuần, không LLM)."""
    if form != "tuoi" or hours_since is None:
        return {"window_status": "n/a", "hours_left": None}
    left = round(PROCESSING_WINDOW_H - hours_since, 1)
    if left <= 0:
        return {"window_status": "overdue", "hours_left": left}
    if left <= URGENT_UNDER_H:
        return {"window_status": "urgent", "hours_left": left}
    return {"window_status": "ok", "hours_left": left}


@app.post("/material-batch-insert", status_code=201)
def material_batch_insert(b: MaterialBatchInsert):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                order_id = None
                if b.order_code:
                    cur.execute("SELECT id FROM production_orders WHERE order_code = %s", (b.order_code,))
                    r = cur.fetchone()
                    order_id = r["id"] if r else None
                cur.execute("""
                    INSERT INTO material_batches
                        (lot_code, farmer, region_grown, part, form, material_code,
                         qty_kg, unit_cost_vnd, harvest_date, gacp_cert, order_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (lot_code) DO NOTHING
                    RETURNING id, harvest_date,
                              EXTRACT(EPOCH FROM (now() - harvest_date))/3600 AS hours_since
                """, (b.lot_code, b.farmer, b.region_grown, b.part, b.form, b.material_code,
                      b.qty_kg, b.unit_cost_vnd, b.harvest_ts, b.gacp_cert, order_id))
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    return {"status": "duplicate", "deduped": True, "lot_code": b.lot_code}
                # Cộng tồn NVL (tươi transient / khô lưu kho)
                cur.execute("""
                    INSERT INTO material_stock (material_code, material_name, qty_on_hand, unit, avg_unit_cost)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (material_code) DO UPDATE
                    SET qty_on_hand = material_stock.qty_on_hand + EXCLUDED.qty_on_hand,
                        avg_unit_cost = EXCLUDED.avg_unit_cost
                """, (b.material_code, b.part, b.qty_kg, "kg", b.unit_cost_vnd))
                # Mua theo đơn → NVL đã về, sẵn sàng sản xuất
                if order_id:
                    cur.execute("""UPDATE material_requirements SET status = 'materials_received'
                                   WHERE order_id = %s""", (order_id,))
                hours = float(row["hours_since"]) if row["hours_since"] is not None else None
                win = _window_status(hours, b.form)
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('material_batches', %s, 'intake', %s)""",
                            (str(row["id"]), psycopg2.extras.Json(
                                {"farmer": b.farmer, "qty_kg": b.qty_kg, **win})))
            conn.commit()
        return {"status": "inserted", "id": row["id"], "lot_code": b.lot_code, "deduped": False,
                "order_linked": order_id is not None,
                "farmer": b.farmer, "material_code": b.material_code, "qty_kg": b.qty_kg,
                "hours_since_harvest": round(hours, 1) if hours is not None else None, **win}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Manuf F1: nhật ký mẻ chế biến + cửa sổ 24h + độ ẩm → HSD ─────────────────
# Quy tắc HSD theo độ ẩm cuối mẻ (ASSUMED — chờ Ngọc Duy xác nhận số thật):
#   ≤7% → 12 tháng; ≤8% → 6 tháng; >8% → CHƯA ĐẠT (sấy tiếp, không chốt mẻ)
MOISTURE_12M = 7.0
MOISTURE_6M = 8.0

@app.post("/process-event", status_code=201)
def process_event(e: ProcessEvent):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if e.event == "start":
                    if not e.order_code:
                        raise HTTPException(status_code=400, detail="start cần order_code")
                    cur.execute("SELECT id FROM production_orders WHERE order_code = %s", (e.order_code,))
                    o = cur.fetchone()
                    if not o:
                        raise HTTPException(status_code=400, detail=f"order_code không tồn tại: {e.order_code}")
                    # Cửa sổ 24h tính từ harvest_date của lô nguyên liệu
                    hours, form = None, "kho"
                    if e.material_lot_code:
                        cur.execute("""SELECT form, EXTRACT(EPOCH FROM (now() - harvest_date))/3600 AS h
                                       FROM material_batches WHERE lot_code = %s""", (e.material_lot_code,))
                        lot = cur.fetchone()
                        if lot:
                            form = lot["form"]
                            hours = float(lot["h"]) if lot["h"] is not None else None
                    win = _window_status(hours, form)
                    cur.execute("""
                        INSERT INTO production_batches
                            (batch_code, order_id, material_lot_code, input_material_kg,
                             shift, source, qc_status)
                        VALUES (%s,%s,%s,%s,%s,%s,'in_progress')
                        ON CONFLICT (batch_code) DO NOTHING
                        RETURNING id
                    """, (e.batch_code, o["id"], e.material_lot_code, e.input_material_kg,
                          e.shift, e.source))
                    r = cur.fetchone()
                    if r is None:
                        conn.commit()
                        return {"status": "duplicate", "deduped": True, "batch_code": e.batch_code}
                    cur.execute("""INSERT INTO batch_process_log (batch_code, stage, operator, note)
                                   VALUES (%s,'start',%s,%s)""",
                                (e.batch_code, e.operator,
                                 f"lot={e.material_lot_code} window={win['window_status']}"))
                    conn.commit()
                    return {"status": "started", "id": r["id"], "batch_code": e.batch_code,
                            "deduped": False,
                            "hours_since_harvest": round(hours, 1) if hours is not None else None, **win}

                if e.event == "stage":
                    if not e.stage:
                        raise HTTPException(status_code=400, detail="stage cần tên công đoạn")
                    cur.execute("""
                        INSERT INTO batch_process_log
                            (batch_code, stage, temp_c, duration_min, moisture_pct, operator, note)
                        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
                    """, (e.batch_code, e.stage, e.temp_c, e.duration_min, e.moisture_pct,
                          e.operator, e.note))
                    lid = cur.fetchone()["id"]
                    conn.commit()
                    return {"status": "logged", "log_id": lid, "stage": e.stage}

                if e.event == "complete":
                    if e.moisture_pct is None:
                        raise HTTPException(status_code=400, detail="complete cần moisture_pct (đo độ ẩm cuối mẻ)")
                    cur.execute("""SELECT b.id, o.product_code FROM production_batches b
                                   JOIN production_orders o ON b.order_id = o.id
                                   WHERE b.batch_code = %s""", (e.batch_code,))
                    b = cur.fetchone()
                    if not b:
                        raise HTTPException(status_code=400, detail=f"batch_code chưa start: {e.batch_code}")
                    # Độ ẩm quyết định HSD (code thuần). Chưa đủ khô → sấy tiếp, KHÔNG chốt mẻ.
                    if e.moisture_pct > MOISTURE_6M:
                        cur.execute("""INSERT INTO batch_process_log (batch_code, stage, moisture_pct, operator, note)
                                       VALUES (%s,'say_lai',%s,%s,'độ ẩm chưa đạt — sấy tiếp')""",
                                    (e.batch_code, e.moisture_pct, e.operator))
                        conn.commit()
                        return {"status": "moisture_fail", "batch_code": e.batch_code,
                                "moisture_pct": e.moisture_pct,
                                "max_allowed": MOISTURE_6M, "action": "sấy tiếp rồi đo lại"}
                    shelf_months = 12 if e.moisture_pct <= MOISTURE_12M else 6
                    cur.execute("SELECT unit_net_kg FROM manuf_products WHERE product_code = %s",
                                (b["product_code"],))
                    mp = cur.fetchone()
                    unit_kg = float(mp["unit_net_kg"]) if mp else 0
                    cur.execute("""
                        UPDATE production_batches
                        SET output_units=%s, ng_units=%s, moisture_pct=%s, unit_weight_kg=%s,
                            expiry_date = CURRENT_DATE + (%s || ' months')::interval,
                            qc_status='pending_lab',
                            material_cost_vnd = CASE WHEN %s > 0 THEN %s ELSE material_cost_vnd END,
                            labor_cost_vnd   = CASE WHEN %s > 0 THEN %s ELSE labor_cost_vnd END
                        WHERE batch_code=%s RETURNING expiry_date
                    """, (e.output_units, e.ng_units, e.moisture_pct, unit_kg, shelf_months,
                          e.material_cost_vnd, e.material_cost_vnd,
                          e.labor_cost_vnd, e.labor_cost_vnd, e.batch_code))
                    exp = cur.fetchone()["expiry_date"]
                    cur.execute("""INSERT INTO batch_process_log (batch_code, stage, moisture_pct, operator, note)
                                   VALUES (%s,'say',%s,%s,%s)""",
                                (e.batch_code, e.moisture_pct, e.operator,
                                 f"đạt — HSD {shelf_months} tháng"))
                    cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                                   VALUES ('production_batches', %s, 'complete', %s)""",
                                (str(b["id"]), psycopg2.extras.Json(
                                    {"moisture_pct": e.moisture_pct, "shelf_months": shelf_months})))
                    conn.commit()
                    return {"status": "completed", "batch_code": e.batch_code,
                            "moisture_pct": e.moisture_pct, "shelf_months": shelf_months,
                            "expiry_date": str(exp), "qc_status": "pending_lab",
                            "note": "chờ kiểm nghiệm dược liệu (F2) trước khi mở bán"}

                raise HTTPException(status_code=400, detail=f"event không hợp lệ: {e.event}")
    except HTTPException:
        raise
    except Exception as e2:
        raise HTTPException(status_code=500, detail=str(e2))


# ── Manuf F2: gate kiểm nghiệm dược liệu — chưa đạt = KHÔNG được bán ─────────
# Ngưỡng chỉ tiêu (ASSUMED theo chuẩn dược liệu — chờ chỉ tiêu thật từ lab/Ngọc Duy):
LAB_CYNARIN_MIN = 2.0    # % hàm lượng dược tính tối thiểu
LAB_MOLD_MAX = 100       # nấm mốc CFU/g

@app.post("/lab-result-insert", status_code=201)
def lab_result_insert(t: LabResultInsert):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""SELECT b.id, b.material_lot_code, b.output_units, b.ng_units,
                                      b.expiry_date, o.product_code
                               FROM production_batches b
                               LEFT JOIN production_orders o ON b.order_id = o.id
                               WHERE b.batch_code = %s""", (t.batch_code,))
                b = cur.fetchone()
                if not b:
                    raise HTTPException(status_code=400, detail=f"batch_code không tồn tại: {t.batch_code}")
                # So chỉ tiêu bằng code thuần (deterministic) — LLM không quyết định gate
                reasons = []
                if t.cynarin_pct < LAB_CYNARIN_MIN:
                    reasons.append(f"cynarin {t.cynarin_pct}% < {LAB_CYNARIN_MIN}%")
                if t.mold_cfu_g >= LAB_MOLD_MAX:
                    reasons.append(f"nấm mốc {t.mold_cfu_g} CFU/g ≥ {LAB_MOLD_MAX}")
                if not t.pesticide_ok:
                    reasons.append("dư lượng BVTV vượt ngưỡng")
                if not t.heavy_metal_ok:
                    reasons.append("kim loại nặng vượt ngưỡng")
                result = "failed" if reasons else "passed"
                cur.execute("""
                    INSERT INTO lab_test_results
                        (batch_code, cynarin_pct, mold_cfu_g, pesticide_ok, heavy_metal_ok,
                         result, reasons, tested_by)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (t.batch_code, t.cynarin_pct, t.mold_cfu_g, t.pesticide_ok,
                      t.heavy_metal_ok, result, psycopg2.extras.Json(reasons), t.tested_by))
                test_id = cur.fetchone()["id"]
                cur.execute("UPDATE production_batches SET qc_status=%s WHERE batch_code=%s",
                            (result, t.batch_code))
                # A1: ĐẠT → TỰ nhập kho bán thành lô (kế thừa HSD từ F1 + traceability về mẻ)
                stocked = None
                if result == "passed" and b["product_code"] and int(b["output_units"] or 0) > 0:
                    cur.execute("""
                        INSERT INTO product_lots (sku, lot_code, expiry_date, qty_on_hand, source, batch_code)
                        VALUES (%s,%s,%s,%s,'production',%s)
                        ON CONFLICT (lot_code) DO NOTHING RETURNING id
                    """, (b["product_code"], t.batch_code, b["expiry_date"],
                          int(b["output_units"]), t.batch_code))
                    if cur.fetchone():
                        _sync_stock(cur, b["product_code"])
                        stocked = {"sku": b["product_code"], "lot_code": t.batch_code,
                                   "qty": int(b["output_units"]),
                                   "expiry_date": str(b["expiry_date"])}
                # Fail → truy xuất về nông hộ/vùng trồng để điều tra
                investigate = None
                if result == "failed" and b["material_lot_code"]:
                    cur.execute("""SELECT farmer, region_grown, part, harvest_date
                                   FROM material_batches WHERE lot_code = %s""",
                                (b["material_lot_code"],))
                    lot = cur.fetchone()
                    if lot:
                        investigate = {"lot_code": b["material_lot_code"], "farmer": lot["farmer"],
                                       "region_grown": lot["region_grown"], "part": lot["part"],
                                       "harvest_date": str(lot["harvest_date"])}
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('lab_test_results', %s, %s, %s)""",
                            (str(test_id), f"lab_{result}",
                             psycopg2.extras.Json({"batch_code": t.batch_code, "reasons": reasons})))
            conn.commit()
        return {"status": result, "test_id": test_id, "batch_code": t.batch_code,
                "reasons": reasons, "sellable": result == "passed",
                "stocked": stocked, "investigate": investigate}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cảnh báo khi yield thực hụt quá X% TƯƠNG ĐỐI so với định mức (ASSUMED 15%)
YIELD_DEVIATION_TOLERANCE_PCT = 15.0

def _compute_report(rows_agg, tolerance: float = YIELD_DEVIATION_TOLERANCE_PCT):
    """Tính deterministic từ số tổng hợp (code thuần — KHÔNG dùng LLM).

    Đặc thù trà/cao atiso: sấy tươi→khô mất 70-95% khối lượng là hao hụt TỰ NHIÊN
    của ngành, KHÔNG phải thất thoát. So yield THỰC với ĐỊNH MỨC (standard_yield),
    chỉ cảnh báo khi hụt quá tolerance — tránh báo động giả (PDF V2 Manuf, phần G2).
    """
    input_kg = float(rows_agg["input_kg"] or 0)
    output_units = int(rows_agg["output_units"] or 0)
    output_kg = float(rows_agg["output_kg"] or 0)
    expected_kg = float(rows_agg["expected_kg"] or 0)
    ng_units = int(rows_agg["ng_units"] or 0)
    cost = float(rows_agg["cost"] or 0)
    revenue = float(rows_agg["revenue"] or 0)
    yield_actual = round(output_kg / input_kg * 100, 2) if input_kg else 0.0
    yield_std = round(expected_kg / input_kg * 100, 2) if input_kg else 0.0
    deviation = round((expected_kg - output_kg) / expected_kg * 100, 2) if expected_kg else 0.0
    ng_pct = round(ng_units / (output_units + ng_units) * 100, 2) if (output_units + ng_units) else 0.0
    profit_pct = round((revenue - cost) / revenue * 100, 2) if revenue else 0.0
    return {"input_kg": input_kg, "output_units": output_units, "output_kg": round(output_kg, 2),
            "expected_output_kg": round(expected_kg, 2), "ng_units": ng_units,
            "cost_vnd": cost, "revenue_vnd": revenue,
            "yield_actual_pct": yield_actual, "yield_std_pct": yield_std,
            "yield_deviation_pct": deviation, "warn_yield": deviation > tolerance,
            "ng_pct": ng_pct, "profit_pct": profit_pct}


# ── QT6: báo cáo lệch định mức (yield) + NG + %lãi theo đơn hoặc ca ──────────
@app.get("/batch-report")
def batch_report(order_code: Optional[str] = None, shift: Optional[str] = None,
                 tolerance: float = YIELD_DEVIATION_TOLERANCE_PCT):
    if not order_code and not shift:
        raise HTTPException(status_code=400, detail="cần order_code hoặc shift")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(b.input_material_kg),0)                AS input_kg,
                           COALESCE(SUM(b.output_units),0)                     AS output_units,
                           COALESCE(SUM(b.output_units * b.unit_weight_kg),0)  AS output_kg,
                           COALESCE(SUM(b.input_material_kg * COALESCE(mp.standard_yield,0)),0) AS expected_kg,
                           COALESCE(SUM(b.ng_units),0)                         AS ng_units,
                           COALESCE(SUM(b.material_cost_vnd + b.labor_cost_vnd),0) AS cost,
                           COALESCE(SUM(b.output_units * o.unit_price),0)      AS revenue
                    FROM production_batches b
                    JOIN production_orders o ON b.order_id = o.id
                    LEFT JOIN manuf_products mp ON mp.product_code = o.product_code
                    WHERE (%s::text IS NULL OR o.order_code = %s)
                      AND (%s::text IS NULL OR b.shift = %s)
                """, (order_code, order_code, shift, shift))
                agg = dict(cur.fetchone())
        rep = _compute_report(agg, tolerance)
        return {"scope": "order" if order_code else "shift", "ref": order_code or shift, **rep}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/production-report-insert", status_code=201)
def production_report_insert(req: ProductionReportInsert):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO production_reports
                        (scope, ref, yield_actual_pct, yield_deviation_pct, ng_pct,
                         cost_vnd, revenue_vnd, profit_pct, ai_explanation)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (req.scope, req.ref, req.yield_actual_pct, req.yield_deviation_pct,
                      req.ng_pct, req.cost_vnd, req.revenue_vnd, req.profit_pct,
                      req.ai_explanation))
                rid = cur.fetchone()[0]
            conn.commit()
        return {"status": "saved", "id": rid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Manuf QT1: tạo lệnh SX từ OCR đơn A (dedup theo order_code) ──────────────
@app.post("/production-order-insert", status_code=201)
def production_order_insert(o: ProductionOrderInsert):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO production_orders
                        (order_code, customer_code, product_code, product_name,
                         qty_ordered, qty_to_produce, unit_price, region, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'draft')
                    ON CONFLICT (order_code) DO NOTHING
                    RETURNING id
                """, (o.order_code, o.customer_code, o.product_code, o.product_name,
                      o.qty_ordered, o.qty_to_produce or o.qty_ordered, o.unit_price, o.region))
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    return {"status": "duplicate", "deduped": True, "order_code": o.order_code}
                oid = row[0]
                cur.execute("""INSERT INTO audit_log (entity, entity_id, action, details)
                               VALUES ('production_orders', %s, 'create_from_ocr', %s)""",
                            (str(oid), psycopg2.extras.Json(
                                {"qty_ordered": o.qty_ordered, "qty_to_produce": o.qty_to_produce,
                                 "deadline": o.deadline})))
            conn.commit()
        return {"status": "created", "id": oid, "order_code": o.order_code,
                "qty_to_produce": o.qty_to_produce or o.qty_ordered, "deduped": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Manuf QT2: sinh DS NVL từ BOM (cần mua = cần dùng − tồn) + số mẻ gợi ý ───
@app.post("/material-requirements-generate", status_code=201)
def material_requirements_generate(body: dict[str, Any]):
    order_code = body.get("order_code")
    if not order_code:
        raise HTTPException(status_code=400, detail="thiếu order_code")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""SELECT id, product_code, COALESCE(qty_to_produce, qty_ordered) AS qty
                               FROM production_orders WHERE order_code = %s""", (order_code,))
                o = cur.fetchone()
                if not o:
                    raise HTTPException(status_code=400, detail=f"order_code không tồn tại: {order_code}")
                qty = int(o["qty"])
                cur.execute("""
                    SELECT b.material_code, b.material_name, b.qty_per_unit, b.unit,
                           b.yield_fresh_to_dry, COALESCE(s.qty_on_hand, 0) AS on_hand
                    FROM bom_materials b LEFT JOIN material_stock s USING (material_code)
                    WHERE b.product_code = %s
                """, (o["product_code"],))
                bom = cur.fetchall()
                if not bom:
                    # SP chưa có BOM → workflow gọi Brain ước lượng rồi POST /material-requirements-insert
                    return {"status": "needs_fallback", "order_code": order_code,
                            "product_code": o["product_code"], "qty": qty}
                # Deterministic — BOM ĐẢO cho dược liệu sấy: cần dùng KHÔ = qty × định mức;
                # thiếu khô = max(0, cần − tồn khô); CẦN MUA TƯƠI = thiếu khô ÷ yield tươi→khô.
                # (bao bì yield=1 → công thức rơi về cần mua = cần − tồn như cũ)
                materials = []
                for m in bom:
                    need = round(qty * float(m["qty_per_unit"]), 3)
                    on_hand = float(m["on_hand"])
                    y = float(m["yield_fresh_to_dry"] or 1)
                    shortfall = max(0, need - on_hand)
                    to_buy = round(shortfall / y, 3) if y > 0 else shortfall
                    materials.append({"material_code": m["material_code"],
                                      "material_name": m["material_name"],
                                      "need": need, "on_hand": on_hand,
                                      "to_buy": to_buy,
                                      "unit": m["unit"],
                                      "buy_unit": "kg tươi" if y < 1 else m["unit"],
                                      "yield_fresh_to_dry": y})
                cur.execute("SELECT batch_output_units FROM manuf_products WHERE product_code = %s",
                            (o["product_code"],))
                mp = cur.fetchone()
                bou = int(mp["batch_output_units"]) if mp else 0
                batches = -(-qty // bou) if bou > 0 else None   # ceil
                cur.execute("""
                    INSERT INTO material_requirements (order_id, materials, estimation_method, batches_suggested)
                    VALUES (%s, %s, 'bom', %s) RETURNING id
                """, (o["id"], psycopg2.extras.Json(materials), batches))
                rid = cur.fetchone()["id"]
            conn.commit()
        return {"status": "generated", "requirement_id": rid, "estimation_method": "bom",
                "batches_suggested": batches, "materials": materials}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/material-requirements-insert", status_code=201)
def material_requirements_insert(req: MaterialReqInsert):
    """Lưu DS NVL do LLM ước lượng (thiếu BOM) — gắn cờ llm_fallback, bắt buộc duyệt tay."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM production_orders WHERE order_code = %s", (req.order_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail=f"order_code không tồn tại: {req.order_code}")
                cur.execute("""
                    INSERT INTO material_requirements (order_id, materials, estimation_method, batches_suggested)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (row[0], psycopg2.extras.Json([m.model_dump() for m in req.materials]),
                      req.estimation_method, req.batches_suggested))
                rid = cur.fetchone()[0]
            conn.commit()
        return {"status": "generated", "requirement_id": rid,
                "estimation_method": req.estimation_method}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT7: báo cáo ĐR (theo kỳ + theo đơn + ngân sách khu vực) ─────────────────
@app.get("/dr-report")
def dr_report(period: str = "month"):
    days = {"day": 1, "week": 7, "month": 30}.get(period, 30)
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                base = """
                    FROM production_batches b JOIN production_orders o ON b.order_id = o.id
                    WHERE b.created_at >= now() - (%s || ' days')::interval
                """
                # Ngân sách khu vực (chi phí + doanh thu + lãi theo region)
                cur.execute("""
                    SELECT o.region,
                           SUM(b.material_cost_vnd + b.labor_cost_vnd) AS cost,
                           SUM(b.output_units * o.unit_price)          AS revenue
                """ + base + " GROUP BY o.region ORDER BY cost DESC", (days,))
                by_region = []
                for r in cur.fetchall():
                    cost = float(r["cost"] or 0); rev = float(r["revenue"] or 0)
                    by_region.append({"region": r["region"], "cost_vnd": cost, "revenue_vnd": rev,
                                      "profit_pct": round((rev - cost) / rev * 100, 2) if rev else 0.0})
                # Lợi nhuận theo từng đơn A
                cur.execute("""
                    SELECT o.order_code,
                           SUM(b.material_cost_vnd + b.labor_cost_vnd) AS cost,
                           SUM(b.output_units * o.unit_price)          AS revenue
                """ + base + " GROUP BY o.order_code ORDER BY o.order_code", (days,))
                by_order = []
                for r in cur.fetchall():
                    cost = float(r["cost"] or 0); rev = float(r["revenue"] or 0)
                    by_order.append({"order_code": r["order_code"], "cost_vnd": cost, "revenue_vnd": rev,
                                     "profit_pct": round((rev - cost) / rev * 100, 2) if rev else 0.0})
                total_cost = sum(x["cost_vnd"] for x in by_region)       # Chi phí B
                total_rev = sum(x["revenue_vnd"] for x in by_region)
        return {"period": period, "chi_phi_B": total_cost, "doanh_thu": total_rev,
                "loi_nhuan": total_rev - total_cost,
                "loi_nhuan_pct": round((total_rev - total_cost) / total_rev * 100, 2) if total_rev else 0.0,
                "ngan_sach_khu_vuc": by_region, "loi_nhuan_theo_don": by_order}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── QT10: competitor prices + alert ──────────────────────────────────────────
@app.post("/competitor-upsert", status_code=201)
def competitor_upsert(batch: CompetitorBatch):
    try:
        alerts = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                for r in batch.rows:
                    cur.execute("""
                        INSERT INTO competitor_prices (sku, product_name, our_price, competitor_price, source)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (r.sku, r.product_name, r.our_price, r.competitor_price, r.source))
                    if r.competitor_price > 0 and r.our_price > r.competitor_price * batch.alert_ratio:
                        alerts.append({"product_name": r.product_name, "our_price": r.our_price,
                                       "competitor_price": r.competitor_price, "source": r.source})
            conn.commit()
        return {"status": "saved", "count": len(batch.rows), "alerts": alerts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
