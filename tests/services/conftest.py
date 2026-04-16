"""Shared fixtures for service-layer unit tests."""

import pytest


@pytest.fixture
def db_stub():
    """Provide a minimal DB-like object for contract tests."""
    class _Stub:
        pass

    return _Stub()


@pytest.fixture
def workflow_payload():
    """Provide workflow payload fixture used by service tests."""
    return {
        "nodes": [],
        "edges": [],
    }


@pytest.fixture
def tx_payload():
    """Provide import/export payload fixture used by service tests."""
    return {
        "product_id": 1,
        "quantity": 2,
    }
