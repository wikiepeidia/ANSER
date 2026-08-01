"""
Wave-0 unit test for AI-OPS-02's RERANKER_DEVICE override (Phase 9,
09-01-PLAN.md Task 2).

Uses a bare `object.__new__(KnowledgeBase)` instance (mirrors
tests/test_kb_rebuild.py's `_kb_with_fakes` pattern) with `.device` set
directly, bypassing `__init__` entirely -- this test never constructs a real
`KnowledgeBase()` and therefore never downloads/loads a real
`bge-reranker-v2-m3` CrossEncoder model or touches the network/GPU.
"""

import src.core.knowledge as knowledge_module
from src.core.knowledge import KnowledgeBase


def _bare_kb(device):
    kb = object.__new__(KnowledgeBase)
    kb.device = device
    return kb


def test_reranker_device_unset_falls_back_to_self_device(monkeypatch):
    monkeypatch.delenv("RERANKER_DEVICE", raising=False)
    kb = _bare_kb("cuda")
    assert kb._resolve_reranker_device() == "cuda"

    kb_cpu = _bare_kb("cpu")
    assert kb_cpu._resolve_reranker_device() == "cpu"


def test_reranker_device_cpu_override_independent_of_self_device(monkeypatch):
    monkeypatch.setenv("RERANKER_DEVICE", "cpu")
    kb = _bare_kb("cuda")
    assert kb._resolve_reranker_device() == "cpu"
    # The embedder's device selection (self.device) is untouched by the
    # override -- proven by self.device still reading "cuda" here.
    assert kb.device == "cuda"


def test_reranker_device_whitespace_and_case_noise_normalized(monkeypatch):
    monkeypatch.setenv("RERANKER_DEVICE", " CPU ")
    kb = _bare_kb("cuda")
    assert kb._resolve_reranker_device() == "cpu"


def test_embedder_device_line_untouched_by_reranker_override(monkeypatch):
    # Regression guard: the module source itself must not have started
    # routing the embedder's device through RERANKER_DEVICE too.
    import inspect

    source = inspect.getsource(knowledge_module.KnowledgeBase.__init__)
    embedder_line = next(
        line for line in source.splitlines() if "self.embedder = SentenceTransformer" in line
    )
    assert "device=self.device" in embedder_line
    assert "_resolve_reranker_device" not in embedder_line
