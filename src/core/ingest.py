# -*- coding: utf-8 -*-
"""
ingest.py — Nạp corpus vào ChromaDB theo kiến trúc hai tầng.

Thay thế ingest_folder() + add_document() cũ. Bốn khác biệt:

  1. ĐỌC .meta.yaml   -> ngay_hieu_luc, huong_dan_cho, dieu_khoan_da_loi_thoi
                         vào metadata từng chunk, để Chroma lọc được
  2. CHUNK HAI TẦNG   -> index Khoản (chính xác), trả về Điều (đủ ngữ cảnh)
  3. TÁCH COLLECTION  -> phụ lục không cạnh tranh với điều khoản ở BM25
  4. DEDUPE THEO HASH -> đổi tên file không làm index trùng

Chunk cha KHÔNG được embed. Chúng nằm trong một collection riêng, tra bằng
parent_id sau khi chunk con thắng ở bước rerank.

Cách dùng:
    from src.core.ingest import CorpusIngestor
    CorpusIngestor(kb).ingest_all()
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from pathlib import Path

import yaml

from .corpus import chunker
from .corpus.reader import read as read_doc, NoTextLayer

logger = logging.getLogger("projecta.ingest")

# Thư mục -> collection mặc định. Metadata có thể ghi đè bằng trường 'collection'.
CORPUS_DIRS = {
    "legal":    "anser_legal",
    "appendix": "anser_legal_phuluc",
    "internal": "anser_internal",
    "market":   "anser_market",
}

PARENT_SUFFIX = "_parents"


class CorpusIngestor:
    def __init__(self, kb, corpus_root: str = "./src/data/corpus"):
        self.kb = kb
        self.root = Path(corpus_root)

    # ------------------------------------------------------- metadata

    @staticmethod
    def _load_meta(txt_path: Path) -> dict | None:
        """.meta.yaml đi kèm. Trả None nếu không có -> không ingest."""
        meta_path = txt_path.with_suffix("").with_suffix(".meta.yaml")
        if not meta_path.exists():
            meta_path = txt_path.parent / (txt_path.stem + ".meta.yaml")
        if not meta_path.exists():
            return None
        with open(meta_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _date_to_int(value) -> int | None:
        """
        Ngày -> số nguyên YYYYMMDD.

        Chroma chỉ so sánh $lte/$gte trên int/float; với chuỗi "2025-07-01" nó
        ném ValueError. Không chuyển thì filter hiệu lực không chạy được, và đó
        là cơ chế duy nhất ngăn bot trích dẫn quy định đã hết hiệu lực.
        """
        if value is None:
            return None
        s = str(value)
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        if not m:
            return None
        return int(m.group(1) + m.group(2) + m.group(3))

    @staticmethod
    def _flatten(meta: dict) -> dict:
        """
        Chroma chỉ nhận metadata vô hướng. Danh sách phải nối thành chuỗi,
        None phải bỏ hẳn (Chroma từ chối giá trị None).
        """
        out = {}
        for k, v in meta.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                out[k] = v
            elif isinstance(v, list) and all(
                    isinstance(x, (str, int, float)) for x in v):
                out[k] = ",".join(str(x) for x in v)
            elif isinstance(v, date):
                out[k] = v.isoformat()
        return out

    # ------------------------------------------------------- ingest

    def _collection(self, name: str):
        return self.kb.client.get_or_create_collection(name=name)

    def _already_ingested(self, coll, sha: str) -> bool:
        """
        Dedupe theo HASH NỘI DUNG, không theo tên file.

        Bản cũ dùng where={"source": filename}: ba bản sao cùng một nghị định
        có ba tên khác nhau nên lọt cả ba vào index.
        """
        try:
            hit = coll.get(where={"sha256": sha}, limit=1)
            return bool(hit and hit.get("ids"))
        except Exception:
            return False

    def ingest_file(self, path: Path, default_collection: str) -> dict:
        result = {"file": path.name, "status": "", "n_children": 0, "n_parents": 0}

        meta = self._load_meta(path)
        if meta is None:
            result["status"] = "BỎ QUA — thiếu .meta.yaml"
            return result

        if not meta.get("ingest", True):
            result["status"] = f"BỎ QUA — ingest:false ({meta.get('ly_do_khong_ingest','')[:50]})"
            return result

        if not meta.get("so_hieu"):
            result["status"] = "BỎ QUA — thiếu so_hieu"
            return result

        try:
            text = read_doc(path).text if path.suffix.lower() != ".txt" \
                else path.read_text(encoding="utf-8")
        except NoTextLayer as e:
            result["status"] = f"BỎ QUA — {e}"
            return result

        sha = hashlib.sha256(text.encode()).hexdigest()[:16]
        coll_name = meta.get("collection") or default_collection
        coll = self._collection(coll_name)

        if self._already_ingested(coll, sha):
            result["status"] = "đã có (trùng hash)"
            return result

        parents, children, warns = chunker.chunk(text, meta)
        if not children:
            result["status"] = "BỎ QUA — không cắt được chunk nào"
            result["warnings"] = warns
            return result

        base_meta = self._flatten(meta)

        # Ngày dạng số YYYYMMDD để Chroma so sánh được bằng $lte/$gte.
        # ngay_het_hieu_luc rỗng -> 99991231 (vô thời hạn), nhờ đó một điều kiện
        # $gte duy nhất phủ được cả văn bản còn hiệu lực lẫn đã hết hạn.
        base_meta["hieu_luc_tu"] = self._date_to_int(meta.get("ngay_hieu_luc")) or 0
        base_meta["hieu_luc_den"] = self._date_to_int(meta.get("ngay_het_hieu_luc")) or 99991231
        base_meta["sha256"] = sha
        base_meta["source"] = path.name
        base_meta["collection"] = coll_name

        # Điều khoản đã bị văn bản khác thay thế -> đánh dấu ở mức CHUNK,
        # không phải mức văn bản. NĐ 181 vẫn còn hiệu lực nhưng điểm g khoản 2
        # Điều 26 thì không; filter theo ngay_hieu_luc của cả văn bản sẽ cho lọt.
        docs, metas, ids = [], [], []
        for c in children:
            m = dict(base_meta)
            m.update({
                "dieu": str(c.dieu),
                "parent_id": c.parent_id,
                "tieu_de_dieu": c.tieu_de_dieu or "",
                "n_token": c.n_token,
            })
            if c.khoan is not None:
                m["khoan"] = c.khoan
            if c.diem:
                m["diem"] = c.diem

            # Khớp CHÍNH XÁC theo từng trường, không dùng tiền tố chuỗi.
            # startswith("dieu-4") khớp cả Điều 40; và một mục chỉ ghi dieu
            # (không ghi khoan) thì phải áp cho MỌI khoản của điều đó.
            for dk in (meta.get("dieu_khoan_da_loi_thoi") or []):
                if str(dk.get("dieu")) != str(c.dieu):
                    continue
                if dk.get("khoan") is not None and dk["khoan"] != c.khoan:
                    continue
                if dk.get("diem") and dk["diem"] != c.diem:
                    continue
                m["da_loi_thoi"] = True
                m["het_hieu_luc_tu"] = str(dk.get("het_hieu_luc_tu", ""))
                m["thay_the_boi"] = str(dk.get("thay_the_boi", ""))
                # Siết hạn của RIÊNG chunk này: văn bản vẫn còn hiệu lực
                # nhưng điều khoản này thì không.
                het = self._date_to_int(dk.get("het_hieu_luc_tu"))
                if het:
                    m["hieu_luc_den"] = het
                break

            docs.append(c.text)
            metas.append(m)
            ids.append(c.child_id)

        embeddings = self.kb.embedder.encode(docs, show_progress_bar=False).tolist()
        coll.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)

        # Chunk cha: lưu để tra theo parent_id, KHÔNG embed (không ai tìm chúng
        # bằng vector — chúng chỉ được kéo ra sau khi chunk con thắng rerank).
        pcoll = self._collection(coll_name + PARENT_SUFFIX)
        pcoll.add(
            documents=[p.text for p in parents],
            embeddings=[[1.0]] * len(parents),
            metadatas=[{
                "source": path.name, "sha256": sha,
                "so_hieu": str(meta["so_hieu"]),
                "dieu": str(p.dieu), "n_token": p.n_token,
            } for p in parents],
            ids=[p.parent_id for p in parents],
        )

        self.kb._bm25_dirty = True
        result.update(status=f"OK -> {coll_name}",
                      n_children=len(children), n_parents=len(parents),
                      warnings=warns)
        return result

    def ingest_all(self) -> list[dict]:
        results = []
        for sub, coll_name in CORPUS_DIRS.items():
            folder = self.root / sub
            if not folder.is_dir():
                continue
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() not in (".txt", ".docx", ".pdf", ".md"):
                    continue
                r = self.ingest_file(path, coll_name)
                results.append(r)
                lvl = logger.warning if "BỎ QUA" in r["status"] else logger.info
                lvl("%-46s %s", path.name, r["status"])
                for w in r.get("warnings", []):
                    logger.warning("  ! %s", w)
        return results