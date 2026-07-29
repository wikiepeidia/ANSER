"""
Session-wide stub module registration for packages pinned in requirements.txt
but not installed in this local dev environment (confirmed: `pypdf`, `docx`,
`rank_bm25` all raise ModuleNotFoundError here).

This module runs once per pytest session, before any sibling test module is
collected/imported, so `from src.core.knowledge import KnowledgeBase` never
fails on these three imports regardless of which test file/function is under
test. Mirrors tests/test_engine_concurrency.py's `vllm` stub pattern exactly,
including the `if "<name>" not in sys.modules:` presence-check idiom, so a
machine that DOES have the real package installed keeps using the real one.
"""

import sys
import types

# --- pypdf stub -------------------------------------------------------
# Matches src/core/knowledge.py::KnowledgeBase._read_file()'s `.pdf` branch:
#   reader = PdfReader(file_path)
#   "\n".join([page.extract_text() or "" for page in reader.pages])
if "pypdf" not in sys.modules:
    _pypdf_stub = types.ModuleType("pypdf")

    class _StubPdfReader:
        """No-op stand-in for pypdf.PdfReader — accepts any args, no pages."""

        def __init__(self, *args, **kwargs):
            self.pages = []

    _pypdf_stub.PdfReader = _StubPdfReader
    sys.modules["pypdf"] = _pypdf_stub

# --- docx stub ----------------------------------------------------------
# Matches src/core/knowledge.py::KnowledgeBase._read_file()'s `.docx` branch:
#   doc = docx.Document(file_path)
#   "\n".join([para.text for para in doc.paragraphs])
if "docx" not in sys.modules:
    _docx_stub = types.ModuleType("docx")

    class _StubDocument:
        """No-op stand-in for docx.Document — accepts any args, no paragraphs."""

        def __init__(self, *args, **kwargs):
            self.paragraphs = []

    _docx_stub.Document = _StubDocument
    sys.modules["docx"] = _docx_stub

# --- rank_bm25 stub -------------------------------------------------------
# Matches src/core/knowledge.py's `from rank_bm25 import BM25Okapi` and
# `_ensure_bm25()`/`search()`'s BM25Okapi(...).get_top_n(query, corpus, n)` use.
if "rank_bm25" not in sys.modules:
    _rank_bm25_stub = types.ModuleType("rank_bm25")

    class _StubBM25Okapi:
        """No-op stand-in for rank_bm25.BM25Okapi — accepts any args."""

        def __init__(self, *args, **kwargs):
            pass

        def get_top_n(self, query, corpus, n):
            return []

    _rank_bm25_stub.BM25Okapi = _StubBM25Okapi
    sys.modules["rank_bm25"] = _rank_bm25_stub
