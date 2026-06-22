import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import chromadb
import psycopg2
import psycopg2.extras

app = FastAPI(title="RAG + DB Service")

# ChromaDB
client = chromadb.HttpClient(host="chromadb", port=8000)

# NeonDB — loaded from env injected by docker-compose
POSTGRES_URL = os.environ.get("POSTGRES_URL", "")


def get_conn():
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


# ── RAG endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

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
    col = client.get_or_create_collection(
        req.collection, metadata={"hnsw:space": "cosine"}
    )
    col.add(
        ids=req.ids,
        documents=req.documents,
        metadatas=[{"source": "mitre_attck"} for _ in req.documents],
    )
    return {"status": "ok", "count": len(req.documents)}


# ── IoT DB endpoint ───────────────────────────────────────────────────────────

@app.post("/iot-insert", status_code=201)
def iot_insert(event: IoTEventRequest):
    """Insert one IoT event into iot_events (NeonDB). Called by n8n Code node."""
    if not POSTGRES_URL:
        raise HTTPException(status_code=500, detail="POSTGRES_URL not configured")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO iot_events (device_id, event_type, payload)
                    VALUES (%s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (event.device_id, event.event_type,
                     psycopg2.extras.Json(event.payload)),
                )
                row = cur.fetchone()
            conn.commit()
        return {"status": "inserted", "id": row[0], "created_at": str(row[1])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Sales Report endpoint ────────────────────────────────────────────────────

@app.get("/daily-sales")
def daily_sales(date: Optional[str] = None):
    """Get sales summary for a given date (default: today)."""
    if not POSTGRES_URL:
        raise HTTPException(status_code=500, detail="POSTGRES_URL not configured")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                date_filter = f"'{date}'" if date else "CURRENT_DATE"
                cur.execute(f"""
                    SELECT
                        COUNT(*)                       AS total_orders,
                        COALESCE(SUM(total_amount), 0) AS total_revenue,
                        COUNT(DISTINCT user_id)        AS unique_staff
                    FROM sales
                    WHERE created_at::date = {date_filter}
                """)
                summary = dict(cur.fetchone())
                summary['total_revenue'] = float(summary['total_revenue'])

                cur.execute(f"""
                    SELECT item->>'name' AS product_name,
                           SUM((item->>'qty')::int) AS qty_sold,
                           SUM((item->>'price')::numeric * (item->>'qty')::int) AS revenue
                    FROM sales,
                         jsonb_array_elements(items::jsonb) AS item
                    WHERE created_at::date = {date_filter}
                    GROUP BY item->>'name'
                    ORDER BY revenue DESC
                    LIMIT 5
                """)
                top_products = [dict(r) for r in cur.fetchall()]
                for p in top_products:
                    p['revenue'] = float(p['revenue'])

        return {"date": date or "today", "summary": summary, "top_products": top_products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Low Stock endpoint ───────────────────────────────────────────────────────

@app.get("/low-stock")
def low_stock(threshold: int = 10):
    """Return products with quantity below threshold."""
    if not POSTGRES_URL:
        raise HTTPException(status_code=500, detail="POSTGRES_URL not configured")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, code, stock_quantity, price, category
                    FROM products
                    WHERE stock_quantity < %s
                    ORDER BY stock_quantity ASC
                """, (threshold,))
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    it['price'] = float(it['price']) if it.get('price') else 0
        return {"threshold": threshold, "count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Customer Insert endpoint ─────────────────────────────────────────────────

class NewCustomerRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

@app.post("/customer-insert", status_code=201)
def customer_insert(req: NewCustomerRequest):
    """Insert a new customer and return the record."""
    if not POSTGRES_URL:
        raise HTTPException(status_code=500, detail="POSTGRES_URL not configured")
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM customers")
                next_id = cur.fetchone()['coalesce']
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
