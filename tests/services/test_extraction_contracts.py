"""Contract checks for Phase 12 service boundary extraction."""

import inspect

import core.services.ai_chat_service as ai_chat_service
import core.services.inventory_tx_service as inventory_tx_service
import core.services.workflow_service as workflow_service


def _assert_no_flask_globals(module):
    source = inspect.getsource(module)
    assert "from flask import" not in source
    assert "request" not in source
    assert "current_user" not in source


def test_workflow_service_contracts_exist(db_stub, workflow_payload):
    assert hasattr(workflow_service, "execute_user_workflow")
    assert hasattr(workflow_service, "list_workflows_for_user")
    assert callable(workflow_service.execute_user_workflow)
    assert callable(workflow_service.list_workflows_for_user)

    workflow_service.execute_user_workflow(workflow_payload, None)
    workflow_service.list_workflows_for_user(db_stub, user_id=1)


def test_ai_chat_service_contracts_exist(db_stub):
    assert hasattr(ai_chat_service, "submit_chat_message")
    assert hasattr(ai_chat_service, "get_chat_history_rows")
    assert callable(ai_chat_service.submit_chat_message)
    assert callable(ai_chat_service.get_chat_history_rows)

    ai_chat_service.submit_chat_message(user_id=1, message="hello")
    ai_chat_service.get_chat_history_rows(db_stub, user_id=1, limit=5)


def test_inventory_transaction_contracts_exist(db_stub, tx_payload):
    assert hasattr(inventory_tx_service, "create_import_transaction")
    assert hasattr(inventory_tx_service, "create_export_transaction")
    assert callable(inventory_tx_service.create_import_transaction)
    assert callable(inventory_tx_service.create_export_transaction)

    inventory_tx_service.create_import_transaction(db_stub, user_id=1, payload=tx_payload)
    inventory_tx_service.create_export_transaction(db_stub, user_id=1, payload=tx_payload)


def test_service_modules_do_not_use_flask_globals():
    _assert_no_flask_globals(workflow_service)
    _assert_no_flask_globals(ai_chat_service)
    _assert_no_flask_globals(inventory_tx_service)
