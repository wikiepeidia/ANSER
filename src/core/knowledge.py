import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
import os
import glob
import logging
import uuid
import torch
from pypdf import PdfReader
import docx
from underthesea import word_tokenize
from rank_bm25 import BM25Okapi

logger = logging.getLogger("projecta.knowledge")

class KnowledgeBase:
    def __init__(self, persist_dir="./data/vector_db", doc_dir="./src/data/docs"):
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
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device=self.device)
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=self.device)

        # DB Setup
        os.makedirs(persist_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="project_a_docs")
        
        self.bm25 = None
        self.bm25_docs = []
        self._bm25_dirty = True

        self.ingest_folder()
        self._ensure_bm25()

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

    def smart_chunk(self, text, chunk_size=150, overlap=30):
        """3. Vietnamese Word-Boundary Aware Chunking (chunk_size in words)."""
        words = word_tokenize(text)
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - overlap
            if start >= len(words): break
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

    def search(self, query: str, top_k=3):
        self._ensure_bm25()
        candidates = []
        
        # Stage 1A: Dense Retrieval
        query_vec = self.embedder.encode([query], show_progress_bar=False).tolist()
        results = self.collection.query(query_embeddings=query_vec, n_results=10)
        
        if results['documents'] and results['documents'][0]:
            candidates.extend(results['documents'][0])
            
        # Stage 1B: Lexical (BM25) Retrieval
        if self.bm25:
            tokenized_query = word_tokenize(query.lower())
            bm25_results = self.bm25.get_top_n(tokenized_query, self.bm25_docs, n=5)
            candidates.extend(bm25_results)
            
        # Deduplicate
        candidates = list(set(candidates))
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
