import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
import os
import re
import glob
import logging
import uuid
import torch
from pypdf import PdfReader
import docx
from .ingest import CorpusIngestor
from .retrieval import Retriever
from underthesea import word_tokenize, sent_tokenize
from rank_bm25 import BM25Okapi

logger = logging.getLogger("projecta.knowledge")

class KnowledgeBase:
    def __init__(self, persist_dir="./data/vector_db", doc_dir="./src/data/corpus/legal"):
        # Ngưỡng điểm cross-encoder để coi là liên quan.
        # Tăng lên nếu vẫn lọt tài liệu lạc đề, giảm nếu bỏ sót.
        self.relevance_threshold = float(
            os.getenv("KB_RELEVANCE_THRESHOLD", "0.0")
        )
        logger.info("Initializing KnowledgeBase (hybrid search)")

        self.doc_dir = doc_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Compute device: %s", self.device.upper())

        # 2. Upgraded Models (Multilingual + Fast)
        # Embedder always stays on self.device -- only the reranker gets an
        # independent RERANKER_DEVICE override (AI-OPS-02's VRAM-freeing
        # lever), so embedder behavior for any existing caller never changes.
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device=self.device)
        self.reranker = CrossEncoder('BAAI/bge-reranker-v2-m3', device=self._resolve_reranker_device())

        # DB Setup
        os.makedirs(persist_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="project_a_docs")
        
        self.bm25 = None
        self.bm25_docs = []
        self._bm25_dirty = True

        CorpusIngestor(self).ingest_all()
        self._ensure_bm25()
        self.retriever = Retriever(self)

    def _resolve_reranker_device(self):
        """Independent device-placement override for the reranker only.

        `RERANKER_DEVICE` unset (or blank) -> falls back to `self.device`
        unchanged (no behavior change for any existing caller). Set (e.g.
        `RERANKER_DEVICE=cpu`) -> moves only the reranker off-GPU, freeing
        VRAM without touching vLLM's own slice or the embedder's device
        selection (09-RESEARCH.md's Architectural Responsibility Map: the
        reranker is the one candidate for CPU demotion). Whitespace/case
        noise (e.g. `" CPU "`) is normalized via strip().lower().
        """
        override = os.getenv("RERANKER_DEVICE", "").strip().lower()
        return override if override else self.device

    def _ensure_bm25(self):
        if not self._bm25_dirty:
            return
        all_data = self.collection.get()
        if all_data and all_data['documents']:
            self.bm25_docs = all_data['documents']
            tokenized_corpus = [word_tokenize(doc.lower()) for doc in self.bm25_docs]
            self.bm25 = BM25Okapi(tokenized_corpus)
        self._bm25_dirty = False

    def _read_file(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            reader = PdfReader(file_path)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        if ext == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        if ext in (".txt", ".md", ".json", ".py"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return ""

    def ingest_folder(self):
        files = glob.glob(os.path.join(self.doc_dir, "*.*"))
        logger.info("Scanning %s — found %d files", self.doc_dir, len(files))

        for file_path in files:
            filename = os.path.basename(file_path)
            existing = self.collection.get(where={"source": filename})
            if existing['ids']:
                continue

            try:
                text = self._read_file(file_path)
                if text.strip():
                    self.add_document(text, source=filename)
                    logger.info("Ingested: %s", filename)
            except Exception as e:
                logger.error("Failed to read document '%s': %s", filename, e, exc_info=True)

    def rebuild_collection(self):
        """Delete and recreate the persisted collection, then fully re-ingest.

        ingest_folder() skips any file whose `source` metadata already has
        entries in the collection (idempotent-by-filename ingest). That
        means a smart_chunk() change alone has zero live effect until the
        collection is explicitly emptied first -- otherwise every file gets
        skipped and stale (old-boundary) chunks stay live forever
        (PITFALLS.md Pitfall 4). This method always does a FULL delete +
        reingest (never a partial per-file rebuild), so the resulting chunk
        set is never a mix of old- and new-boundary chunks.
        """
        before_count = self.collection.count()
        logger.info(
            "rebuild_collection: starting rebuild of 'project_a_docs' (currently %d chunks)",
            before_count,
        )

        try:
            self.client.delete_collection(name="project_a_docs")
        except Exception as e:
            logger.warning(
                "rebuild_collection: delete_collection('project_a_docs') failed "
                "(collection may not exist yet) — continuing: %s",
                e,
            )

        self.collection = self.client.get_or_create_collection(name="project_a_docs")

        # Collection is now empty, so ingest_folder()'s per-file dedupe check
        # (collection.get(where={"source": filename})) finds no existing ids
        # for any file and re-reads/re-chunks every file in self.doc_dir with
        # the current smart_chunk() logic.
        self.ingest_folder()

        # Force the next search() call's _ensure_bm25() to rebuild the
        # lexical index from the fresh, single-generation chunk set — never
        # a mix of old- and new-boundary chunks (Pitfall 4).
        self._bm25_dirty = True

        after_count = self.collection.count()
        logger.info(
            "rebuild_collection: done — %d chunks before, %d chunks after",
            before_count,
            after_count,
        )

    def smart_chunk(self, text, chunk_size=150, overlap=30):
        """3. Sentence/structure-aware chunking (chunk_size in words).

        Packs whole sentences into chunks so a chunk boundary never falls
        inside a sentence, except the oversized-single-sentence fallback
        (a single sentence longer than chunk_size still gets word-sliced,
        the same math the previous word-count sliding window used, to
        guarantee bounded output instead of one giant unbounded chunk).
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        sentences = []
        for paragraph in paragraphs:
            sentences.extend(sent_tokenize(paragraph))

        if not sentences:
            return []

        chunks = []
        current = []
        current_count = 0

        for sentence in sentences:
            sentence_word_count = len(word_tokenize(sentence))

            if sentence_word_count > chunk_size:
                # Flush whatever's buffered before word-slicing the run-on sentence.
                if current:
                    chunks.append(" ".join(current))
                    current = []
                    current_count = 0

                words = word_tokenize(sentence)
                start = 0
                while start < len(words):
                    end = start + chunk_size
                    chunks.append(" ".join(words[start:end]))
                    start = end - overlap
                    if start >= len(words):
                        break
                continue

            if current and current_count + sentence_word_count > chunk_size:
                chunks.append(" ".join(current))

                # Reseed the buffer with an overlap of whole trailing sentences.
                overlap_count = 0
                carried = []
                for prev_sentence in reversed(current):
                    prev_count = len(word_tokenize(prev_sentence))
                    if overlap_count + prev_count > overlap:
                        break
                    carried.insert(0, prev_sentence)
                    overlap_count += prev_count
                current = carried
                current_count = overlap_count

            current.append(sentence)
            current_count += sentence_word_count

        if current:
            chunks.append(" ".join(current))

        return chunks

    def add_document(self, text: str, source: str = "manual_entry"):
        raw_chunks = self.smart_chunk(text)
        if not raw_chunks: return

        ids = [f"{source}_{i}" for i in range(len(raw_chunks))]
        embeddings = self.embedder.encode(raw_chunks, show_progress_bar=False).tolist()
        metadatas = [{"source": source} for _ in raw_chunks]

        self.collection.add(
            documents=raw_chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        self._bm25_dirty = True

    def reciprocal_rank_fusion(self, ranked_lists, k=60):
        """Merge multiple ranked candidate lists (e.g. dense + BM25) into a
        single deterministic, cross-list-aware order.

        For each document, its fused score is the sum, over every ranked
        list it appears in, of `1 / (k + rank)`, where `rank` is the
        document's 1-indexed position within that specific list. A document
        appearing near the top of two lists outranks one that only barely
        made a single list -- signal the previous set()-based dedupe merge
        could never express, and whose iteration order was non-deterministic
        run-to-run due to Python's per-process string-hash randomization.

        Returns a list of (doc, score) tuples ordered by descending fused
        score, each unique document appearing exactly once regardless of how
        many source lists it appeared in.
        """
        scores = {}
        for ranked_list in ranked_lists:
            for rank, doc in enumerate(ranked_list, start=1):
                scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
        return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)

    def search(self, query: str, top_k=3):
        self._ensure_bm25()

        # Stage 1A: Dense Retrieval
        query_vec = self.embedder.encode([query], show_progress_bar=False).tolist()
        results = self.collection.query(query_embeddings=query_vec, n_results=10)

        dense_results = (
            results['documents'][0]
            if results['documents'] and results['documents'][0]
            else []
        )

        # Stage 1B: Lexical (BM25) Retrieval
        if self.bm25:
            tokenized_query = word_tokenize(query.lower())
            bm25_results = self.bm25.get_top_n(tokenized_query, self.bm25_docs, n=5)
        else:
            bm25_results = []

        # Merge: Reciprocal Rank Fusion (RAG-02) -- replaces the previous
        # set()-based dedupe with a real, inspectable, deterministic fused
        # rank order that rewards cross-list agreement.
        fused = self.reciprocal_rank_fusion([dense_results, bm25_results])
        candidates = [doc for doc, score in fused]
        if not candidates:
            return ""

        # Stage 2: Cross-Encoder Reranking
        pairs = [[query, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)

        # Sort by score
        scored_docs = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

        # Stage 3: Lọc theo ngưỡng liên quan
        # Cross-encoder ms-marco cho logit: dương = liên quan, âm sâu = không liên quan.
        # Không lọc thì câu hỏi ngoài lĩnh vực vẫn nhận được tài liệu ngẫu nhiên
        # -> model bị nhồi ngữ cảnh sai -> sinh nội dung vô nghĩa.
        relevant = [(s, d) for s, d in scored_docs if s >= self.relevance_threshold]

        if not relevant:
            logger.info(
                "KB: không có tài liệu vượt ngưỡng %.1f (điểm cao nhất %.2f) — trả rỗng",
                self.relevance_threshold,
                scored_docs[0][0] if scored_docs else float("nan"),
            )
            return ""

        best_docs = [doc for _, doc in relevant[:top_k]]
        logger.info(
            "KB: %d/%d tài liệu vượt ngưỡng, điểm cao nhất %.2f",
            len(relevant), len(scored_docs), relevant[0][0],
        )
        return "\n\n---\n\n".join(best_docs)

    def search(self, query, top_k=6, as_of=None):
        return self.retriever.search(query, top_k=top_k, as_of=as_of)
