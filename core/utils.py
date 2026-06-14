import json
from datetime import datetime

_WORKSPACE_COLUMNS = ('id', 'user_id', 'name', 'type', 'description')


def _workspace_mapping(workspace):
    if isinstance(workspace, dict):
        return workspace
    if hasattr(workspace, 'keys'):
        return workspace
    return dict(zip(_WORKSPACE_COLUMNS, workspace))

class Utils:
    @staticmethod
    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Object of type datetime is not JSON serializable")
    
    @staticmethod
    def parse_json_safely(json_string, default=None):
        try:
            return json.loads(json_string) if json_string else default
        except (json.JSONDecodeError, ValueError, TypeError):
            return default
    
    @staticmethod
    def format_workspace_tree(workspaces):
        """Format workspaces for tree-like display"""
        tree = {
            'personal': [],
            'team': [],
            'scenarios': [],
            'projects': []
        }
        
        for workspace in workspaces:
            row = _workspace_mapping(workspace)
            workspace_type = row['type']
            if workspace_type in tree:
                tree[workspace_type].append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'type': workspace_type
                })
        
        return tree
    
    @staticmethod
    def get_workspace_icon(workspace_type):
        icons = {
            'personal': '👤',
            'team': '👥', 
            'scenarios': '🎭',
            'projects': '📁'
        }
        return icons.get(workspace_type, '📋')
    
    @staticmethod
    def get_status_color(status):
        colors = {
            'todo': '#6b7280',
            'in_progress': '#3b82f6',
            'completed': '#10b981',
            'blocked': '#ef4444'
        }
        return colors.get(status, '#6b7280')

utils = Utils()
