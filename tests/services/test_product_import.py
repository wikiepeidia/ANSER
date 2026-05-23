"""Unit tests for import_products_from_excel service function."""

import io
import pytest
import openpyxl

import core.services.product_service as product_service


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_excel(rows, headers=None):
    """Build an in-memory .xlsx file with given headers and rows."""
    if headers is None:
        headers = ['code', 'name', 'category', 'unit', 'price', 'stock_quantity']
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf


class _CursorStub:
    def __init__(self, existing_products=None):
        # existing_products: list of (id, code, name) tuples already in DB
        self._existing_products = existing_products or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        return self

    def executemany(self, query, params_list):
        for p in params_list:
            self.executed.append((query, p))

    def fetchone(self):
        return None

    def fetchall(self):
        last_query = self.executed[-1][0] if self.executed else ''
        if 'SELECT id, code, name FROM products' in last_query:
            return self._existing_products
        return []

    def close(self):
        pass


class _ConnStub:
    def __init__(self, existing_products=None):
        self.cursor_obj = _CursorStub(existing_products)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


# ── Tests ──────────────────────────────────────────────────────────────────

def test_import_inserts_new_products():
    """Sản phẩm chưa có trong DB phải được INSERT với code tự động."""
    conn = _ConnStub()
    file = _make_excel([
        ['SP001', 'Mì tôm', 'Thực phẩm', 'Thùng', 85000, 100],
        ['SP002', 'Nước ngọt', 'Đồ uống', 'Két', 120000, 50],
    ])

    result = product_service.import_products_from_excel(conn, file, created_by=1)

    assert result['inserted'] == 2
    assert result['updated'] == 0
    assert result['skipped'] == 0
    assert result['errors'] == []
    assert conn.committed is True


def test_import_updates_existing_product():
    """Sản phẩm trùng CODE trong DB phải được UPDATE, giữ nguyên code DB."""
    conn = _ConnStub(existing_products=[(1, 'SP001', 'Mì tôm')])
    file = _make_excel([
        ['SP001', 'Mì tôm', 'Thực phẩm', 'Thùng', 90000, 200],
    ])

    result = product_service.import_products_from_excel(conn, file, created_by=1)

    assert result['inserted'] == 0
    assert result['updated'] == 1
    assert result['skipped'] == 0

    queries = [q for q, _ in conn.cursor_obj.executed]
    assert any('UPDATE products' in q for q in queries)


def test_import_skips_empty_name_rows():
    """Dòng không có name phải bị bỏ qua."""
    conn = _ConnStub()
    file = _make_excel([
        ['SP001', 'Mì tôm', 'Thực phẩm', 'Thùng', 85000, 100],
        ['SP002', '',       '',           '',       0,      0  ],  # name rỗng
        ['SP003', None,     '',           '',       0,      0  ],  # name None
    ])

    result = product_service.import_products_from_excel(conn, file, created_by=1)

    assert result['inserted'] == 1
    assert result['skipped'] == 2


def test_import_handles_invalid_price():
    """Dòng có price không phải số phải vào errors, không crash."""
    conn = _ConnStub()
    file = _make_excel([
        ['SP001', 'Mì tôm', 'Thực phẩm', 'Thùng', 'không_phải_số', 100],
    ])

    result = product_service.import_products_from_excel(conn, file, created_by=1)

    assert result['skipped'] == 1
    assert len(result['errors']) == 1
    assert 'Dòng 2' in result['errors'][0]


def test_import_raises_on_missing_name_column():
    """File thiếu cột name phải raise ValueError ngay."""
    conn = _ConnStub()
    file = _make_excel(
        [['SP001', 85000]],
        headers=['code', 'price'],  # không có 'name'
    )

    with pytest.raises(ValueError, match="cột tên sản phẩm"):
        product_service.import_products_from_excel(conn, file, created_by=1)


def test_import_no_code_auto_assigns_sp_code():
    """Sản phẩm mới không có trong DB phải được gán code SP tự động."""
    conn = _ConnStub()
    file = _make_excel(
        [['Sản phẩm mới', 'Thực phẩm', 85000, 100]],
        headers=['name', 'category', 'price', 'stock_quantity'],
    )

    result = product_service.import_products_from_excel(conn, file, created_by=1)

    assert result['inserted'] == 1
    # Phải có INSERT với code SP dạng SPxxx
    queries_params = [(q, p) for q, p in conn.cursor_obj.executed if 'INSERT INTO products' in q]
    assert len(queries_params) == 1
    inserted_code = queries_params[0][1][0]
    assert inserted_code.startswith('SP')
