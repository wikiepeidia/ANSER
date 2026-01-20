
Failed to fetch scenarios: 'Database' object has no attribute 'get_scenarios'

AI agent system is not dumping the nodes. If we ask:
tôi muốn làm 1 quy trình tự động hóa mà nó sẽ tự đọc file google sheet 'Kịch bản' và gửi email về kịch bản đó cho email: <sonkhagioi@gmail.com>
it manage to load the modal✅ Automation Created
✅ Quy trình đã được tạo!

Tên: Send Google Sheet Content via Email : Open worlflow but nothing happened, there is nothign on the canvas. Besides, the modal when referesh page suddenly change to pure json:
{ "action": "create_workflow", "name": "Send Google Sheet Content via Email", "payload": { "nodes": [ { "id": "1", "type": "google_sheet_read", "params": { "sheetId": "Kịch bản", "range": "A1:Z" } }, { "id": "2", "type": "gmail_send", "params": { "to": "sonkhagioi@gmail.com", "subject": "Kịch bản từ Google Sheet", "body": "{{node_1.output}}" } } ], "edges": [ { "from": "1", "to": "2" } ] } }
