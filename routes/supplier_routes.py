"""Supplier routes — real backend for supplier CRUD (SUPPLIER-01) and the
supplier->batches FK lookup (SUPPLIER-02).

Replaces the localStorage mock in static/js/store.js (suppliers array,
createSupplier/updateSupplier/deleteSupplier, and the fragile trimmed/
lowercased getSupplierBatches string-matching at store.js:844-851) with a
real `suppliers` table and a `material_batches.supplier_id` FK JOIN.

This file's own CRUD always server-generates the real `NCC-{id:03d}` code
directly, unlike routes/inventory_routes.py's free-text-supplier-name
resolver helper (which is exclusively for POST /api/material-batches'
free-text-to-FK resolution and produces a placeholder `NCC-PENDING-{hex}`
code) -- the two paths are deliberately independent, see 02-RESEARCH.md.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.sanxuat_db import get_connection, now

supplier_bp = Blueprint('supplier', __name__)


def _serialize_supplier(row):
    return {
        'id': row['id'],
        'code': row['code'],
        'name': row['name'],
        'contact': row['contact'] or '',
        'phone': row['phone'] or '',
        'email': row['email'] or '',
        'address': row['address'] or '',
        'notes': row['notes'] or '',
    }


# ── Supplier CRUD (SUPPLIER-01) ──────────────────────────────────────────

@supplier_bp.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM suppliers WHERE is_deleted = FALSE ORDER BY created_at DESC'
        ).fetchall()
        return jsonify({'success': True, 'suppliers': [_serialize_supplier(r) for r in rows]})
    finally:
        conn.close()


@supplier_bp.route('/api/suppliers', methods=['POST'])
@login_required
def create_supplier():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên nhà cung cấp'}), 400

    conn = get_connection()
    try:
        # Client-supplied `code` is never trusted/inserted -- the real code
        # is always server-generated below from the new row's own id.
        cur = conn.execute(
            'INSERT INTO suppliers (name, contact, phone, email, address, notes, '
            'created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (name, data.get('contact', ''), data.get('phone', ''), data.get('email', ''),
             data.get('address', ''), data.get('notes', ''), current_user.id, now()),
        )
        supplier_id = cur.lastrowid
        code = f'NCC-{str(supplier_id).zfill(3)}'
        conn.execute('UPDATE suppliers SET code = ? WHERE id = ?', (code, supplier_id))
        conn.commit()
        return jsonify({'success': True, 'id': supplier_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@supplier_bp.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
@login_required
def update_supplier(supplier_id):
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên nhà cung cấp'}), 400

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM suppliers WHERE id = ? AND is_deleted = FALSE', (supplier_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy nhà cung cấp'}), 404
        # `code` is never touched here -- only set once, at create time.
        conn.execute(
            'UPDATE suppliers SET name=?, contact=?, phone=?, email=?, address=?, notes=? '
            'WHERE id=?',
            (name, data.get('contact', ''), data.get('phone', ''), data.get('email', ''),
             data.get('address', ''), data.get('notes', ''), supplier_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật nhà cung cấp thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@supplier_bp.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
@login_required
def delete_supplier(supplier_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM suppliers WHERE id = ? AND is_deleted = FALSE', (supplier_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy nhà cung cấp'}), 404
        conn.execute(
            'UPDATE suppliers SET is_deleted = TRUE, deleted_at = ? WHERE id = ?',
            (now(), supplier_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa nhà cung cấp thành công'})
    finally:
        conn.close()
