"""Product CRUD — service layer extracted from main_routes."""
import re
import sqlite3

import pandas as pd

# Từ khoá nhận diện từng field — dùng cho auto-detect
_FIELD_KEYWORDS = {
    'name':           {'tên', 'name', 'product', 'item', 'hàng', 'hang', 'sản', 'san', 'phẩm', 'pham'},
    'code':           {'mã', 'ma', 'code', 'sku', 'barcode', 'id'},
    'category':       {'loại', 'loai', 'nhóm', 'nhom', 'category', 'group', 'type', 'danh'},
    'unit':           {'đơn', 'don', 'vị', 'vi', 'unit', 'uom', 'đvt'},
    'price':          {'giá', 'gia', 'price', 'bán', 'ban', 'lẻ', 'le', 'retail'},
    'stock_quantity': {'tồn', 'ton', 'kho', 'stock', 'qty', 'quantity', 'inventory', 'số', 'so', 'lượng', 'luong'},
    'description':    {'mô', 'mo', 'tả', 'ta', 'description', 'note', 'ghi', 'chú', 'chu', 'desc'},
    'image_url':      {'hình', 'hinh', 'ảnh', 'anh', 'image', 'photo', 'url', 'đại', 'dai', 'diện', 'dien'},
}

# Regex xóa prefix store-code kiểu Sapo: "LC_CN1_", "PL_", v.v.
_PREFIX_RE = re.compile(r'^[a-z0-9]+(?:_[a-z0-9]+)*_')

# Nhãn hiển thị cho từng field
FIELD_LABELS = {
    'name':           'Tên sản phẩm',
    'code':           'Mã sản phẩm',
    'category':       'Danh mục',
    'unit':           'Đơn vị',
    'price':          'Giá bán',
    'stock_quantity': 'Tồn kho',
    'description':    'Mô tả',
    'image_url':      'Hình ảnh (URL)',
}


def _can_access_all(role):
    return role == 'admin'


def _normalize_col(col):
    """Chuẩn hóa 1 tên cột: lower → bỏ * → bỏ prefix store-code."""
    c = str(col).lower().strip().rstrip('*').strip()
    return _PREFIX_RE.sub('', c)


def detect_column_mapping(raw_columns):
    """Đoán field cho từng cột dựa trên token keyword matching.

    Returns list of dicts:
        [{'original': 'Tên sản phẩm*', 'normalized': 'tên sản phẩm',
          'suggested': 'name', 'samples': ['Mì tôm', 'Nước ngọt']}, ...]
    """
    result = []
    used_fields = set()

    scores = []
    normalized_cols = [_normalize_col(c) for c in raw_columns]

    for orig, norm in zip(raw_columns, normalized_cols):
        tokens = set(re.split(r'[\s_\-/()*]+', norm))
        tokens.discard('')
        col_scores = {}
        for field, keywords in _FIELD_KEYWORDS.items():
            score = len(tokens & keywords)
            if score > 0:
                col_scores[field] = score
        scores.append((orig, norm, col_scores))

    assigned = {}
    all_pairs = []
    for orig, norm, col_scores in scores:
        for field, score in col_scores.items():
            all_pairs.append((score, orig, field))
    all_pairs.sort(reverse=True)

    used_cols = set()
    for score, orig, field in all_pairs:
        if orig not in used_cols and field not in used_fields:
            assigned[orig] = field
            used_cols.add(orig)
            used_fields.add(field)

    for orig, norm, _ in scores:
        result.append({
            'original': orig,
            'normalized': norm,
            'suggested': assigned.get(orig),
        })

    return result


def get_all_products(conn, warehouse_id=None, user_id=None, role='user'):
    """List products. If warehouse_id given, stock_quantity reflects that
    warehouse's own stock (from warehouse_stock) instead of the system-wide
    total — 0 if the product has no stock recorded at that warehouse yet."""
    c = conn.cursor()
    scoped = user_id is not None and not _can_access_all(role)
    if warehouse_id:
        query = (
            'SELECT p.id, p.code, p.name, p.category, p.unit, p.price,'
            ' COALESCE(ws.stock_quantity, 0) AS stock_quantity,'
            ' p.description, p.created_at, p.image_url, p.expiry_date'
            ' FROM products p'
            ' LEFT JOIN warehouse_stock ws ON ws.product_id = p.id AND ws.warehouse_id = ?'
        )
        params = [warehouse_id]
        if scoped:
            query += ' WHERE p.created_by = ?'
            params.append(user_id)
        query += ' ORDER BY p.created_at DESC'
        c.execute(query, tuple(params))
    else:
        query = (
            'SELECT id, code, name, category, unit, price, stock_quantity, description, created_at, image_url, expiry_date'
            ' FROM products'
        )
        params = []
        if scoped:
            query += ' WHERE created_by = ?'
            params.append(user_id)
        query += ' ORDER BY created_at DESC'
        c.execute(query, tuple(params))
    rows = c.fetchall()
    return [
        {'id': r['id'], 'code': r['code'], 'name': r['name'], 'category': r['category'],
         'unit': r['unit'], 'price': r['price'], 'stock_quantity': r['stock_quantity'],
         'description': r['description'], 'created_at': r['created_at'], 'image_url': r['image_url'],
         'expiry_date': r['expiry_date']}
        for r in rows
    ]


def create_product(conn, code, name, category, unit, price, stock_quantity, description, created_by,
                    image_url='', expiry_date=None):
    c = conn.cursor()
    try:
        c.execute(
            '''INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by, image_url, expiry_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (code, name, category, unit, price, stock_quantity, description, created_by, image_url or None, expiry_date or None),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, 'Product code already exists'
    except Exception:
        conn.rollback()
        raise


def update_product(conn, product_id, name, category, unit, price, stock_quantity,
                   description, image_url='', user_id=None, role='user', expiry_date=None):
    c = conn.cursor()
    try:
        query = '''UPDATE products SET name=?, category=?, unit=?, price=?, stock_quantity=?,
               description=?, image_url=?, expiry_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'''
        params = [name, category, unit, price, stock_quantity, description, image_url or None, expiry_date or None, product_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by=?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Product not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def delete_product(conn, product_id, user_id=None, role='user'):
    c = conn.cursor()
    try:
        query = 'DELETE FROM products WHERE id=?'
        params = [product_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by=?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Product not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _get_next_sp_number(cursor):
    """Lấy số thứ tự tiếp theo cho mã SP (ví dụ: SP007 → trả về 8)."""
    cursor.execute("SELECT code FROM products WHERE code LIKE 'SP%'")
    numbers = []
    for (code,) in cursor.fetchall():
        try:
            numbers.append(int(code[2:]))
        except (ValueError, IndexError):
            pass
    return max(numbers, default=0) + 1


def import_products_from_excel(conn, file_storage, created_by, column_map=None):
    """Upsert products from an uploaded Excel file.

    column_map: dict {tên_cột_gốc: field_name} do user xác nhận.
                Nếu None thì dùng auto-detect.

    Returns dict: {inserted, updated, skipped, errors}

    Performance: loads existing products once into memory, then bulk-executes
    inserts and updates — O(4 queries) regardless of file size.
    """
    try:
        df = pd.read_excel(file_storage, engine='openpyxl')
    except Exception as e:
        raise ValueError(f'Không đọc được file Excel: {e}')

    MAX_ROWS = 2000
    if len(df) > MAX_ROWS:
        raise ValueError(
            f'File có {len(df):,} dòng, vượt giới hạn {MAX_ROWS:,} sản phẩm/lần import. '
            f'Vui lòng chia nhỏ file thành nhiều phần và import từng phần.'
        )

    df.columns = [str(c).strip() for c in df.columns]

    if column_map:
        rename = {k: v for k, v in column_map.items() if v}
        df.rename(columns=rename, inplace=True)
    else:
        mapping = detect_column_mapping(list(df.columns))
        rename = {m['original']: m['suggested'] for m in mapping if m['suggested']}
        df.rename(columns=rename, inplace=True)

    if 'name' not in df.columns:
        raise ValueError("Không tìm thấy cột tên sản phẩm. Vui lòng xác nhận lại mapping.")

    result = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': []}

    c = conn.cursor()
    try:
        # ── Bước 1: Load toàn bộ sản phẩm hiện có vào memory (1 query) ──────
        c.execute('SELECT id, code, name FROM products WHERE created_by = ?', (created_by,))
        existing_by_code = {}
        existing_by_name = {}
        for pid, pcode, pname in c.fetchall():
            if pcode:
                existing_by_code[pcode.strip()] = (pid, pcode.strip())
            if pname:
                existing_by_name[pname.strip().lower()] = (pid, pcode.strip() if pcode else '')

        next_sp_num = _get_next_sp_number(c)

        # ── Bước 2: Phân loại từng dòng trong Python (không query DB) ────────
        to_update = []
        to_insert = []

        for i, row in df.iterrows():
            row_num = i + 2

            name = str(row.get('name', '')).strip()
            if not name or name == 'nan':
                result['skipped'] += 1
                continue

            try:
                code_val    = str(row['code']).strip() if 'code' in row and pd.notna(row['code']) else ''
                category    = str(row['category']).strip() if 'category' in row and pd.notna(row['category']) else ''
                unit        = str(row['unit']).strip() if 'unit' in row and pd.notna(row['unit']) else 'cái'
                price       = float(row['price']) if 'price' in row and pd.notna(row['price']) else 0.0
                stock       = int(float(row['stock_quantity'])) if 'stock_quantity' in row and pd.notna(row['stock_quantity']) else 0
                description = str(row['description']).strip() if 'description' in row and pd.notna(row['description']) else ''
                image_url   = str(row['image_url']).strip() if 'image_url' in row and pd.notna(row['image_url']) else ''
            except (ValueError, TypeError) as e:
                result['errors'].append(f'Dòng {row_num}: Giá trị không hợp lệ — {e}')
                result['skipped'] += 1
                continue

            existing_rec = existing_by_code.get(code_val) if code_val else None
            if existing_rec is None:
                existing_rec = existing_by_name.get(name.lower())

            if existing_rec:
                existing_id, existing_code = existing_rec
                final_code = code_val or existing_code
                if not final_code:
                    final_code = f'SP{next_sp_num:03d}'
                    next_sp_num += 1
                to_update.append((final_code, name, category, unit, price, stock,
                                  description, image_url or None, existing_id))
                existing_by_name[name.lower()] = (existing_id, final_code)
                if final_code:
                    existing_by_code[final_code] = (existing_id, final_code)
                result['updated'] += 1
            else:
                final_code = code_val or f'SP{next_sp_num:03d}'
                if not code_val:
                    next_sp_num += 1
                to_insert.append((final_code, name, category, unit, price, stock,
                                  description, created_by, image_url or None))
                existing_by_name[name.lower()] = (None, final_code)
                if final_code:
                    existing_by_code[final_code] = (None, final_code)
                result['inserted'] += 1

        # ── Bước 3: Bulk execute ──────────────────────────────────────────────
        if to_update:
            c.executemany(
                '''UPDATE products SET code=?, name=?, category=?, unit=?, price=?,
                   stock_quantity=?, description=?, image_url=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?''',
                to_update,
            )

        if to_insert:
            c.executemany(
                '''INSERT INTO products (code, name, category, unit, price, stock_quantity,
                   description, created_by, image_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                to_insert,
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return result
