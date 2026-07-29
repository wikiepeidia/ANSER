"""
RAG-03: tests for KnowledgeBase.rebuild_collection().

Closes PITFALLS.md Pitfall 4: a smart_chunk() change alone has zero live
effect because ingest_folder()'s per-file `collection.get(where={"source":
filename})` dedupe check skips any file that already has entries in the
collection. rebuild_collection() must delete + recreate the persisted
collection FIRST so ingest_folder()'s dedupe check sees an empty store and
genuinely re-ingests (and re-chunks) every file, instead of skipping them all.

Uses fake ChromaDB client/collection and a fake embedder only -- no real
ChromaDB persistence, no real embedder, no network. Constructs
`kb = object.__new__(KnowledgeBase)` to bypass __init__/model loading, same
bare-instance pattern as test_smart_chunk.py and
tests/test_engine_concurrency.py.
"""

import sys
import tempfile
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.core.knowledge import KnowledgeBase  # noqa: E402


class _ListWithTolist(list):
    """Small list subclass so `.encode(...).tolist()` succeeds against a fake."""

    def tolist(self):
        return list(self)


class _FakeEmbedder:
    def encode(self, texts, show_progress_bar=False):
        # One fake embedding vector per input text -- shape/content don't
        # matter, only that `.tolist()` succeeds and lengths line up.
        return _ListWithTolist([[0.0, 0.0] for _ in texts])


class _FakeChromaCollection:
    def __init__(self):
        self._store = {}  # id -> {"document": ..., "metadata": ...}

    def get(self, where=None):
        if where and "source" in where:
            source = where["source"]
            ids = [
                doc_id
                for doc_id, entry in self._store.items()
                if entry["metadata"].get("source") == source
            ]
        else:
            ids = list(self._store.keys())
        documents = [self._store[doc_id]["document"] for doc_id in ids]
        return {"ids": ids, "documents": documents}

    def add(self, documents, embeddings, metadatas, ids):
        for doc_id, document, metadata in zip(ids, documents, metadatas):
            self._store[doc_id] = {"document": document, "metadata": metadata}

    def count(self):
        return len(self._store)


class _FakeChromaClient:
    def __init__(self):
        self._collections = {}
        self.deleted = []

    def get_or_create_collection(self, name):
        if name not in self._collections:
            self._collections[name] = _FakeChromaCollection()
        return self._collections[name]

    def delete_collection(self, name):
        self.deleted.append(name)
        self._collections.pop(name, None)


def _kb_with_fakes(doc_dir):
    kb = object.__new__(KnowledgeBase)
    kb.doc_dir = str(doc_dir)
    kb.client = _FakeChromaClient()
    kb.collection = kb.client.get_or_create_collection(name="project_a_docs")
    kb.embedder = _FakeEmbedder()
    kb._bm25_dirty = False
    return kb


def test_rebuild_replaces_stale_entries_instead_of_skipping_them():
    with tempfile.TemporaryDirectory() as tmp:
        doc_dir = Path(tmp)
        (doc_dir / "doc1.txt").write_text("Con meo rat de thuong.", encoding="utf-8")
        (doc_dir / "doc2.txt").write_text("Con cho rat trung thanh.", encoding="utf-8")

        kb = _kb_with_fakes(doc_dir)

        # Simulate the pre-Phase-6 "already ingested" state.
        kb.ingest_folder()
        assert len(kb.collection.get()["ids"]) == 2

        pre_rebuild_collection = kb.collection

        kb.rebuild_collection()

        assert kb.client.deleted == ["project_a_docs"], (
            f"Expected delete_collection('project_a_docs') called exactly "
            f"once, got: {kb.client.deleted}"
        )
        assert kb.collection is not pre_rebuild_collection, (
            "rebuild_collection() must reassign self.collection to a freshly "
            "created collection object after delete_collection(), so "
            "ingest_folder()'s dedupe check sees an empty store."
        )
        assert len(kb.collection.get()["ids"]) == 2, (
            "Expected both files re-ingested (not skipped) after rebuild."
        )


def test_rebuild_marks_bm25_dirty():
    with tempfile.TemporaryDirectory() as tmp:
        doc_dir = Path(tmp)
        (doc_dir / "doc1.txt").write_text("Con meo rat de thuong.", encoding="utf-8")

        kb = _kb_with_fakes(doc_dir)
        kb._bm25_dirty = False

        kb.rebuild_collection()

        assert kb._bm25_dirty is True, (
            "rebuild_collection() must set self._bm25_dirty = True so the "
            "next search() call's _ensure_bm25() rebuilds the BM25 index "
            "from the fresh, single-generation chunk set."
        )
