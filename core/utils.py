import json
from datetime import datetime

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
            workspace_type = workspace[3]  # type column
            if workspace_type in tree:
                tree[workspace_type].append({
                    'id': workspace[0],
                    'name': workspace[2],
                    'description': workspace[4],
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