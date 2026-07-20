"""Wallet, subscription, and profile routes — wallet_bp Blueprint."""
import sqlite3

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from core.extensions import db_manager
from core.services.wallet_service import (
    create_topup_request, create_withdrawal, get_pending_transactions,
    get_wallet_data, process_transaction, toggle_auto_renew, upgrade_subscription,
)

wallet_bp = Blueprint('wallet', __name__)


@wallet_bp.route('/wallet')
@login_required
def wallet_dashboard():
    return render_template('wallet.html', user=current_user)


@wallet_bp.route('/api/user/wallet')
@login_required
def api_get_wallet():
    conn = db_manager.get_business_connection()
    try:
        data = get_wallet_data(conn, current_user.id)
        return jsonify({'success': True, **data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@wallet_bp.route('/api/session')
def api_session():
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False})
    return jsonify({'authenticated': True, 'user': {
        'id': current_user.id, 'email': current_user.email,
        'name': current_user.name, 'role': getattr(current_user, 'role', 'user'),
    }})


@wallet_bp.route('/api/user/profile', methods=['POST'])
@login_required
def api_update_profile():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Tên là bắt buộc'}), 400
    conn = db_manager.get_connection()
    try:
        c = conn.cursor()
        c.execute('UPDATE users SET name = ? WHERE id = ?', (name, current_user.id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@wallet_bp.route('/api/settings/update', methods=['POST'])
@login_required
def api_update_settings():
    data = request.get_json()
    setting_key = data.get('key')
    if not setting_key:
        return jsonify({'success': False, 'message': 'Thiếu khóa cài đặt'}), 400
    try:
        # `get_business_db_connection` (không phải `get_business_connection`) là
        # @contextmanager — `get_business_connection` trả PGShimConnection, vốn
        # KHÔNG implement __enter__/__exit__, nên `with` ở đây từng ném
        # TypeError mỗi lần save setting.
        with db_manager.get_business_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO system_settings (key, value, group_name, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP''',
                (setting_key, data.get('value'), data.get('group')),
            )
            conn.commit()
        return jsonify({'success': True, 'message': 'Đã cập nhật cài đặt'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@wallet_bp.route('/api/user/wallet/topup', methods=['POST'])
@login_required
def api_topup_wallet():
    data = request.get_json() or {}
    try:
        amount = int(data.get('amount', 0))
    except (TypeError, ValueError):
        amount = 0
    method = (data.get('method') or 'bank_transfer').strip()
    reference = (data.get('reference') or '').strip()[:120]
    note = (data.get('note') or '').strip()[:200]
    conn = db_manager.get_business_connection()
    try:
        create_topup_request(conn, current_user.id, amount, method, reference, note)
        return jsonify({'success': True, 'message': 'Yêu cầu nạp tiền đã được gửi. Admin sẽ xác nhận sớm.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@wallet_bp.route('/api/admin/wallet/withdraw', methods=['POST'])
@login_required
def api_admin_withdraw():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    data = request.get_json() or {}
    try:
        amount = int(data.get('amount', 0))
    except (TypeError, ValueError):
        amount = 0
    bank_name = (data.get('bank_name') or '').strip()
    account_number = (data.get('account_number') or '').strip()
    account_name = (data.get('account_name') or '').strip()
    note = (data.get('note') or '').strip()
    if not bank_name or not account_number or not account_name:
        return jsonify({'success': False, 'message': 'Vui lòng cung cấp đầy đủ thông tin ngân hàng'}), 400
    conn = db_manager.get_business_connection()
    try:
        create_withdrawal(conn, current_user.id, amount, bank_name, account_number, account_name, note)
        return jsonify({'success': True, 'message': 'Yêu cầu rút tiền đã được gửi.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@wallet_bp.route('/api/user/subscription/upgrade', methods=['POST'])
@login_required
def api_upgrade_subscription():
    data = request.get_json() or {}
    plan_key = str(data.get('plan', ''))
    conn = db_manager.get_business_connection()
    auth_conn = db_manager.get_connection()
    try:
        result = upgrade_subscription(conn, auth_conn, current_user.id, plan_key)
        return jsonify({'success': True, 'message': 'Nâng cấp thành công.',
                        'balance': result['new_balance'], 'expires_at': result['expires_at']})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
        auth_conn.close()


@wallet_bp.route('/api/user/subscription/auto-renew', methods=['POST'])
@login_required
def api_user_toggle_auto_renew():
    data = request.get_json() or {}
    enabled = data.get('enabled')
    if enabled is None:
        return jsonify({'success': False, 'message': 'Tham số không hợp lệ: enabled'}), 400
    conn = db_manager.get_business_connection()
    try:
        toggle_auto_renew(conn, current_user.id, bool(enabled))
        return jsonify({'success': True, 'message': 'Đã cập nhật tự động gia hạn'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@wallet_bp.route('/api/admin/wallet/pending', methods=['GET'])
@login_required
def api_admin_pending_wallet_transactions():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    conn = db_manager.get_business_connection()
    conn.row_factory = sqlite3.Row
    auth_conn = db_manager.get_connection()
    auth_conn.row_factory = sqlite3.Row
    try:
        transactions = get_pending_transactions(conn, auth_conn)
        return jsonify({'success': True, 'transactions': transactions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
        auth_conn.close()


@wallet_bp.route('/api/admin/wallet/pending/<int:transaction_id>', methods=['POST'])
@login_required
def api_admin_process_wallet_transaction(transaction_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    data = request.get_json() or {}
    action = data.get('action')
    note = (data.get('note') or '').strip()
    conn = db_manager.get_business_connection()
    try:
        process_transaction(conn, transaction_id, action,
                            current_user.id, current_user.email, note)
        msg = 'Giao dịch đã được duyệt và ví đã được cập nhật.' if action == 'approve' else 'Giao dịch đã bị từ chối.'
        return jsonify({'success': True, 'message': msg})
    except (ValueError, LookupError) as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
