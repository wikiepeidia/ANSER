
from src.core.config import Config

class AgentMiddleware:
    def __init__(self):
        pass

    def get_db_schema(self):
        # In Agentic Mode, the Backend sends the schema.
        # We return a placeholder to avoid duplication.
        return "Schema provided in user context."

    def get_workflow_tools(self):
        return """
        [AVAILABLE WORKFLOW NODES]
        1. 'google_sheet_read' { "sheetId": "...", "range": "A1:Z" }
        2. 'google_sheet_write' { "sheetId": "...", "range": "A1", "data": "{{parent.output}}", "writeMode": "append" }
        3. 'gmail_send' { "to": "...", "subject": "...", "body": "..." }
        4. 'filter' { "condition": "contains", "field": "status", "value": "active" }
        5. 'database_query' { "query": "SELECT * FROM sales" }
        
        [OUTPUT FORMAT]
        {
          "action": "create_workflow",
          "name": "Workflow Name",
          "payload": {
            "nodes": [ ... ],
            "edges": [ ... ]
          }
        }
        """
