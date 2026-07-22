"""
src/core/agent_middleware.py

Cung cấp "danh mục công cụ" (workflow nodes) cho CoderAgent để sinh JSON workflow
TƯƠNG THÍCH với workflow_engine.py của Body (topological-sort / Kahn's algorithm).

⚠️ QUAN TRỌNG: Danh sách node + param dưới đây PHẢI khớp 1-1 với
core/workflow_engine.py bên repo Body. Nếu Body đổi/đặt tên param khác,
cập nhật ở đây — sai param = CoderAgent sinh workflow KHÔNG chạy được.
(File này nằm ở Brain nhưng là "bản sao mô tả" của engine bên Body.)
"""


class AgentMiddleware:
    def __init__(self):
        pass

    def get_db_schema(self) -> str:
        # Ở chế độ Agentic, Backend (Body) gửi schema kèm user context.
        # Trả placeholder để tránh trùng lặp định nghĩa schema.
        return "Schema provided in user context."

    def get_workflow_tools(self) -> str:
        # Đây là string được nhét thẳng vào prompt của CoderAgent => viết bằng tiếng Anh,
        # ngắn gọn, đúng tên node mà workflow_engine.py của Body hỗ trợ.
        return """
[AVAILABLE WORKFLOW NODES]  (type -> params)
- google_sheet_read   { "sheetId": "...", "range": "A1:Z" }
- google_sheet_write  { "sheetId": "...", "range": "A1", "data": "{{n1.output}}", "writeMode": "append" }
- google_doc_read     { "docId": "..." }
- google_doc_write    { "docId": "...", "content": "{{n1.output}}" }
- gmail_send          { "to": "...", "subject": "...", "body": "..." }
- discord_notify      { "webhookUrl": "...", "content": "..." }
- slack_notify        { "channel": "...", "text": "..." }
- make_webhook        { "url": "...", "method": "POST", "body": "{{n1.output}}" }
- filter              { "field": "status", "condition": "contains", "value": "active" }
- invoice_ocr         { "imageUrl": "..." }        # gọi sang Brain /ocr
- invoice_forecast    { "productId": "...", "horizon": 7 }
- iot_db_insert       { "table": "iot_events", "data": "{{n1.output}}" }
- iot_db_query        { "table": "iot_events", "filter": "..." }

[RULES]
- Use ONLY the node types listed above. Do NOT invent nodes.
- There is NO raw-SQL node. To read business data, the platform handles it
  server-side; never emit arbitrary SQL.
- Reference a previous node's output via "{{<node_id>.output}}".

[OUTPUT FORMAT]  (return EXACTLY this shape)
{
  "action": "create_workflow",
  "name": "Workflow Name",
  "payload": {
    "nodes": [
      { "id": "n1", "type": "google_sheet_read", "params": { "sheetId": "...", "range": "A1:Z" } },
      { "id": "n2", "type": "discord_notify",    "params": { "webhookUrl": "...", "content": "{{n1.output}}" } }
    ],
    "edges": [
      { "from": "n1", "to": "n2" }
    ]
  }
}
"""