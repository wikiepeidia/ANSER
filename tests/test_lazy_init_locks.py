"""
Regression tests for ENGINE-04 ("two real (if minor) TOCTOU races still present").

Proves the two remaining unguarded lazy-init singletons —
`HttpClientPool.get_client()` (src/core/utils.py) and `routes/chat.py`'s
module-level `_saas` singleton (`_get_saas()`) — now follow the same
fast-path-check -> acquire-lock -> recheck -> construct shape already correct
in `src/api/dependencies.py`'s `RuntimeState.ensure_text_runtime()`, and
construct exactly once under concurrent first access.

No `@pytest.mark.asyncio` — `pytest-asyncio` is not a declared project
dependency (mirrors tests/test_engine_concurrency.py's asyncio.run() pattern).
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path (mirrors tests/test_server.py's existing pattern)
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))


def test_get_client_concurrent_calls_share_single_instance():
    """
    10 concurrent first-access calls to HttpClientPool.get_client() must
    return the identical httpx.AsyncClient object, with zero exceptions.
    """
    from src.core.utils import HttpClientPool

    # Reset shared state so this test is independent of import/run order
    HttpClientPool._client = None

    async def _run_concurrent():
        return await asyncio.gather(
            *[HttpClientPool.get_client() for _ in range(10)]
        )

    results = asyncio.run(_run_concurrent())

    assert len(results) == 10
    first = results[0]
    for client in results:
        assert client is first, (
            "HttpClientPool.get_client() returned different AsyncClient "
            "instances under concurrent first access — double-checked lock "
            "is missing or broken."
        )

    # Reset state for later tests in the suite
    asyncio.run(HttpClientPool.close())


def test_get_saas_concurrent_calls_share_single_instance(monkeypatch):
    """
    10 concurrent first-access calls to chat.py's _get_saas() must construct
    the underlying SaasAPI exactly once and return the identical object.
    """
    # Importing chat.py pulls in fastapi — same pre-existing requirement
    # tests/test_server.py already has; ENV=LOCAL mirrors that pattern too.
    os.environ["ENV"] = "LOCAL"

    import src.api.routes.chat as chat_module
    import src.core.saas_api as saas_api_module

    # Reset shared state so this test is independent of import/run order
    chat_module._saas = None

    call_count = {"n": 0}

    class FakeSaasAPI:
        def __init__(self):
            call_count["n"] += 1

    monkeypatch.setattr(saas_api_module, "SaasAPI", FakeSaasAPI)

    async def _run_concurrent():
        return await asyncio.gather(
            *[chat_module._get_saas() for _ in range(10)]
        )

    results = asyncio.run(_run_concurrent())

    assert call_count["n"] == 1, (
        f"Expected SaasAPI to be constructed exactly once, got {call_count['n']} "
        "constructions — double-checked lock is missing or broken."
    )

    assert len(results) == 10
    first = results[0]
    for saas in results:
        assert saas is first, (
            "_get_saas() returned different objects under concurrent first "
            "access — double-checked lock is missing or broken."
        )

    # Reset state for later tests in the suite
    chat_module._saas = None
