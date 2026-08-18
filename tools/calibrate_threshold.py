#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calibrate_threshold.py — Chọn KB_RELEVANCE_THRESHOLD bằng số liệu.

Ngưỡng hiện tại là 0.0, và comment trong knowledge.py mô tả thang điểm
ms-marco trong khi model thật là bge-reranker-v2-m3 — hai thang khác nhau.
Nghĩa là ngưỡng chưa từng được đo.

Cách làm: chạy reranker thật trên 30 câu TRONG lĩnh vực và 30 câu NGOÀI
lĩnh vực, so hai phân bố điểm, chọn ngưỡng tách chúng.

    python tools/calibrate_threshold.py
    python tools/calibrate_threshold.py --top-n 5 --out nguong.json
"""

from __future__ import annotations

import argparse
import io
import json
import statistics
import sys
from pathlib import Path

for _n in ("stdout", "stderr"):
    _s = getattr(sys, _n)
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        setattr(sys, _n, io.TextIOWrapper(_s.buffer, encoding="utf-8",
                                          errors="replace", line_buffering=True))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --- 30 câu TRONG lĩnh vực: corpus PHẢI trả lời được ------------------
IN_DOMAIN = [
    "Thuế suất thuế giá trị gia tăng đối với hàng hóa thông thường là bao nhiêu",
    "Mức thuế suất 5% áp dụng cho những hàng hóa dịch vụ nào",
    "Hàng hóa nào được áp dụng thuế suất 0%",
    "Trà thảo mộc chịu thuế giá trị gia tăng bao nhiêu phần trăm",
    "Hộ kinh doanh có doanh thu bao nhiêu thì không chịu thuế giá trị gia tăng",
    "Điều kiện khấu trừ thuế giá trị gia tăng đầu vào là gì",
    "Hóa đơn từ 5 triệu đồng trở lên cần chứng từ thanh toán nào",
    "Phương pháp khấu trừ thuế áp dụng cho đối tượng nào",
    "Phương pháp tính trực tiếp trên giá trị gia tăng là gì",
    "Tỷ lệ phần trăm tính thuế đối với hoạt động phân phối cung cấp hàng hóa",
    "Tỷ lệ tính thuế với dịch vụ xây dựng không bao thầu nguyên vật liệu",
    "Điều kiện hoàn thuế giá trị gia tăng đối với hàng xuất khẩu",
    "Cơ sở kinh doanh được hoàn thuế khi số thuế đầu vào chưa khấu trừ hết bao nhiêu",
    "Đối tượng nào không chịu thuế giá trị gia tăng",
    "Sản phẩm trồng trọt chưa chế biến có chịu thuế giá trị gia tăng không",
    "Dịch vụ y tế có thuộc đối tượng không chịu thuế không",
    "Thời điểm xác định thuế giá trị gia tăng đối với bán hàng hóa",
    "Giá tính thuế giá trị gia tăng được xác định thế nào",
    "Nghị quyết giảm 2% thuế giá trị gia tăng áp dụng đến khi nào",
    "Những nhóm hàng hóa nào không được giảm thuế giá trị gia tăng",
    "Dịch vụ viễn thông có được giảm thuế giá trị gia tăng không",
    "Hàng hóa chịu thuế tiêu thụ đặc biệt có được giảm 2% không",
    "Người nộp thuế giá trị gia tăng gồm những ai",
    "Hóa đơn chứng từ đối với hàng hóa dịch vụ bán ra được quy định thế nào",
    "Khấu trừ thuế đối với tài sản cố định là ô tô dưới 9 chỗ",
    "Hoàn thuế giá trị gia tăng đối với dự án đầu tư",
    "Cơ sở kinh doanh nộp thuế theo phương pháp khấu trừ cần điều kiện gì",
    "Thuế giá trị gia tăng đầu vào của hàng hóa xuất khẩu được xử lý thế nào",
    "Nhà cung cấp nước ngoài không có cơ sở thường trú nộp thuế thế nào",
    "Cửa hàng bán lẻ cần lưu giữ chứng từ gì để được khấu trừ thuế",
]

# --- 30 câu NGOÀI lĩnh vực: corpus KHÔNG trả lời được -----------------
# Cố ý chia ba mức khó, để thấy ngưỡng chịu được tới đâu.
OUT_DOMAIN = [
    # Hoàn toàn khác lĩnh vực (dễ loại)
    "Thủ tục ly hôn đơn phương cần giấy tờ gì",
    "Cách nấu phở bò ngon tại nhà",
    "Đội tuyển Việt Nam đá với ai tối nay",
    "Thời tiết Hà Nội ngày mai thế nào",
    "Làm sao để học tiếng Anh nhanh",
    "Giá vàng SJC hôm nay bao nhiêu",
    "Cách chữa đau lưng tại nhà",
    "Nên mua xe máy điện hãng nào",
    "Lịch thi tốt nghiệp THPT năm nay",
    "Cách trồng cây trong chậu",
    # Pháp luật nhưng khác ngành (khó vừa)
    "Thủ tục đăng ký kết hôn với người nước ngoài",
    "Mức phạt vi phạm nồng độ cồn khi lái xe",
    "Điều kiện hưởng lương hưu theo luật bảo hiểm xã hội",
    "Thủ tục xin cấp giấy phép xây dựng nhà ở",
    "Quy định về thời gian thử việc trong hợp đồng lao động",
    "Mức bồi thường khi thu hồi đất nông nghiệp",
    "Thủ tục đăng ký nhãn hiệu độc quyền",
    "Điều kiện nhập quốc tịch Việt Nam",
    "Quy định về nghỉ thai sản của lao động nữ",
    "Thủ tục khai nhận di sản thừa kế",
    # Thuế nhưng KHÔNG có trong corpus (khó nhất — corpus chỉ có GTGT)
    "Thuế thu nhập cá nhân từ tiền lương tính thế nào",
    "Biểu thuế lũy tiến từng phần có mấy bậc",
    "Giảm trừ gia cảnh cho người phụ thuộc là bao nhiêu",
    "Thuế thu nhập doanh nghiệp có thuế suất bao nhiêu",
    "Chi phí nào được trừ khi tính thuế thu nhập doanh nghiệp",
    "Lệ phí môn bài năm nay phải nộp bao nhiêu",
    "Thuế tài nguyên tính trên căn cứ nào",
    "Thuế bảo vệ môi trường với xăng dầu là bao nhiêu",
    "Thuế nhập khẩu ưu đãi đặc biệt theo hiệp định EVFTA",
    "Thuế sử dụng đất phi nông nghiệp tính thế nào",
]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def histogram(in_s: list[float], out_s: list[float], bins: int = 20) -> None:
    lo = min(in_s + out_s)
    hi = max(in_s + out_s)
    if hi == lo:
        return
    w = (hi - lo) / bins
    print(f"\n  Phân bố điểm  (I = trong lĩnh vực, O = ngoài)")
    print(f"  {'khoảng':>16}  {'':<42}")
    for b in range(bins):
        a, z = lo + b * w, lo + (b + 1) * w
        ci = sum(1 for x in in_s if a <= x < z or (b == bins - 1 and x == hi))
        co = sum(1 for x in out_s if a <= x < z or (b == bins - 1 and x == hi))
        if ci or co:
            print(f"  {a:7.3f}..{z:6.3f}  {'I' * ci}{'O' * co}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=3,
                    help="lấy điểm cao nhất của mấy chunk đầu (mặc định 3)")
    ap.add_argument("--out", default="threshold_report.json")
    args = ap.parse_args()

    print("Nạp KnowledgeBase (mất vài phút nếu build corpus lần đầu)...")
    from src.core.knowledge import KnowledgeBase
    kb = KnowledgeBase()
    from src.core.retrieval import Retriever, expand_query, effectivity_filter

    saved = kb.relevance_threshold
    kb.relevance_threshold = -999.0        # tắt cổng để thu điểm thô
    r = Retriever(kb)

    def top_scores(q: str) -> list[float]:
        hits = r.retrieve(q, top_k=args.top_n)
        return [h["score"] for h in hits if h.get("score") is not None]

    print(f"\nChạy {len(IN_DOMAIN)} câu TRONG lĩnh vực...")
    in_scores = []
    for i, q in enumerate(IN_DOMAIN, 1):
        s = top_scores(q)
        if s:
            in_scores.append(max(s))
        print(f"  [{i:2d}/{len(IN_DOMAIN)}] {max(s) if s else float('nan'):7.3f}  {q[:56]}")

    print(f"\nChạy {len(OUT_DOMAIN)} câu NGOÀI lĩnh vực...")
    out_scores = []
    for i, q in enumerate(OUT_DOMAIN, 1):
        s = top_scores(q)
        if s:
            out_scores.append(max(s))
        print(f"  [{i:2d}/{len(OUT_DOMAIN)}] {max(s) if s else float('nan'):7.3f}  {q[:56]}")

    kb.relevance_threshold = saved

    if not in_scores or not out_scores:
        sys.exit("Không thu được điểm — kiểm tra corpus đã ingest chưa.")

    print(f"\n{'=' * 74}")
    print(f"  {'':<22}{'TRONG lĩnh vực':>16}{'NGOÀI lĩnh vực':>18}")
    print(f"{'=' * 74}")
    for lbl, f in [("thấp nhất", min), ("trung vị", statistics.median),
                   ("trung bình", statistics.mean), ("cao nhất", max)]:
        print(f"  {lbl:<22}{f(in_scores):>16.3f}{f(out_scores):>18.3f}")
    print(f"  {'phân vị 5%':<22}{percentile(in_scores, .05):>16.3f}"
          f"{percentile(out_scores, .05):>18.3f}")
    print(f"  {'phân vị 95%':<22}{percentile(in_scores, .95):>16.3f}"
          f"{percentile(out_scores, .95):>18.3f}")

    histogram(in_scores, out_scores)

    # Quét ngưỡng: chọn theo F1 nhưng ưu tiên không bỏ sót câu hợp lệ.
    lo, hi = min(in_scores + out_scores), max(in_scores + out_scores)
    best = None
    rows = []
    for i in range(201):
        t = lo + (hi - lo) * i / 200
        tp = sum(1 for x in in_scores if x >= t)     # câu hợp lệ được nhận
        fn = len(in_scores) - tp                     # câu hợp lệ bị từ chối oan
        fp = sum(1 for x in out_scores if x >= t)    # câu lạc đề vẫn lọt
        tn = len(out_scores) - fp
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append((t, tp, fn, fp, tn, prec, rec, f1))
        if best is None or f1 > best[7]:
            best = rows[-1]

    print(f"\n{'=' * 74}")
    print("  Quét ngưỡng — vài mốc đáng chú ý")
    print(f"{'=' * 74}")
    print(f"  {'ngưỡng':>9}{'nhận đúng':>11}{'từ chối oan':>13}"
          f"{'lạc đề lọt':>12}{'F1':>8}")
    marks = [rows[int(len(rows) * p)] for p in (.1, .25, .5, .75, .9)]
    for t, tp, fn, fp, tn, pr, rc, f1 in marks:
        print(f"  {t:>9.3f}{tp:>11d}{fn:>13d}{fp:>12d}{f1:>8.3f}")

    t, tp, fn, fp, tn, pr, rc, f1 = best
    print(f"\n{'=' * 74}")
    print(f"  ĐỀ XUẤT: KB_RELEVANCE_THRESHOLD = {t:.3f}")
    print(f"{'=' * 74}")
    print(f"    nhận đúng câu hợp lệ : {tp}/{len(in_scores)}")
    print(f"    từ chối oan          : {fn}")
    print(f"    câu lạc đề vẫn lọt   : {fp}/{len(out_scores)}")
    print(f"    F1                   : {f1:.3f}")

    # Ngưỡng thận trọng: không từ chối oan câu hợp lệ nào.
    safe = min(in_scores)
    fp_safe = sum(1 for x in out_scores if x >= safe)
    print(f"\n  Phương án thận trọng (không bỏ sót câu hợp lệ nào): {safe:.3f}")
    print(f"    -> {fp_safe}/{len(out_scores)} câu lạc đề vẫn lọt")

    if min(in_scores) <= max(out_scores):
        print(f"\n  LƯU Ý: hai phân bố CHỒNG LẤN "
              f"(thấp nhất trong={min(in_scores):.3f} <= cao nhất ngoài={max(out_scores):.3f}). "
              f"\n  Không có ngưỡng nào tách sạch. Xem histogram để chọn theo mức đánh đổi "
              f"\n  bạn chấp nhận: thà từ chối oan, hay thà để lọt câu lạc đề.")

    Path(args.out).write_text(json.dumps({
        "de_xuat": round(t, 4), "than_trong": round(safe, 4),
        "f1": round(f1, 4), "in_scores": in_scores, "out_scores": out_scores,
        "top_n": args.top_n,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  -> {args.out}")
    print(f"\n  Áp dụng:  export KB_RELEVANCE_THRESHOLD={t:.3f}\n")


if __name__ == "__main__":
    main()
