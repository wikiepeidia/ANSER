"""
rebuild_knowledge_base.py — RAG-03 live rebuild script.

This script must be run ONCE, on a live session with the real embedder/
reranker models and the real persisted `./data/vector_db`, after any
smart_chunk() change. It is intentionally NOT exercised by
tests/test_kb_rebuild.py (that test uses fake ChromaDB/embedder
collaborators only, no real models, no real persistence) — this script is
consumed by Plan 06-03's checkpoint, where a human actually runs it against
the real environment.

WHY THIS IS NEEDED:
  ingest_folder() skips any file whose `source` metadata already has
  entries in the collection (idempotent-by-filename ingest). That means a
  smart_chunk() code change alone has ZERO live effect on the persisted
  collection until it is explicitly rebuilt — otherwise every already-
  ingested file gets skipped and stale (old-boundary) chunks stay live
  forever (PITFALLS.md Pitfall 4).

RUN:  python offline_training/rebuild_knowledge_base.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.core.knowledge import KnowledgeBase  # noqa: E402


def main():
    # Constructing KnowledgeBase() already runs the constructor's own
    # initial ingest_folder() against whatever the persisted
    # ./data/vector_db currently holds.
    kb = KnowledgeBase()

    before = kb.collection.count()
    print(f"[rebuild_knowledge_base] Collection 'project_a_docs' before rebuild: {before} chunks")

    kb.rebuild_collection()

    after = kb.collection.count()
    print(f"[rebuild_knowledge_base] Collection 'project_a_docs' after rebuild:  {after} chunks")
    print(f"[rebuild_knowledge_base] Done — delta: {after - before:+d} chunks")


if __name__ == "__main__":
    main()
