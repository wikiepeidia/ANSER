"""Workspace and scenario API routes — workspace_bp Blueprint."""
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from core.extensions import db_manager
from core.services.workspace_service import (
    create_item, create_workspace, delete_item, get_workspace_items, update_item,
)
from core.logger import get_logger

logger = get_logger(__name__)

workspace_bp = Blueprint('workspaces', __name__)


@workspace_bp.route('/api/workspaces')
@login_required
def get_workspaces():
    try:
        auth_manager = current_app.extensions['auth_manager']
        workspaces = auth_manager.get_user_workspaces(current_user.id)
        return jsonify([
            {'id': w[0], 'name': w[2], 'type': w[3], 'description': w[4], 'created_at': w[6]}
            for w in workspaces
        ])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/workspace/<int:workspace_id>/items')
@login_required
def get_workspace_items_route(workspace_id):
    try:
        items = get_workspace_items(workspace_id, current_user.id)
        return jsonify(items)
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/workspace/<int:workspace_id>/items', methods=['POST'])
@login_required
def create_item_route(workspace_id):
    data = request.get_json()
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({'success': False, 'message': 'Tiêu đề mục là bắt buộc'}), 400
    try:
        item_id = create_item(
            workspace_id, current_user.id,
            data['title'].strip(), data.get('description', ''),
            data.get('type', 'task'), data.get('status', 'todo'),
            data.get('priority', 'medium'),
        )
        return jsonify({'success': True, 'item_id': item_id, 'message': 'Tạo mục thành công'})
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@workspace_bp.route('/api/items/<int:item_id>', methods=['PUT'])
@login_required
def update_item_route(item_id):
    data = request.get_json()
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({'success': False, 'message': 'Tiêu đề mục là bắt buộc'}), 400
    try:
        update_item(
            item_id, current_user.id,
            data['title'].strip(), data.get('description', ''),
            data.get('status', 'todo'), data.get('priority', 'medium'),
        )
        return jsonify({'success': True, 'message': 'Cập nhật mục thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@workspace_bp.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item_route(item_id):
    try:
        delete_item(item_id, current_user.id)
        return jsonify({'success': True, 'message': 'Xóa mục thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@workspace_bp.route('/api/workspace', methods=['POST'])
@login_required
def create_workspace_route():
    data = request.get_json()
    if not data or 'name' not in data or 'type' not in data or not data['name'].strip():
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc: tên và loại'}), 400
    try:
        workspace_id = create_workspace(
            current_user.id, data['name'].strip(),
            data['type'], data.get('description', ''),
        )
        return jsonify({'success': True, 'workspace_id': workspace_id,
                        'message': 'Tạo không gian làm việc thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@workspace_bp.route('/api/scenarios', methods=['GET'])
@login_required
def get_scenarios():
    try:
        return jsonify({'success': True, 'scenarios': db_manager.get_scenarios(current_user.id)})
    except Exception as e:
        logger.error("Error fetching scenarios for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
@login_required
def get_scenario(scenario_id):
    try:
        scenario = db_manager.get_scenario(scenario_id, current_user.id)
        if scenario:
            return jsonify({'success': True, 'scenario': scenario})
        return jsonify({'success': False, 'message': 'Không tìm thấy kịch bản'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/scenarios', methods=['POST'])
@login_required
def create_scenario():
    try:
        data = request.get_json()
        logger.info("Creating scenario for user %s: %s", current_user.id, data.get("name"))
        scenario_id = db_manager.create_scenario(
            user_id=current_user.id,
            name=data.get('name'),
            description=data.get('description', ''),
            active=data.get('active', False),
            steps=data.get('steps'),
        )
        return jsonify({'success': True, 'message': 'Tạo kịch bản thành công', 'id': scenario_id})
    except Exception as e:
        logger.error("Error creating scenario for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
@login_required
def update_scenario(scenario_id):
    try:
        db_manager.update_scenario(scenario_id, current_user.id, request.get_json())
        return jsonify({'success': True, 'message': 'Cập nhật kịch bản thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@workspace_bp.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
@login_required
def delete_scenario(scenario_id):
    try:
        db_manager.delete_scenario(scenario_id, current_user.id)
        return jsonify({'success': True, 'message': 'Xóa kịch bản thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
