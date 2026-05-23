"""Analytics, dashboard, reports, and automation routes — operations_bp Blueprint."""
import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.services.analytics_service import analytics_service
from core.services.operations_service import (
    create_automation, create_scheduled_report, delete_automation,
    delete_scheduled_report, get_automations, get_dashboard_stats,
    get_report_stats, get_scheduled_reports, update_automation,
)
from core.logger import get_logger

logger = get_logger(__name__)

operations_bp = Blueprint('operations', __name__)


@operations_bp.route('/api/admin/analytics/data', methods=['GET'])
@login_required
def api_get_analytics_data():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    property_id = request.args.get('property_id')
    if request.args.get('force') in ('1', 'true', 'yes'):
        try:
            cache_file = os.path.join(os.getcwd(), 'secrets', 'ga_cache.json')
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info("Analytics cache cleared via force param")
        except OSError as e:
            logger.warning("Failed to clear analytics cache via force param: %s", e)
    return jsonify(analytics_service.get_report(property_id))


@operations_bp.route('/api/admin/analytics/clear_cache', methods=['POST'])
@login_required
def api_admin_clear_analytics_cache():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    try:
        cache_file = os.path.join(os.getcwd(), 'secrets', 'ga_cache.json')
        if os.path.exists(cache_file):
            os.remove(cache_file)
            return jsonify({'success': True, 'message': 'Đã xóa cache'})
        return jsonify({'success': False, 'message': 'Không có file cache'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def api_get_dashboard_stats():
    try:
        stats = get_dashboard_stats(current_user.id)
        return jsonify({'success': True, 'pending_returns': 0, 'credits': 100,
                        'subscription_status': 'Active', **stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/reports/stats', methods=['GET'])
@login_required
def api_get_report_stats():
    try:
        stats = get_report_stats()
        return jsonify({'success': True, **stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/reports/scheduled', methods=['GET'])
@login_required
def api_get_scheduled_reports():
    try:
        reports = get_scheduled_reports()
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/reports/scheduled', methods=['POST'])
@login_required
def api_create_scheduled_report():
    data = request.get_json()
    try:
        create_scheduled_report(
            data.get('name'), data.get('report_type'), data.get('frequency'),
            data.get('channel'), data.get('recipients'), current_user.id,
        )
        return jsonify({'success': True, 'message': 'Lên lịch báo cáo thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/reports/scheduled/<int:report_id>', methods=['DELETE'])
@login_required
def api_delete_scheduled_report(report_id):
    try:
        delete_scheduled_report(report_id)
        return jsonify({'success': True, 'message': 'Xóa báo cáo thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/automations', methods=['GET'])
@login_required
def api_get_automations():
    try:
        return jsonify({'success': True, 'automations': get_automations()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/automations', methods=['POST'])
@login_required
def api_create_automation():
    data = request.get_json()
    try:
        create_automation(data.get('name'), data.get('type'), data.get('config', {}), current_user.id)
        return jsonify({'success': True, 'message': 'Tạo tự động hóa thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/automations/<int:automation_id>', methods=['PUT'])
@login_required
def api_update_automation(automation_id):
    try:
        update_automation(automation_id, request.get_json())
        return jsonify({'success': True, 'message': 'Cập nhật tự động hóa thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_bp.route('/api/automations/<int:automation_id>', methods=['DELETE'])
@login_required
def api_delete_automation(automation_id):
    try:
        delete_automation(automation_id)
        return jsonify({'success': True, 'message': 'Xóa tự động hóa thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
