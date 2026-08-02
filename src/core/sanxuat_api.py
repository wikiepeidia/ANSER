"""
src/core/sanxuat_api.py — Tra cứu dữ liệu sản xuất trực tiếp từ Postgres của
San Xuất (`SANXUAT_POSTGRES_URL`).

Kết nối trực tiếp, chỉ đọc (SELECT), mô phỏng CHÍNH XÁC pattern đã chứng minh
của `saas_api.py::SaasAPI` (per 12-CONTEXT.md's "SanXuatAPI: Direct Read-Only
Postgres Connection" decision). Không method nào ở đây INSERT/UPDATE/DELETE.

⚠️ SCHEMA MAP (ngay dưới): tên bảng/cột PHẢI khớp core/sanxuat_db.py bên
   nhánh anser-san-xuat. Nếu schema đổi, CHỈ sửa khối hằng số dưới đây.

`SANXUAT_POSTGRES_URL` là biến môi trường KHÁC `DATABASE_URL` (biến của
Retail's `Config.DB_URL`) — đọc trực tiếp qua `os.getenv` ở đây, KHÔNG import
`Config`, vì `Config` là lớp cấu hình riêng của Retail và fail-fast ở thời
điểm khởi tạo class nếu thiếu biến môi trường của nó.
"""
import json
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# =====================================================================
# SCHEMA MAP — đối chiếu với core/sanxuat_db.py (nhánh anser-san-xuat)
# =====================================================================
PRODUCTION_ORDERS_TABLE = "production_orders"
MATERIAL_BATCHES_TABLE = "material_batches"
BOM_LINES_TABLE = "bom_lines"
PRODUCTS_TABLE = "products"
# =====================================================================


def _normalize_pg_url(raw_url: str) -> str:
    """
    Áp dụng đúng cách rewrite `postgres://`/`postgresql://` ->
    `postgresql+psycopg2://` mà `Config.DB_URL` dùng cho `DATABASE_URL` —
    lặp lại ở đây vì `SANXUAT_POSTGRES_URL` là biến môi trường khác, đọc
    trực tiếp, không đi qua `Config`.
    """
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


class SanXuatAPI:
    """Kết nối trực tiếp, chỉ đọc tới Postgres sản xuất của San Xuất."""

    def __init__(self):
        raw_url = os.getenv("SANXUAT_POSTGRES_URL", "")
        if not raw_url:
            logger.error(
                "SANXUAT_POSTGRES_URL chưa được thiết lập -- SanXuatAPI sẽ "
                "trả lỗi thân thiện thay vì crash"
            )
            self.engine = None
            return
        try:
            self.engine = create_engine(_normalize_pg_url(raw_url))
        except Exception:
            logger.error("Không thể khởi tạo kết nối CSDL San Xuất", exc_info=True)
            self.engine = None

    def _require_engine(self):
        if not self.engine:
            raise RuntimeError("Kết nối CSDL San Xuất chưa sẵn sàng")

    def lookup_production_order(self, query, limit=20):
        self._require_engine()
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT code, product_code, product_name, quantity, unit, status
                    FROM {PRODUCTION_ORDERS_TABLE}
                    WHERE is_deleted = FALSE
                      AND (code ILIKE :q OR product_name ILIKE :q OR product_code ILIKE :q)
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                rows = conn.execute(sql, {"q": f"%{query}%", "limit": limit}).fetchall()

                if not rows:
                    return f"Không tìm thấy lệnh sản xuất khớp '{query}'."

                results = []
                for r in rows:
                    results.append({
                        "code": r[0],
                        "product_code": r[1],
                        "product_name": r[2],
                        "quantity": r[3],
                        "unit": r[4],
                        "status": r[5],
                    })
                return json.dumps(results, ensure_ascii=False, indent=2)
        except SQLAlchemyError:
            logger.error(
                "Lỗi truy vấn lệnh sản xuất query='%s'", query, exc_info=True,
            )
            return f"Lỗi hệ thống khi tra cứu lệnh sản xuất '{query}'."

    def get_material_batch_status(self, query, limit=20):
        self._require_engine()
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT batch_code, material_code, material_name, quantity,
                           import_date, expiry_date, qc_status
                    FROM {MATERIAL_BATCHES_TABLE}
                    WHERE is_deleted = FALSE
                      AND (material_name ILIKE :q OR material_code ILIKE :q OR batch_code ILIKE :q)
                    ORDER BY import_date DESC
                    LIMIT :limit
                """)
                rows = conn.execute(sql, {"q": f"%{query}%", "limit": limit}).fetchall()

                if not rows:
                    return f"Không tìm thấy lô nguyên liệu khớp '{query}'."

                results = []
                for r in rows:
                    results.append({
                        "batch_code": r[0],
                        "material_code": r[1],
                        "material_name": r[2],
                        "quantity": r[3],
                        "import_date": str(r[4]) if r[4] is not None else None,
                        "expiry_date": str(r[5]) if r[5] is not None else None,
                        "qc_status": r[6],
                    })
                return json.dumps(results, ensure_ascii=False, indent=2)
        except SQLAlchemyError:
            logger.error(
                "Lỗi truy vấn lô nguyên liệu query='%s'", query, exc_info=True,
            )
            return f"Lỗi hệ thống khi tra cứu lô nguyên liệu '{query}'."

    def get_bom_for_product(self, product_code):
        self._require_engine()
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT code, name, unit, unit_cost, qty_per_unit
                    FROM {BOM_LINES_TABLE}
                    WHERE product_code = :pc
                """)
                rows = conn.execute(sql, {"pc": product_code}).fetchall()

                if not rows:
                    return (
                        f"Không tìm thấy định mức nguyên liệu (BOM) cho "
                        f"sản phẩm '{product_code}'."
                    )

                lines = []
                total_unit_cost = 0
                for r in rows:
                    lines.append({
                        "code": r[0],
                        "name": r[1],
                        "unit": r[2],
                        "unit_cost": r[3],
                        "qty_per_unit": r[4],
                    })
                    total_unit_cost += (r[3] or 0) * (r[4] or 0)

                return json.dumps({
                    "lines": lines,
                    "estimated_unit_cost": round(total_unit_cost, 2),
                }, ensure_ascii=False, indent=2)
        except SQLAlchemyError:
            logger.error(
                "Lỗi truy vấn BOM product_code='%s'", product_code, exc_info=True,
            )
            return f"Lỗi hệ thống khi tra cứu định mức nguyên liệu '{product_code}'."

    def infer_qty_to_produce(self, items):
        """
        Ước tính `qty_to_produce` theo công thức đã chốt ở 12-CONTEXT.md:
        `qty_to_produce = max(0, ordered_qty - current_available_stock)`,
        dùng `products.stock_quantity` thật (per `products.code` — cột này
        dùng chung cho cả thành phẩm lẫn nguyên liệu-mô-hình-hoá-như-sản-phẩm,
        theo `routes/inventory_routes.py::_resolve_material_product`).

        Khi không đọc được tồn kho thật (thiếu engine, sku không có trong
        `products`, hoặc lỗi truy vấn), method này lùi về đúng hành vi
        naive-passthrough của mock (`routes/n8n_api.py::internal_brain_chat`:
        `it.get("qty") or 0`) -- không bao giờ tệ hơn mock nó thay thế. Một
        lookup lỗi chỉ ảnh hưởng đúng item đó, không huỷ cả batch.
        """
        results = []
        for it in (items or []):
            if not isinstance(it, dict):
                continue
            sku = it.get("sku")
            ordered_qty = it.get("qty") or 0
            qty_to_produce = ordered_qty  # fallback/naive passthrough, set first

            if self.engine and sku:
                try:
                    with self.engine.connect() as conn:
                        sql = text(f"SELECT stock_quantity FROM {PRODUCTS_TABLE} WHERE code = :code")
                        row = conn.execute(sql, {"code": sku}).fetchone()
                        current_stock = row[0] if row and row[0] is not None else 0
                        qty_to_produce = max(0, ordered_qty - current_stock)
                except SQLAlchemyError:
                    logger.warning(
                        "Lỗi tra cứu tồn kho sku=%s -- dùng SL đặt làm SL cần SX",
                        sku, exc_info=True,
                    )
                    # qty_to_produce stays at its fallback value (ordered_qty)

            results.append({"sku": sku, "qty_to_produce": qty_to_produce})
        return results
