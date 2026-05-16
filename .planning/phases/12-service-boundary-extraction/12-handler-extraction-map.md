# Phase 12 Handler Extraction Map

This ledger tracks route-handler migration from monolithic handlers to Flask-independent service functions.

| Endpoint | Method | Current Handler | Target Service Function | Delegation Status | Test Reference |
| --- | --- | --- | --- | --- | --- |
| /api/workflow/execute | POST | run_workflow | execute_user_workflow(workflow_data, google_token_raw) | verified | tests/services/test_workflow_service.py |
| /api/workflows | GET | get_user_workflows | list_workflows_for_user(db_conn, user_id) | verified | tests/services/test_workflow_service.py |
| /api/workflows | POST | save_workflow | save_workflow_for_user(db_conn, user_id, payload) | verified | tests/services/test_workflow_service.py |
| /api/ai/chat | POST | ai_chat | submit_chat_message(user_id, message) | verified | tests/services/test_ai_chat_service.py |
| /api/ai/status/<job_id> | GET | ai_job_status | get_chat_job_status(job_id) | verified | tests/services/test_ai_chat_service.py |
| /api/ai/history | GET | get_chat_history | fetch_chat_history(db_conn, user_id, limit=50) | verified | tests/services/test_ai_chat_service.py |
| /api/ai/history | DELETE | clear_chat_history | clear_chat_history_rows(db_conn, user_id) | verified | tests/services/test_ai_chat_service.py |
| /api/imports | POST | api_create_import | create_import_transaction(db_conn, user_id, payload) | verified | tests/services/test_inventory_tx_service.py; tests/services/test_inventory_route_delegation.py |
| /api/exports | POST | api_create_export | create_export_transaction(db_conn, user_id, payload, automation_engine) | verified | tests/services/test_inventory_tx_service.py; tests/services/test_inventory_route_delegation.py |
