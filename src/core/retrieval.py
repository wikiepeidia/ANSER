# -*- coding: utf-8 -*-
"""
retrieval.py — Truy hồi hai tầng cho corpus pháp lý.

Luồng:
    1. Mở rộng truy vấn   từ điển đồng nghĩa pháp lý        (0 token LLM)
    2. Dense + BM25       trên chunk CON, có filter hiệu lực
    3. RRF fusion         gộp hai danh sách xếp hạng
    4. Rerank             bge-reranker trên chunk CON (~400 token,
                          không chạm trần 512 của CrossEncoder)
    5. Cổng chất lượng    cắt theo ngưỡng đã hiệu chỉnh
    6. Nở chunk CHA       tra parent_id, khử trùng lặp
    7. Cắt ngân sách      dừng ở ~6.000 token (max_model_len 8192)

Không có lượt gọi LLM nào trong toàn bộ luồng.

Điểm mấu chốt là bước 6: reranker chấm chunk nhỏ (nơi nó mạnh nhất), model
đọc chunk lớn (nơi nó cần ngữ cảnh). Khoản 1 nêu quy tắc, khoản 4 nêu ngoại
lệ — trả về một khoản đơn lẻ thường cho câu trả lời đúng chữ mà sai ý.
"""

from __future__ import annotations

import logging
import re
from datetime import date

logger = logging.getLogger("projecta.retrieval")

# Cache BM25 giữa các truy vấn.
#
# Không cache thì mỗi câu hỏi phải get() toàn bộ collection, word_tokenize
# từng chunk bằng underthesea, rồi dựng lại BM25Okapi — với 459 chunk trên
# 2 collection là ~900 lần tokenize tiếng Việt cho MỘT câu hỏi, mất ~9 giây.
#
# Hai tầng cache:
#   _TOKEN_CACHE  chunk -> token, theo (collection, số chunk). Tốn nhất, và
#                 chỉ đổi khi corpus đổi.
#   _BM25_CACHE   index đã dựng, theo (collection, điều kiện lọc). Cùng một
#                 ngày giao dịch dùng lại được.
_TOKEN_CACHE: dict = {}
_BM25_CACHE: dict = {}


def clear_cache():
    """Gọi sau khi re-ingest, nếu không BM25 vẫn chạy trên chunk thế hệ cũ."""
    _TOKEN_CACHE.clear()
    _BM25_CACHE.clear()

PARENT_SUFFIX = "_parents"

# Ngân sách ngữ cảnh, suy ra từ max_model_len=8192 trừ system prompt (~200),
# câu hỏi + lịch sử (~400), max_new_tokens (1024) và đệm an toàn.
CONTEXT_BUDGET_TOKENS = 6000
CHARS_PER_TOKEN = 3.06

DENSE_N = 20
BM25_N = 20

# Người dùng nói tiếng đời thường, luật viết tiếng pháp lý. Không nối nhịp thì
# dense lẫn BM25 đều trượt. Đây là "query rewriting" bằng từ điển — cùng tác
# dụng, 0 token, ~0ms.
SYNONYMS = {
    "hóa đơn đỏ": "hóa đơn giá trị gia tăng",
    "thuế khoán": "phương pháp khoán thuế hộ kinh doanh",
    "bán online": "kinh doanh thương mại điện tử",
    "bán hàng online": "kinh doanh thương mại điện tử",
    "vat": "thuế giá trị gia tăng",
    "gtgt": "thuế giá trị gia tăng",
    "tncn": "thuế thu nhập cá nhân",
    "tndn": "thuế thu nhập doanh nghiệp",
    "ttđb": "thuế tiêu thụ đặc biệt",
    "hộ kd": "hộ kinh doanh",
    "hkd": "hộ kinh doanh",
    "xuất hóa đơn": "lập hóa đơn",
    "tiền mặt": "thanh toán không dùng tiền mặt",
    "giảm thuế": "giảm thuế giá trị gia tăng",
    "hoàn thuế": "hoàn thuế giá trị gia tăng",
    "mã số thuế": "mã số thuế người nộp thuế",
}

# Câu hỏi nào đọc collection nào. Phụ lục và báo cáo thị trường chỉ được
# truy vấn khi câu hỏi thật sự thuộc về chúng — trộn vào mặc định thì chúng
# cạnh tranh với điều khoản luật ở nhánh BM25 (từ khóa chung như "hàng hóa",
# "loại khác" xuất hiện dày đặc trong danh mục).
# Tên danh mục và mặt hàng thực tế của cửa hàng. Câu hỏi nhắc tới chúng phải
# chạm được anser_product (mô tả sản phẩm) và anser_internal (bảng thuế suất).
_PRODUCT_WORDS = [
    "trà", "chè", "cao mềm", "cao nước", "thảo mộc", "thảo dược",
    "atiso", "atisô", "olong", "ô long", "trà xanh", "sấy khô",
    "hà thủ ô", "linh chi", "khổ qua", "nhàu", "đinh lăng",
    "cà gai leo", "diệp hạ châu", "túi lọc",
]

ROUTE_HINTS = {
    "anser_legal_phuluc": re.compile(
        r"\b\d{4}\.\d{2}|mã hs|mã hàng|danh mục|khoáng sản|tỷ lệ %|tỷ lệ phần trăm",
        re.I),
    "anser_market": re.compile(
        r"thị trường|xu hướng|tăng trưởng|đối thủ|thị phần|báo cáo ngành|dự báo",
        re.I),
    # Bảng thuế suất theo danh mục nằm trong anser_internal. Nó là mắt xích
    # nối TÊN SẢN PHẨM (khách hỏi) với NHÓM NGÀNH (luật quy định) — thiếu nó,
    # câu "trà thảo mộc chịu thuế bao nhiêu %" bị reranker chấm 0.038 vì
    # corpus pháp lý không có một chữ nào về trà.
    "anser_internal": re.compile(
        r"cửa hàng|đổi trả|bảo hành|giao hàng|chính sách|shop"
        r"|" + r"|".join(_PRODUCT_WORDS), re.I),
    "anser_product": re.compile(
        r"sản phẩm|mặt hàng|giá bao nhiêu|còn hàng|mã sp|công dụng|thành phần"
        r"|" + r"|".join(_PRODUCT_WORDS), re.I),
}


# Thứ bậc hiệu lực pháp lý. Cùng một nội dung, Luật là căn cứ gốc còn Nghị
# định chỉ quy định chi tiết — trích dẫn Luật đúng hơn về mặt pháp lý.
#
# Không có ưu tiên này, văn bản dài chiếm hết top_k: NĐ 181 có 240 chunk còn
# Luật 48 chỉ 134, nên câu "thuế suất thông thường" trả về NĐ 181 Điều 31/39
# thay vì Luật 48 Điều 9.
#
# Cộng vào điểm rerank, không nhân — nhân sẽ làm một chunk lạc đề của Luật
# vượt qua chunk đúng của Thông tư.
HIERARCHY_BOOST = {
    "luat": 0.05,
    "nghi_quyet": 0.05,     # nghị quyết Quốc hội ngang luật
    "phap_lenh": 0.04,
    "nghi_dinh": 0.02,
    "quyet_dinh": 0.01,
    "thong_tu": 0.0,
    "vbhn": 0.02,
}


def hierarchy_boost(meta: dict) -> float:
    return HIERARCHY_BOOST.get(str(meta.get("loai_vb", "")).lower(), 0.0)


def n_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def expand_query(query: str) -> str:
    """Thêm thuật ngữ pháp lý tương ứng vào cuối truy vấn, giữ nguyên bản gốc."""
    low = query.lower()
    extra = [v for k, v in SYNONYMS.items() if k in low and v.lower() not in low]
    return f"{query} {' '.join(extra)}" if extra else query


def route_collections(query: str, default: str = "anser_legal") -> list[str]:
    """Collection nào cần truy vấn cho câu hỏi này."""
    cols = [default]
    for name, pattern in ROUTE_HINTS.items():
        if pattern.search(query):
            cols.append(name)
    return cols


def effectivity_filter(as_of: date | str | None = None) -> dict:
    """
    Điều kiện Chroma: chỉ lấy chunk có hiệu lực tại thời điểm as_of.

    Ngày lưu dạng số YYYYMMDD vì Chroma không so sánh $lte trên chuỗi.
    Chunk bị văn bản khác thay thế có hieu_luc_den riêng, nhỏ hơn của cả văn
    bản — nhờ đó filter bắt được cả trường hợp "nghị định còn hiệu lực nhưng
    một điểm đã bị thay".
    """
    if as_of is None:
        as_of = date.today()
    if isinstance(as_of, str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", as_of)
        d = int(m.group(1) + m.group(2) + m.group(3)) if m else 0
    else:
        d = as_of.year * 10000 + as_of.month * 100 + as_of.day
    return {"$and": [{"hieu_luc_tu": {"$lte": d}},
                     {"hieu_luc_den": {"$gte": d}}]}


class Retriever:
    def __init__(self, kb):
        self.kb = kb

    # ------------------------------------------------------- tầng 1

    def _dense(self, collection, query_vec, where) -> list[dict]:
        try:
            r = collection.query(query_embeddings=query_vec, n_results=DENSE_N,
                                 where=where)
        except Exception as e:
            logger.warning("dense query lỗi trên %s: %s", collection.name, e)
            return []
        if not r.get("ids") or not r["ids"][0]:
            return []
        return [{"id": i, "text": d, "meta": m}
                for i, d, m in zip(r["ids"][0], r["documents"][0], r["metadatas"][0])]

    def _bm25(self, collection, query, where) -> list[dict]:
        """
        BM25 phải lọc theo CÙNG điều kiện ngày với dense.

        Nếu không, nhánh lexical bypass filter và kéo về điều khoản đã hết
        hiệu lực — rồi RRF đẩy chúng lên cao vì chúng khớp từ khóa rất tốt.

        Index được cache: dựng lại mỗi truy vấn tốn ~4 giây cho một collection
        459 chunk, chủ yếu do underthesea.word_tokenize.
        """
        import json as _json

        from rank_bm25 import BM25Okapi
        from underthesea import word_tokenize

        key = (collection.name, _json.dumps(where, sort_keys=True, default=str))
        cached = _BM25_CACHE.get(key)

        if cached is None:
            try:
                data = collection.get(where=where, limit=5000)
            except Exception as e:
                logger.warning("bm25 get lỗi trên %s: %s", collection.name, e)
                return []
            docs = data.get("documents") or []
            if not docs:
                return []

            tok_key = (collection.name, len(docs))
            tokens = _TOKEN_CACHE.get(tok_key)
            if tokens is None or len(tokens) != len(docs):
                tokens = [word_tokenize(d.lower()) for d in docs]
                _TOKEN_CACHE[tok_key] = tokens
                logger.info("BM25: tokenize %d chunk của %s (chỉ lần đầu)",
                            len(docs), collection.name)

            cached = (BM25Okapi(tokens), docs, data["ids"], data["metadatas"])
            _BM25_CACHE[key] = cached

        bm25, docs, ids, metas = cached
        scores = bm25.get_scores(word_tokenize(query.lower()))
        order = sorted(range(len(docs)), key=lambda i: scores[i],
                       reverse=True)[:BM25_N]
        return [{"id": ids[i], "text": docs[i], "meta": metas[i]}
                for i in order if scores[i] > 0]

    # ------------------------------------------------------- tầng 2

    def _expand_parents(self, children: list[dict], budget: int) -> list[str]:
        """
        Chunk con thắng -> trả về chunk CHA chứa nó.

        Hai chunk con khác nhau có thể trỏ về cùng một cha; phải khử trùng lặp,
        nếu không cùng một Điều bị nhồi hai lần vào context — vừa tốn ngân sách
        vừa làm model tưởng điều đó quan trọng gấp đôi.
        """
        out, used, spent = [], set(), 0
        sep_cost = n_tokens("\n\n---\n\n")

        for c in children:
            meta = c.get("meta") or {}
            pid = meta.get("parent_id")
            coll_name = meta.get("collection", "anser_legal")

            text = None
            if pid and pid not in used:
                try:
                    pcoll = self.kb.client.get_or_create_collection(
                        name=coll_name + PARENT_SUFFIX)
                    got = pcoll.get(ids=[pid])
                    if got and got.get("documents"):
                        text = got["documents"][0]
                        used.add(pid)
                except Exception as e:
                    logger.debug("không lấy được parent %s: %s", pid, e)
            elif pid in used:
                continue          # cha này đã có trong context

            if text is None:
                text = c["text"]  # không có cha -> dùng chính chunk con

            t = n_tokens(text) + (sep_cost if out else 0)
            if spent + t > budget:
                # Đã có nội dung thì dừng hẳn, đừng cắt cụt giữa chừng —
                # một Điều bị cắt ngang còn tệ hơn là thiếu nó.
                if out:
                    break
                text = text[: int((budget - sep_cost) * CHARS_PER_TOKEN)]
                t = n_tokens(text)
            out.append(text)
            spent += t

        logger.info("Nở cha: %d chunk, ~%d token", len(out), spent)
        return out

    # ------------------------------------------------------- public

    def retrieve(self, query: str, top_k: int = 6, as_of=None,
                 budget: int = CONTEXT_BUDGET_TOKENS) -> list[dict]:
        expanded = expand_query(query)
        where = effectivity_filter(as_of)
        query_vec = self.kb.embedder.encode([expanded],
                                            show_progress_bar=False).tolist()

        pool: dict[str, dict] = {}
        ranked_lists = []
        for name in route_collections(query):
            try:
                coll = self.kb.client.get_or_create_collection(name=name)
            except Exception:
                continue
            if coll.count() == 0:
                continue
            for lst in (self._dense(coll, query_vec, where),
                        self._bm25(coll, expanded, where)):
                for item in lst:
                    pool[item["id"]] = item
                ranked_lists.append([i["id"] for i in lst])

        if not pool:
            logger.info("KB: không có ứng viên nào sau filter hiệu lực")
            return []

        fused = self.kb.reciprocal_rank_fusion(ranked_lists)
        candidates = [pool[i] for i, _ in fused if i in pool]

        pairs = [[expanded, c["text"]] for c in candidates]
        raw = self.kb.reranker.predict(pairs)

        # Ưu tiên thứ bậc: cộng sau khi rerank, trước khi cắt top_k. Cổng chất
        # lượng vẫn so ngưỡng trên điểm ĐÃ cộng, nên một chunk sát ngưỡng của
        # Luật sẽ qua còn chunk tương đương của Thông tư thì không — đúng ý đồ.
        scores = [float(s) + hierarchy_boost(c.get("meta") or {})
                  for s, c in zip(raw, candidates)]
        scored = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

        # Cổng chất lượng: dùng điểm reranker làm tín hiệu "đủ chưa", thay vì
        # bắt một model 7B tự chấm — nó gần như luôn gật đầu.
        relevant = [(s, c) for s, c in scored if s >= self.kb.relevance_threshold]
        if not relevant:
            logger.info("KB: không chunk nào vượt ngưỡng %.2f (cao nhất %.2f)",
                        self.kb.relevance_threshold,
                        scored[0][0] if scored else float("nan"))
            return []

        logger.info("KB: %d/%d chunk vượt ngưỡng, cao nhất %.2f",
                    len(relevant), len(scored), relevant[0][0])
        return [dict(c, score=float(s)) for s, c in relevant[:top_k]]

    def search(self, query: str, top_k: int = 6, as_of=None) -> str:
        """Giữ nguyên giao diện cũ: trả về chuỗi ghép, rỗng nếu không có gì."""
        children = self.retrieve(query, top_k=top_k, as_of=as_of)
        if not children:
            return ""
        return "\n\n---\n\n".join(self._expand_parents(children,
                                                       CONTEXT_BUDGET_TOKENS))

    def search_with_citations(self, query: str, top_k: int = 6, as_of=None):
        """
        Như search() nhưng kèm trích dẫn sinh TỪ METADATA, không để LLM viết.

        Trả về (context, [{'text': 'khoản 2 Điều 9 Luật 48/2024/QH15', ...}]).
        """
        children = self.retrieve(query, top_k=top_k, as_of=as_of)
        if not children:
            return "", []

        cites, seen = [], set()
        for c in children:
            m = c.get("meta") or {}
            parts = []
            if m.get("diem"):
                parts.append(f"điểm {m['diem']}")
            if m.get("khoan") is not None:
                parts.append(f"khoản {m['khoan']}")
            if m.get("dieu"):
                parts.append(f"Điều {m['dieu']}")
            ref = " ".join(parts)
            so = m.get("so_hieu", "")
            label = f"{ref} {so}".strip() if ref else so
            if label and label not in seen:
                seen.add(label)
                cites.append({
                    "text": label,
                    "so_hieu": so,
                    "tieu_de_dieu": m.get("tieu_de_dieu", ""),
                    "hieu_luc_tu": m.get("hieu_luc_tu"),
                    "da_loi_thoi": bool(m.get("da_loi_thoi")),
                    "thay_the_boi": m.get("thay_the_boi", ""),
                    "score": c.get("score"),
                })

        context = "\n\n---\n\n".join(
            self._expand_parents(children, CONTEXT_BUDGET_TOKENS))
        return context, cites