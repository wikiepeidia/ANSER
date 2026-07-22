from src.core.context import ContextResolver
from src.core.memory import MemoryManager


class _FakeMemory:
    def __init__(self, stores):
        self._stores = stores

    def get_user_stores(self, user_id):
        return self._stores


def test_context_resolver_ready_when_single_store():
    memory = _FakeMemory(
        [{"id": 1, "name": "Store A", "industry": "Retail", "location": "HCM"}]
    )
    resolver = ContextResolver(memory)
    status, context = resolver.resolve_login(user_id=123)
    assert status == "READY"
    assert "Store A" in context


def test_context_resolver_ambiguous_when_multiple_stores():
    memory = _FakeMemory(
        [
            {"id": 1, "name": "Store A", "industry": "Retail", "location": "HCM"},
            {"id": 2, "name": "Store B", "industry": "Retail", "location": "HN"},
        ]
    )
    resolver = ContextResolver(memory)
    status, stores = resolver.resolve_login(user_id=123)
    assert status == "AMBIGUOUS"
    assert len(stores) == 2


def test_memory_manager_store_methods_safe_without_db():
    memory = MemoryManager()
    memory.engine = None
    assert memory.get_user_stores(uid=1) == []
    assert memory.get_store_details(store_id=1) is None
    assert memory.save_workflow(wid=1, name="wf", data={"a": 1}) is None
