import json
import re
try: from json_repair import repair_json
except: repair_json = None

class AgentMiddleware:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_system_context(self):
        schema = self._get_db_schema_summary()
        tools = """
        [TOOLS]
        'google_sheet_read': {sheetId, range}
        'gmail_send': {to, subject, body}
        
        [PROTOCOL]
        Output JSON with "action": "create_workflow".
        """
        return f"{schema}\n{tools}"

    def _get_db_schema_summary(self):
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            try:
                c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                tables = [r[0] for r in c.fetchall()]
            except:
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in c.fetchall()]
            return "Tables: " + ", ".join(tables)
        except: return ""
        finally:
            if 'conn' in locals(): conn.close()

    def process_ai_response(self, ai_text, user_id):
        # 1. Try to find JSON
        json_data = None
        
        # Regex for markdown
        match = re.search(r'```json\s*(\{.*?\})\s*```', ai_text, re.DOTALL)
        if match:
            try: json_data = json.loads(match.group(1))
            except: pass
        
        # Regex for raw JSON
        if not json_data:
            try:
                start = ai_text.find('{')
                end = ai_text.rfind('}') + 1
                if start != -1 and end != -1:
                    if repair_json: json_data = json.loads(repair_json(ai_text[start:end]))
                    else: json_data = json.loads(ai_text[start:end])
            except: pass

        # 2. If JSON found, execute and RETURN CLEAN TEXT
        if json_data and isinstance(json_data, dict):
            action = json_data.get('action')
            
            if action == 'create_workflow':
                result = self._handle_create_workflow(json_data, user_id)
                # result[0] is the clean message ("✅ Created..."), result[1] is metadata
                return result 
            
            if action == 'query_db':
                return self._handle_query_db(json_data, user_id)

        # 3. If no JSON, return text as is
        return ai_text, None

    def _handle_create_workflow(self, data, user_id):
        name = data.get('name', 'AI Flow')
        payload = data.get('payload', {})
        if 'nodes' not in payload and 'nodes' in data: payload = data
        
        # Fix Nodes
        nodes = payload.get('nodes', [])
        for i, n in enumerate(nodes):
            n['id'] = str(n.get('id', i+1))
            if 'position' not in n: n['position'] = {"x": 100+(i*200), "y": 100}
            
        # Fix Edges
        edges = []
        for e in payload.get('edges', []):
            edges.append({"from": str(e.get('from')), "to": str(e.get('to'))})
            
        final_data = {"nodes": nodes, "edges": edges}
        
        conn = self.db.get_connection()
        c = conn.cursor()
        try:
            js = json.dumps(final_data)
            if hasattr(self.db, 'use_postgres') and self.db.use_postgres:
                c.execute('INSERT INTO workflows (user_id, name, data, created_at, updated_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id', (user_id, name, js))
                wid = c.fetchone()[0]
            else:
                c.execute('INSERT INTO workflows (user_id, name, data, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (user_id, name, js))
                wid = c.lastrowid
            conn.commit()
            
            # --- THE FIX: Return a User-Friendly Message, NOT JSON ---
            return f"✅ **Quy trình đã được tạo!**\n\nTên: {name}", {"action": "workflow_created", "id": wid}
            
        except Exception as e:
            return f"Error: {e}", None
        finally: conn.close()

    def _handle_query_db(self, data, user_id):
        return "Query executed.", {"type": "query"}