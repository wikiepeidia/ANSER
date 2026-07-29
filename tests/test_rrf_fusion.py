"""
RAG-02: Reciprocal Rank Fusion tests for KnowledgeBase.reciprocal_rank_fusion()
and its wiring into KnowledgeBase.search().

Every test constructs `kb = object.__new__(KnowledgeBase)` to bypass
`__init__`/model loading entirely, mirroring tests/test_smart_chunk.py's
bare-instance construction pattern.

Relies on tests/conftest.py's session-wide pypdf/docx/rank_bm25 stub
registration so `from src.core.knowledge import KnowledgeBase` succeeds on
this machine (those three packages are pinned in requirements.txt but not
installed locally). No model download happens here -- BAAI/bge-reranker-v2-m3
is never actually loaded by these tests; a fake reranker object stands in
for the real CrossEncoder.
"""

import sys
from pathlib import Path

import pytest

# Add project root to sys.path (mirrors tests/test_smart_chunk.py).
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.core.knowledge import KnowledgeBase  # noqa: E402


def _kb():
    return object.__new__(KnowledgeBase)


def test_reciprocal_rank_fusion_scores_and_orders_by_rrf_formula():
    kb = _kb()

    fused = kb.reciprocal_rank_fusion(
        [["docA", "docB", "docC"], ["docB", "docD"]], k=60
    )

    fused_dict = dict(fused)
    assert set(fused_dict.keys()) == {"docA", "docB", "docC", "docD"}, (
        f"Expected all four unique docs exactly once, got: {fused}"
    )

    # docB appears in both lists: rank 2 (1-indexed) in list 1, rank 1 in list 2.
    assert fused_dict["docB"] == pytest.approx(1 / 61 + 1 / 62, abs=1e-9)
    # docA: rank 1, list 1 only.
    assert fused_dict["docA"] == pytest.approx(1 / 61, abs=1e-9)
    # docD: rank 1, list 2 only.
    assert fused_dict["docD"] == pytest.approx(1 / 62, abs=1e-9)
    # docC: rank 3, list 1 only.
    assert fused_dict["docC"] == pytest.approx(1 / 63, abs=1e-9)

    order = [doc for doc, _ in fused]
    assert order == ["docB", "docA", "docD", "docC"], (
        "docB should rank first (cross-list appearance boost) despite docA "
        f"being rank-1 in dense alone. Got order: {order}"
    )


class _FakeEncodeResult(list):
    """List-subclass standing in for the embedder's numpy-array return value
    -- search() calls `.tolist()` on it."""

    def tolist(self):
        return list(self)


class _FakeEmbedder:
    def encode(self, texts, show_progress_bar=False):
        return _FakeEncodeResult([[0.1, 0.2, 0.3]])


class _FakeCollection:
    def query(self, query_embeddings, n_results):
        return {"documents": [["dense1", "dense2"]]}


class _FakeBM25:
    def get_top_n(self, tokenized_query, corpus, n):
        return ["bm25a", "bm25b"]


class _FakeReranker:
    def __init__(self, scores):
        self._scores = scores
        self.received_pairs = None

    def predict(self, pairs):
        self.received_pairs = pairs
        return self._scores


def test_search_delegates_merge_to_reciprocal_rank_fusion_and_preserves_its_order(
    monkeypatch,
):
    kb = _kb()
    kb.embedder = _FakeEmbedder()
    kb.collection = _FakeCollection()
    kb.bm25 = _FakeBM25()
    kb.bm25_docs = []
    kb._bm25_dirty = False
    kb.relevance_threshold = -999.0
    kb.reranker = _FakeReranker([0.9, 0.5])

    fusion_calls = []

    def fake_fusion(self, ranked_lists, k=60):
        fusion_calls.append(ranked_lists)
        return [("docB", 0.9), ("docA", 0.5)]

    monkeypatch.setattr(
        KnowledgeBase, "reciprocal_rank_fusion", fake_fusion, raising=False
    )

    kb.search("test query")

    assert len(fusion_calls) == 1, (
        f"Expected reciprocal_rank_fusion to be called exactly once, got "
        f"{len(fusion_calls)} calls: {fusion_calls}"
    )
    assert fusion_calls[0] == [["dense1", "dense2"], ["bm25a", "bm25b"]], (
        "search() must pass dense_results and bm25_results as two separate "
        f"ranked lists in dense-then-bm25 order. Got: {fusion_calls[0]}"
    )

    assert kb.reranker.received_pairs == [
        ["test query", "docB"],
        ["test query", "docA"],
    ], (
        "reranker.predict() must receive candidates in exactly the fusion's "
        f"returned order. Got: {kb.reranker.received_pairs}"
    )
