import json
import logging
from sqlalchemy import create_engine, text
from src.core.config import Config

logger = logging.getLogger(__name__)

class SaasAPI:
    def __init__(self):
        self.config = Config()
        self.engine = create_engine(self.config.DB_URL)

    def lookup_product(self, query, workspace_id=1):
        """
        Maps AI 'Product Search' -> Project 'Items' Table.
        """
        with self.engine.connect() as conn:
            # Search in 'items' where type is 'product' (or default item)
            # We assume 'metadata' column holds JSON like {"price": 100, "stock": 10}
            sql = text("""
                SELECT id, title, description, metadata 
                FROM items 
                WHERE workspace_id = :ws_id 
                AND title ILIKE :query
            """)
            
            rows = conn.execute(sql, {"ws_id": workspace_id, "query": f"%{query}%"}).fetchall()
            
            if not rows:
                return f"❌ Không tìm thấy sản phẩm '{query}' trong kho."
            
            results = []
            for r in rows:
                # Parse Metadata safely
                price = "N/A"
                stock = "N/A"
                try:
                    if r[3]: # metadata column
                        meta = json.loads(r[3])
                        price = f"{meta.get('price', 0):,} VND"
                        stock = meta.get('stock', 0)
                except (TypeError, json.JSONDecodeError) as exc:
                    logger.warning("Failed parsing product metadata for item_id=%s: %s", r[0], exc)
                
                results.append({
                    "id": r[0],
                    "name": r[1],
                    "price": price,
                    "stock": stock,
                    "desc": r[2]
                })
                
            return json.dumps(results, ensure_ascii=False, indent=2)

    def get_sales_report(self, workspace_id=1, period="today"):
        """
        Queries the new 'sales' table.
        """
        with self.engine.connect() as conn:
            # Simple Today query (Postgres syntax)
            sql = text("""
                SELECT SUM(amount), COUNT(*) 
                FROM sales 
                WHERE workspace_id = :ws_id 
                AND date(date) = CURRENT_DATE
            """)
            
            res = conn.execute(sql, {"ws_id": workspace_id}).fetchone()
            
            revenue = res[0] if res[0] else 0
            orders = res[1] if res[1] else 0
            
            return {"revenue": f"{revenue:,.0f} VND", "orders": orders}
            
    def update_price(self, product_name, new_price, workspace_id=1):
        """Updates price inside the metadata JSON of the items table."""
        with self.engine.connect() as conn:
            # 1. Find Item
            sql_find = text("SELECT id, metadata FROM items WHERE title ILIKE :name AND workspace_id = :ws_id LIMIT 1")
            item = conn.execute(sql_find, {"name": f"%{product_name}%", "ws_id": workspace_id}).fetchone()
            
            if not item: return "❌ Item not found."
            
            # 2. Update JSON
            try:
                meta = json.loads(item[1]) if item[1] else {}
                old_price = meta.get('price', 0)
                meta['price'] = float(new_price)
                
                # 3. Save back
                sql_update = text("UPDATE items SET metadata = :meta WHERE id = :id")
                conn.execute(sql_update, {"meta": json.dumps(meta), "id": item[0]})
                conn.commit()
                
                return f"✅ Updated '{product_name}'. Price: {old_price} -> {new_price}"
            except Exception as e:
                return f"❌ Error updating metadata: {e}"