"""Material batch routes — real backend for material batches + supplier
auto-resolution.

Replaces the localStorage mock in static/js/store.js (Material Batches +
Traceability section, materialBatches array / createBatch / traceBatch /
getExpiringBatches). See .planning/phases/02-material-batches-warehouses-
traceability-suppliers/02-RESEARCH.md for the locked resolution contract
this file implements (Pattern 6 _resolve_supplier, Pattern 7
MATERIALS_CATALOG, Pattern 5 traceability-chain JOIN).
"""
import secrets
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.auth import require_role
from core.sanxuat_db import get_connection, now
from routes.production_routes import _serialize_order

inventory_bp = Blueprint('inventory', __name__)

# Server-side source of truth for material reference data, mirrored in
# static/js/store.js (_MOCK_MATERIALS). A POST/PUT body's materialCode is
# resolved against this list; materialName/unit are never trusted from the
# client. NVL-008 is the first herbal raw material used by the real
# manufacturing OCR intake path (Phase 13).
MATERIALS_CATALOG = [
    {'code': 'NVL-001', 'name': 'Vải cotton', 'unit': 'm', 'unitCost': 45000},
    {'code': 'NVL-002', 'name': 'Chỉ may', 'unit': 'cuộn', 'unitCost': 8000},
    {'code': 'NVL-003', 'name': 'Khuy nhựa', 'unit': 'cái', 'unitCost': 500},
    {'code': 'NVL-004', 'name': 'Nhãn mác', 'unit': 'cái', 'unitCost': 1200},
    {'code': 'NVL-005', 'name': 'Bao bì đóng gói', 'unit': 'cái', 'unitCost': 2500},
    {'code': 'NVL-006', 'name': 'Keo dán công nghiệp', 'unit': 'kg', 'unitCost': 60000},
    {'code': 'NVL-007', 'name': 'Dây kéo', 'unit': 'cái', 'unitCost': 3000},
    {'code': 'NVL-008', 'name': 'Lá Atiso tươi', 'unit': 'kg', 'unitCost': 12000},
]


def _find_material(code):
    for m in MATERIALS_CATALOG:
        if m['code'] == code:
            return m
    return None


def _resolve_supplier(conn, name, user_id):
    """Resolve a free-text supplier name into a real suppliers.id, matching
    by trimmed/case-insensitive name or auto-creating a placeholder-coded
    row (NCC-PENDING-{hex}) if nothing matches. Empty/missing name -> None
    (no auto-create for an empty string). Called only from this file's
    create/update batch routes — routes/supplier_routes.py's own supplier
    CRUD (02-04) always creates suppliers directly with a real NCC-{id}
    code, never through this resolver.

    The placeholder code is intentionally kept as-is (NOT converted to a
    real NCC-{id} code, unlike the id-derived code convention used
    elsewhere in this app) — per T-02-05 in this plan's threat model, it
    must stay visibly flagged as auto-created/unverified until a human
    corrects it via 02-04's real supplier CRUD.
    """
    name = (name or '').strip()
    if not name:
        return None
    row = conn.execute(
        'SELECT id FROM suppliers WHERE LOWER(TRIM(name)) = LOWER(?) AND is_deleted = FALSE',
        (name,),
    ).fetchone()
    if row:
        return row['id']
    placeholder_code = f'NCC-PENDING-{secrets.token_hex(2).upper()}'
    cur = conn.execute(
        'INSERT INTO suppliers (code, name, created_by, created_at) VALUES (?, ?, ?, ?)',
        (placeholder_code, name, user_id, now()),
    )
    return cur.lastrowid


def _resolve_material_product(conn, material, user_id):
    """Resolve a MATERIALS_CATALOG material into a real products.id (NVL is
    modeled as a product too, per material_batches.material_product_id),
    auto-creating it on first use -- same find-or-create shape as
    _resolve_supplier above."""
    row = conn.execute('SELECT id FROM products WHERE code = ?', (material['code'],)).fetchone()
    if row:
        return row['id']
    cur = conn.execute(
        'INSERT INTO products (code, name, unit, created_by, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (material['code'], material['name'], material['unit'], user_id, now(), now()),
    )
    return cur.lastrowid


def _serialize_batch(row):
    return {
        'id': row['id'],
        'code': row['batch_code'],
        'materialCode': row['material_code'],
        'materialName': row['material_name'],
        'materialProductId': row['material_product_id'],
        'unit': row['unit'],
        'supplierId': row['supplier_id'],
        'supplierName': row['supplier_name'] or '',
        'quantity': row['quantity'],
        'receivedAt': row['import_date'],
        'expiryDate': row['expiry_date'] or '',
        'qcStatus': row['qc_status'],
        'qcNote': row['qc_note'] or '',
        'locationId': row['location_id'],
        'notes': row['notes'] or '',
    }


# Shared base query for every route that reads material_batches — always
# LEFT JOINs suppliers to populate supplierName, and deliberately never
# filters suppliers.is_deleted in the JOIN condition (Pitfall 3): a batch
# referencing a later-soft-deleted supplier must still show its name.
_BATCH_SELECT = (
    'SELECT b.*, s.name AS supplier_name FROM material_batches b '
    'LEFT JOIN suppliers s ON s.id = b.supplier_id'
)


def _validate_batch_payload(data):
    """Shared create/update validation. Returns (material_dict, quantity,
    None) on success, or (None, None, (body, status)) on failure."""
    material_code = data.get('materialCode')
    if not material_code:
        return None, None, ({'success': False, 'message': 'Thiếu mã nguyên vật liệu'}, 400)
    material = _find_material(material_code)
    if not material:
        return None, None, ({'success': False, 'message': 'Mã nguyên vật liệu không hợp lệ'}, 400)
    try:
        quantity = float(data.get('quantity') or 0)
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return None, None, ({'success': False, 'message': 'Số lượng phải lớn hơn 0'}, 400)
    return material, quantity, None


# ── Material Batches CRUD (TRACE-01) ─────────────────────────────────────

@inventory_bp.route('/api/material-batches', methods=['GET'])
@login_required
def get_material_batches():
    conn = get_connection()
    try:
        rows = conn.execute(
            f'{_BATCH_SELECT} WHERE b.is_deleted = FALSE ORDER BY b.import_date DESC'
        ).fetchall()
        return jsonify({'success': True, 'batches': [_serialize_batch(r) for r in rows]})
    finally:
        conn.close()


@inventory_bp.route('/api/material-batches', methods=['POST'])
@login_required
def create_material_batch():
    data = request.get_json(silent=True) or {}
    material, quantity, error = _validate_batch_payload(data)
    if error:
        body, status = error
        return jsonify(body), status

    conn = get_connection()
    try:
        supplier_id = _resolve_supplier(conn, data.get('supplierName'), current_user.id)
        material_product_id = _resolve_material_product(conn, material, current_user.id)
        location_id = data.get('locationId')
        cur = conn.execute(
            'INSERT INTO material_batches (material_code, material_name, material_product_id, '
            'unit, supplier_id, quantity, expiry_date, notes, location_id, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (material['code'], material['name'], material_product_id, material['unit'], supplier_id,
             quantity, data.get('expiryDate') or '', data.get('notes', ''), location_id,
             current_user.id, now()),
        )
        batch_id = cur.lastrowid
        code = f'LO-{2000 + batch_id}'
        conn.execute('UPDATE material_batches SET batch_code = ? WHERE id = ?', (code, batch_id))
        conn.commit()
        return jsonify({'success': True, 'id': batch_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@inventory_bp.route('/api/material-batches/<int:batch_id>', methods=['GET'])
@login_required
def get_material_batch(batch_id):
    conn = get_connection()
    try:
        # No is_deleted filter here (Pitfall 2) — only the list endpoint
        # filters; a soft-deleted batch must remain individually queryable
        # for historical traceability (TRACE-02).
        row = conn.execute(f'{_BATCH_SELECT} WHERE b.id = ?', (batch_id,)).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404
        return jsonify({'success': True, 'batch': _serialize_batch(row)})
    finally:
        conn.close()


@inventory_bp.route('/api/material-batches/<int:batch_id>', methods=['PUT'])
@login_required
def update_material_batch(batch_id):
    data = request.get_json(silent=True) or {}
    material, quantity, error = _validate_batch_payload(data)
    if error:
        body, status = error
        return jsonify(body), status

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM material_batches WHERE id = ? AND is_deleted = FALSE', (batch_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404
        supplier_id = _resolve_supplier(conn, data.get('supplierName'), current_user.id)
        material_product_id = _resolve_material_product(conn, material, current_user.id)
        location_id = data.get('locationId')
        conn.execute(
            'UPDATE material_batches SET material_code=?, material_name=?, material_product_id=?, '
            'unit=?, supplier_id=?, quantity=?, expiry_date=?, notes=?, location_id=? WHERE id=?',
            (material['code'], material['name'], material_product_id, material['unit'], supplier_id,
             quantity, data.get('expiryDate') or '', data.get('notes', ''), location_id, batch_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật lô nguyên liệu thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@inventory_bp.route('/api/material-batches/<int:batch_id>', methods=['DELETE'])
@login_required
def delete_material_batch(batch_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM material_batches WHERE id = ? AND is_deleted = FALSE', (batch_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404
        conn.execute(
            'UPDATE material_batches SET is_deleted = TRUE, deleted_at = ? WHERE id = ?',
            (now(), batch_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa lô nguyên liệu thành công'})
    finally:
        conn.close()


# ── Traceability chain (TRACE-02) ────────────────────────────────────────

@inventory_bp.route('/api/material-batches/<int:batch_id>/trace', methods=['GET'])
@login_required
def trace_material_batch(batch_id):
    conn = get_connection()
    try:
        # No is_deleted filter (Pitfall 2) — trace must work even for a
        # soft-deleted batch; only a genuinely nonexistent id is a 404.
        batch_row = conn.execute(f'{_BATCH_SELECT} WHERE b.id = ?', (batch_id,)).fetchone()
        if not batch_row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404

        order_rows = conn.execute(
            'SELECT DISTINCT po.* FROM production_orders po '
            'JOIN bom_lines bl ON bl.product_code = po.product_code '
            'WHERE bl.code = ? AND po.is_deleted = FALSE '
            'ORDER BY po.created_at DESC',
            (batch_row['material_code'],),
        ).fetchall()
        consuming_orders = [
            {'order': _serialize_order(r), 'isFinishedGoods': r['status'] == 'completed'}
            for r in order_rows
        ]
        return jsonify({
            'success': True,
            'batch': _serialize_batch(batch_row),
            'consumingOrders': consuming_orders,
        })
    finally:
        conn.close()


# ── QC results (QC-01) ───────────────────────────────────────────────────

QC_STATUSES = ('pending', 'passed', 'failed')

# qc_results.result uses its own short 'pass'/'fail' vocabulary (see
# core/sanxuat_db.py's trigger, which only acts on 'fail') -- distinct from
# material_batches.qc_status's 'pending'/'passed'/'failed'.
_QC_RESULT_BY_STATUS = {'passed': 'pass', 'failed': 'fail'}


@inventory_bp.route('/api/material-batches/<int:batch_id>/qc-result', methods=['POST'])
@login_required
@require_role('manager')
def record_qc_result(batch_id):
    data = request.get_json(silent=True) or {}
    qc_status = data.get('qcStatus')
    qc_note = data.get('qcNote') or ''
    if qc_status not in QC_STATUSES:
        return jsonify({'success': False, 'message': 'Trạng thái QC không hợp lệ'}), 400

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM material_batches WHERE id = ? AND is_deleted = FALSE', (batch_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404

        result = _QC_RESULT_BY_STATUS.get(qc_status, qc_status)
        conn.execute(
            'INSERT INTO qc_results (batch_id, tested_by, test_type, result, detail, tested_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (batch_id, data.get('testedBy') or '', data.get('testType') or '', result, qc_note, now()),
        )
        # Belt-and-suspenders with the DB trigger (which only fires on
        # result='fail') -- this still needs to run explicitly so a
        # 'passed' result is reflected on material_batches too.
        conn.execute(
            'UPDATE material_batches SET qc_status = ?, qc_note = ? WHERE id = ?',
            (qc_status, qc_note, batch_id),
        )
        conn.commit()
        return jsonify({'success': True, 'qcStatus': qc_status, 'qcNote': qc_note})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


# ── Batch process events (QC-03/QC-04) ───────────────────────────────────

def _serialize_batch_event(row):
    return {
        'id': row['id'],
        'batchId': row['batch_id'],
        'ts': row['created_at'],
        'event': row['event'],
        'note': row['note'] or '',
    }


@inventory_bp.route('/api/material-batches/<int:batch_id>/events', methods=['POST'])
@login_required
def log_batch_event(batch_id):
    data = request.get_json(silent=True) or {}
    event = (data.get('event') or '').strip()
    note = data.get('note') or ''
    if not event:
        return jsonify({'success': False, 'message': 'Thiếu tên sự kiện quy trình'}), 400

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM material_batches WHERE id = ? AND is_deleted = FALSE', (batch_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy lô nguyên liệu'}), 404

        conn.execute(
            'INSERT INTO material_batch_events (batch_id, event, note, created_at) '
            'VALUES (?, ?, ?, ?)',
            (batch_id, event, note, now()),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Ghi nhận sự kiện thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@inventory_bp.route('/api/material-batches/<int:batch_id>/events', methods=['GET'])
@login_required
def get_batch_events(batch_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM material_batch_events WHERE batch_id = ? ORDER BY created_at ASC',
            (batch_id,),
        ).fetchall()
        return jsonify({'success': True, 'events': [_serialize_batch_event(r) for r in rows]})
    finally:
        conn.close()


# ── Expiring batches (TRACE-06) ──────────────────────────────────────────

def query_expiring_batches(conn, days):
    """Shared query for batches expiring within `days` days (or already
    expired), most-urgent-first. Used by this module's own GET route
    (TRACE-06) and by routes/n8n_api.py's `expiring-alert` internal
    dispatch action (TRACE-07) -- single source of truth, never forked."""
    rows = conn.execute(
        f"{_BATCH_SELECT} WHERE b.is_deleted = FALSE AND b.expiry_date IS NOT NULL "
        "AND b.expiry_date != '' ORDER BY b.expiry_date ASC"
    ).fetchall()
    today = datetime.now().date()
    results = []
    for r in rows:
        try:
            expiry = datetime.strptime(r['expiry_date'], '%Y-%m-%d').date()
        except (TypeError, ValueError):
            continue
        day_count = (expiry - today).days
        if day_count <= days:
            results.append((r, day_count))
    results.sort(key=lambda pair: pair[1])
    return [
        {**_serialize_batch(r), 'daysUntilExpiry': day_count}
        for r, day_count in results
    ]


@inventory_bp.route('/api/material-batches/expiring', methods=['GET'])
@login_required
def get_expiring_material_batches():
    days = request.args.get('days', default=7, type=int)
    conn = get_connection()
    try:
        return jsonify({'success': True, 'batches': query_expiring_batches(conn, days)})
    finally:
        conn.close()
