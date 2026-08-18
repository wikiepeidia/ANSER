#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_rag.py — Đo chất lượng truy hồi RAG trên bộ 70 câu hỏi.

Đo 5 chỉ số:

    recall@k          điều khoản đúng có nằm trong chunk trả về không
    citation_ok       trích dẫn sinh ra có khớp chunk thật không
    staleness_rate    tỷ lệ trích văn bản/điều khoản đã hết hiệu lực  -> mục tiêu 0
    refusal_ok        câu ngoài phạm vi có bị từ chối không
    latency_ms        thời gian truy hồi (KHÔNG gồm sinh câu trả lời)

Chỉ đo TRUY HỒI, không cần vLLM. Chạy được trên Colab free.

    python tools/eval_rag.py
    python tools/eval_rag.py --top-k 6 --threshold 0.35
    python tools/eval_rag.py --compare baseline.json
"""

from __future__ import annotations

import argparse
import io
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

for _n in ("stdout", "stderr"):
    _s = getattr(sys, _n)
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        setattr(sys, _n, io.TextIOWrapper(_s.buffer, encoding="utf-8",
                                          errors="replace", line_buffering=True))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MUC_TIEU = {
    "recall": 0.85,
    "citation_ok": 0.95,
    "staleness_rate": 0.0,
    "refusal_ok": 0.95,
}


def build_kb(threshold: float | None):
    """
    Dựng KB tối giản: chỉ embedder + reranker, KHÔNG vLLM.

    KnowledgeBase thật kéo theo model 7B AWQ (~12GB VRAM, vài phút khởi động)
    cho một việc không dùng đến nó — đo truy hồi chỉ cần hai model nhỏ.
    """
    import chromadb
    import torch
    from sentence_transformers import SentenceTransformer, CrossEncoder

    dev = "cuda" if torch.cuda.is_available() else "cpu"

    class MiniKB:
        def __init__(self):
            self.client = chromadb.PersistentClient(path="./data/vector_db")
            self.embedder = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                device=dev)
            self.reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device=dev)
            self.relevance_threshold = (
                threshold if threshold is not None
                else float(__import__("os").getenv("KB_RELEVANCE_THRESHOLD", "0.0")))
            self._bm25_dirty = False
            self.collection = self.client.get_or_create_collection(
                name="project_a_docs")

        def reciprocal_rank_fusion(self, ranked_lists, k=60):
            scores = {}
            for lst in ranked_lists:
                for rank, doc in enumerate(lst, start=1):
                    scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
            return sorted(scores.items(), key=lambda p: p[1], reverse=True)

    return MiniKB()


def cham_mot_cau(case: dict, hits: list[dict], cites: list[dict]) -> dict:
    """Chấm một câu hỏi. Trả về dict các chỉ số nhị phân."""
    r = {"nhom": case["nhom"], "cau": case["cau"], "n_hits": len(hits)}

    # --- câu ngoài phạm vi: đúng khi TỪ CHỐI ---
    if case["dieu_dung"] is None:
        r["refusal_ok"] = len(hits) == 0
        r["nguon"] = sorted({h["meta"].get("so_hieu", "?") for h in hits})
        return r

    # --- recall: chunk trả về có chứa điều khoản đúng không ---
    got = {(h["meta"].get("so_hieu"), str(h["meta"].get("dieu")))
           for h in hits}
    want = {(so, str(d)) for so, d in case["dieu_dung"]}
    r["recall"] = bool(got & want)
    r["dieu_tra_ve"] = sorted(f"{s} Đ{d}" for s, d in got)
    r["dieu_can"] = sorted(f"{s} Đ{d}" for s, d in want)

    # --- citation: nhãn trích dẫn có khớp chunk thật không ---
    # Trích dẫn sinh từ metadata nên về nguyên tắc luôn khớp; kiểm tra ở đây
    # là để bắt lỗi ánh xạ (vd parent_id lệch làm sai số điều).
    ok = 0
    for c in cites:
        if any(c["so_hieu"] == h["meta"].get("so_hieu")
               and str(h["meta"].get("dieu")) in c["text"] for h in hits):
            ok += 1
    r["citation_ok"] = (ok == len(cites)) if cites else False

    # --- staleness: có chunk nào đã hết hiệu lực lọt vào không ---
    r["stale"] = any(h["meta"].get("da_loi_thoi") for h in hits)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--threshold", type=float, default=None,
                    help="ghi đè KB_RELEVANCE_THRESHOLD")
    ap.add_argument("--as-of", default=None,
                    help="ngày giao dịch YYYY-MM-DD (mặc định: hôm nay)")
    ap.add_argument("--out", default="eval_report.json")
    ap.add_argument("--compare", help="so với một báo cáo trước")
    ap.add_argument("--verbose", action="store_true",
                    help="in chi tiết từng câu sai")
    args = ap.parse_args()

    from tools.eval_dataset import EVAL_SET
    from src.core.retrieval import Retriever

    print("Nạp model (embedder + reranker)...")
    kb = build_kb(args.threshold)
    r = Retriever(kb)
    print(f"  ngưỡng = {kb.relevance_threshold}")
    print(f"  top_k  = {args.top_k}")
    print(f"  as_of  = {args.as_of or 'hôm nay'}\n")

    rows, latencies = [], []
    for i, case in enumerate(EVAL_SET, 1):
        t0 = time.perf_counter()
        try:
            hits = r.retrieve(case["cau"], top_k=args.top_k, as_of=args.as_of)
            cites = []
            if hits:
                _, cites = r.search_with_citations(case["cau"], top_k=args.top_k,
                                                   as_of=args.as_of)
        except Exception as e:
            print(f"  [{i:2d}] LỖI: {e}")
            hits, cites = [], []
        dt = (time.perf_counter() - t0) * 1000
        latencies.append(dt)

        row = cham_mot_cau(case, hits, cites)
        row["latency_ms"] = round(dt, 1)
        rows.append(row)

        mark = "."
        if case["dieu_dung"] is None:
            mark = "." if row.get("refusal_ok") else "X"
        else:
            mark = "." if row.get("recall") else "X"
            if row.get("stale"):
                mark = "S"
        print(f"  [{i:2d}/{len(EVAL_SET)}] {mark} {dt:6.0f}ms  {case['cau'][:56]}")

    # ---------------------------------------------------- tổng hợp
    by = defaultdict(list)
    for row in rows:
        by[row["nhom"]].append(row)

    print(f"\n{'=' * 76}")
    print(f"  {'nhóm':<16}{'n':>4}{'recall':>10}{'citation':>10}"
          f"{'stale':>8}{'refusal':>10}{'ms(p50)':>10}")
    print(f"{'=' * 76}")

    def rate(items, key):
        vals = [x[key] for x in items if key in x]
        return sum(vals) / len(vals) if vals else None

    tong = {}
    for nhom in ("tra_cuu", "tinh_toan", "hieu_luc", "ngu_canh", "ngoai_pham_vi"):
        items = by.get(nhom, [])
        if not items:
            continue
        rc = rate(items, "recall")
        ct = rate(items, "citation_ok")
        st = rate(items, "stale")
        rf = rate(items, "refusal_ok")
        p50 = statistics.median(x["latency_ms"] for x in items)
        tong[nhom] = dict(n=len(items), recall=rc, citation_ok=ct,
                          stale=st, refusal_ok=rf, p50_ms=p50)
        f = lambda v: "  —  " if v is None else f"{v:.2f}"
        print(f"  {nhom:<16}{len(items):>4}{f(rc):>10}{f(ct):>10}"
              f"{f(st):>8}{f(rf):>10}{p50:>10.0f}")

    co_dap_an = [x for x in rows if "recall" in x]
    ngoai = [x for x in rows if "refusal_ok" in x]
    tong_hop = {
        "recall": rate(co_dap_an, "recall"),
        "citation_ok": rate(co_dap_an, "citation_ok"),
        "staleness_rate": rate(co_dap_an, "stale"),
        "refusal_ok": rate(ngoai, "refusal_ok"),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted(latencies)[int(len(latencies) * .95)],
    }

    print(f"\n{'=' * 76}")
    print("  TỔNG HỢP")
    print(f"{'=' * 76}")
    for k, muc in MUC_TIEU.items():
        v = tong_hop.get(k)
        if v is None:
            continue
        dat = (v <= muc) if k == "staleness_rate" else (v >= muc)
        print(f"  {k:<20}{v:>8.3f}   mục tiêu {muc:<6} {'ĐẠT' if dat else 'CHƯA ĐẠT'}")
    print(f"  {'latency p50':<20}{tong_hop['latency_p50_ms']:>8.0f} ms")
    print(f"  {'latency p95':<20}{tong_hop['latency_p95_ms']:>8.0f} ms")

    # ---------------------------------------------------- chi tiết câu sai
    sai = [x for x in rows
           if (x.get("recall") is False) or (x.get("refusal_ok") is False)
           or x.get("stale")]
    if sai:
        print(f"\n{'=' * 76}")
        print(f"  {len(sai)} CÂU CẦN XEM")
        print(f"{'=' * 76}")
        for x in sai:
            ly_do = ("trích văn bản hết hiệu lực" if x.get("stale")
                     else "không từ chối" if x.get("refusal_ok") is False
                     else "trượt điều khoản đúng")
            print(f"\n  [{x['nhom']}] {x['cau'][:64]}")
            print(f"    -> {ly_do}")
            if args.verbose:
                if x.get("dieu_can"):
                    print(f"       cần   : {', '.join(x['dieu_can'])}")
                    print(f"       trả về: {', '.join(x['dieu_tra_ve']) or '(rỗng)'}")
                elif x.get("nguon"):
                    print(f"       lấy nhầm từ: {', '.join(x['nguon'])}")

    # ---------------------------------------------------- so sánh baseline
    if args.compare and Path(args.compare).exists():
        old = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        print(f"\n{'=' * 76}")
        print(f"  SO VỚI {args.compare}")
        print(f"{'=' * 76}")
        for k in ("recall", "citation_ok", "staleness_rate", "refusal_ok"):
            a, b = old["tong_hop"].get(k), tong_hop.get(k)
            if a is None or b is None:
                continue
            d = b - a
            arrow = "→" if abs(d) < 0.005 else ("↑" if d > 0 else "↓")
            print(f"  {k:<20}{a:>8.3f} {arrow} {b:.3f}  ({d:+.3f})")
        for k in ("latency_p50_ms",):
            a, b = old["tong_hop"].get(k), tong_hop.get(k)
            if a:
                print(f"  {k:<20}{a:>8.0f} → {b:.0f} ms  ({b - a:+.0f})")

    Path(args.out).write_text(json.dumps({
        "cau_hinh": {"top_k": args.top_k,
                     "threshold": kb.relevance_threshold,
                     "as_of": args.as_of},
        "tong_hop": tong_hop, "theo_nhom": tong, "chi_tiet": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  -> {args.out}\n")


if __name__ == "__main__":
    main()
