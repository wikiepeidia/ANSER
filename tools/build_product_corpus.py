#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_product_corpus.py — Chuyển san_pham_ngocduy.xlsx thành corpus RAG.

Sinh ra ba thứ:

    corpus/product/sp_<danh-muc>.txt   mô tả sản phẩm, gom theo danh mục
    corpus/product/*.meta.yaml
    corpus/internal/thue_suat_san_pham.txt   bảng ánh xạ danh mục -> thuế suất

Bảng thuế suất là mảnh nối còn thiếu: luật nói về NHÓM NGÀNH, khách hàng hỏi
theo TÊN SẢN PHẨM. Không có nó, câu "trà thảo mộc chịu thuế bao nhiêu %" bị
reranker chấm 0.038 — đúng, vì corpus pháp lý không có một chữ nào về trà.

CỘT BỊ LOẠI Ở TẦNG PIPELINE (không để phụ thuộc prompt):
    Giá nhập      dữ liệu nội bộ — lọt vào index là bot đọc giá vốn cho khách
    Hàng tồn kho  đổi hàng ngày, phải truy vấn SQL chứ không vector hóa

Cách dùng:
    python tools/build_product_corpus.py san_pham_ngocduy.xlsx
    python tools/build_product_corpus.py san_pham_ngocduy.xlsx --out src/data/corpus
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

for _n in ("stdout", "stderr"):
    _s = getattr(sys, _n)
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        setattr(sys, _n, io.TextIOWrapper(_s.buffer, encoding="utf-8",
                                          errors="replace", line_buffering=True))

# Cột KHÔNG BAO GIỜ được đưa vào index. Chặn ở đây, không chặn bằng prompt.
CAM_TUYET_DOI = {"Giá nhập", "Hàng tồn kho"}

# Cột không mang thông tin cho người hỏi
BO_QUA = {"Ảnh sản phẩm", "ID Woo", "Slug", "Đơn vị tiền", "Danh mục"}

# --- Thuế suất theo danh mục -----------------------------------------
# 'khong_chiu_thue' KHÁC '0%': không chịu thuế thì KHÔNG được khấu trừ thuế
# đầu vào, còn 0% thì được. Nhầm hai cái này là sai bản chất, không phải sai
# con số.
THUE_SUAT = {
    "CAO MỀM": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến thành sản phẩm khác (nấu cô đặc). Thuế suất 10%, "
              "được giảm 2% còn 8% đến hết 31/12/2026."),
    "CAO NƯỚC": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến thành sản phẩm khác. 10% giảm còn 8%."),
    "TRÀ ATISO": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến (phối trộn, đóng túi lọc). 10% giảm còn 8%."),
    "TRÀ THẢO MỘC": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến (phối trộn nhiều loại thảo mộc). 10% giảm còn 8%."),
    "TRÀ XANH": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến (sao, vò, đóng gói thành trà). 10% giảm còn 8%."),
    "TRÀ OLONG": dict(
        suat="8%", loai="giam_2pt",
        can_cu="NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP",
        ly_do="Đã chế biến (lên men bán phần). 10% giảm còn 8%."),
    "THẢO MỘC SẤY KHÔ": dict(
        suat="không chịu thuế", loai="khong_chiu_thue",
        can_cu="khoản 1 Điều 5 Luật 48/2024/QH15, khoản 1 Điều 4 NĐ 181/2025/NĐ-CP",
        ly_do="Sản phẩm cây trồng TỰ TRỒNG, chỉ qua sơ chế thông thường. "
              "Điều 4 khoản 1 NĐ 181/2025 liệt kê 'phơi, sấy khô' và 'cắt' "
              "trong danh mục sơ chế thông thường."),
}

CANH_BAO_KHAU_TRU = """\
LƯU Ý QUAN TRỌNG — KHÔNG CHỊU THUẾ KHÁC VỚI THUẾ SUẤT 0%

    Không chịu thuế : không có thuế đầu ra, KHÔNG được khấu trừ thuế đầu vào
    Thuế suất 0%    : không có thuế đầu ra, ĐƯỢC khấu trừ thuế đầu vào

Với nhóm THẢO MỘC SẤY KHÔ, chi phí đầu vào (bao bì, vận chuyển, điện sấy)
KHÔNG được khấu trừ. Nếu đang khấu trừ thì cần rà soát lại.

Điều kiện áp dụng: phải là hàng TỰ TRỒNG và bán ra. Nếu mua đi bán lại thì
áp dụng quy định khác — xem khoản 1 Điều 5 và Điều 9 Luật 48/2024/QH15.
"""

RANH_GIOI = """\
RANH GIỚI PHÂN LOẠI

Ranh giới không nằm ở tên gọi mà ở chỗ CÓ LÀM RA SẢN PHẨM MỚI HAY KHÔNG.

    Chỉ làm sạch, phơi, sấy khô, cắt, xay      -> sơ chế thông thường
    Nấu cô đặc, phối trộn, lên men, đóng túi   -> chế biến thành sản phẩm khác

Sản phẩm cần rà lại thủ công: mặt hàng nào chỉ là lá hoặc hoa sấy khô đóng
gói, dù tên có chữ "trà", vẫn thuộc nhóm sơ chế thông thường chứ không phải
đã chế biến.
"""


def slug(text: str) -> str:
    s = text.lower()
    for a, b in [("àáảãạăằắẳẵặâầấẩẫậ", "a"), ("èéẻẽẹêềếểễệ", "e"),
                 ("ìíỉĩị", "i"), ("òóỏõọôồốổỗộơờớởỡợ", "o"),
                 ("ùúủũụưừứửữự", "u"), ("ỳýỷỹỵ", "y"), ("đ", "d")]:
        for ch in a:
            s = s.replace(ch, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def doc_xlsx(path: Path) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb["Tổng sản phẩm"] if "Tổng sản phẩm" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.values)
    header = [str(h).strip() if h else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        out.append({h: v for h, v in zip(header, r) if h})
    return out


def viet_san_pham(sp: dict) -> str:
    """Một sản phẩm -> đoạn text. Giá nhập và tồn kho bị loại tại đây."""
    dong = [f"Mã sản phẩm: {sp.get('Mã sản phẩm')}",
            f"Tên: {sp.get('Tên sản phẩm')}"]
    dm = sp.get("Danh mục chính")
    if dm:
        dong.append(f"Danh mục: {dm}")
        t = THUE_SUAT.get(str(dm).upper())
        if t:
            dong.append(f"Thuế suất GTGT: {t['suat']} ({t['can_cu']})")
    gia = sp.get("Giá bán")
    if gia:
        try:
            dong.append(f"Giá bán: {int(float(gia)):,} VNĐ".replace(",", "."))
        except (TypeError, ValueError):
            dong.append(f"Giá bán: {gia} VNĐ")
    mo_ta = str(sp.get("Mô tả") or "").strip()
    if mo_ta:
        dong.append(f"Mô tả: {re.sub(r'\s+', ' ', mo_ta)}")
    link = sp.get("Link sản phẩm")
    if link:
        dong.append(f"Link: {link}")
    return "\n".join(dong)


def meta_yaml(so_hieu: str, ten: str, n: int, sha: str, collection: str,
              linh_vuc: str) -> str:
    return f"""\
# {ten}
so_hieu: "{so_hieu}"
loai_vb: du_lieu_san_pham
co_quan: "Ngọc Duy Group"

# Không phải văn bản QPPL nên không có ngày ban hành. Đặt mốc đủ sớm để
# filter hiệu lực luôn cho qua.
ngay_hieu_luc: 2024-01-01
ngay_het_hieu_luc: null
trang_thai: con_hieu_luc

linh_vuc: [{linh_vuc}]
huong_dan_cho: []

ngay_tai: {date.today().isoformat()}
dinh_dang_goc: xlsx
file_goc: "san_pham_ngocduy.xlsx"
sha256_txt: "{sha}"
n_san_pham: {n}

ingest: true
collection: {collection}

# Giá nhập và tồn kho ĐÃ BỊ LOẠI ở tầng pipeline (build_product_corpus.py),
# không phụ thuộc vào prompt. Giá nhập là dữ liệu nội bộ; tồn kho đổi hàng
# ngày nên phải truy vấn SQL qua saas_api.py chứ không vector hóa.
cot_bi_loai: [gia_nhap, hang_ton_kho]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--out", default="src/data/corpus")
    args = ap.parse_args()

    root = Path(args.out)
    d_prod = root / "product"
    d_int = root / "internal"
    d_prod.mkdir(parents=True, exist_ok=True)
    d_int.mkdir(parents=True, exist_ok=True)

    sps = doc_xlsx(Path(args.xlsx))
    print(f"Đọc {len(sps)} sản phẩm từ {args.xlsx}\n")

    # --- kiểm tra an toàn -------------------------------------------
    co_cam = [c for c in CAM_TUYET_DOI if any(c in sp for sp in sps)]
    if co_cam:
        print(f"  Cột nhạy cảm phát hiện và SẼ BỊ LOẠI: {', '.join(co_cam)}")

    # --- gom theo danh mục ------------------------------------------
    theo_dm = defaultdict(list)
    for sp in sps:
        theo_dm[str(sp.get("Danh mục chính") or "KHÁC").upper()].append(sp)

    thieu = [dm for dm in theo_dm if dm not in THUE_SUAT]
    if thieu:
        print(f"  CẢNH BÁO: danh mục chưa có thuế suất: {', '.join(thieu)}")
        print("            -> bổ sung vào THUE_SUAT trước khi dùng cho tính thuế\n")

    tong_chunk = 0
    for dm, items in sorted(theo_dm.items()):
        t = THUE_SUAT.get(dm, {})
        head = [f"DANH MỤC SẢN PHẨM: {dm}",
                f"Số lượng: {len(items)} sản phẩm"]
        if t:
            head.append(f"Thuế suất GTGT: {t['suat']}")
            head.append(f"Căn cứ: {t['can_cu']}")
            head.append(f"Lý do: {t['ly_do']}")
        body = "\n\n".join(viet_san_pham(sp) for sp in items)
        text = "\n".join(head) + "\n\n" + body + "\n"

        name = f"sp_{slug(dm)}"
        (d_prod / f"{name}.txt").write_text(text, encoding="utf-8")
        sha = hashlib.sha256(text.encode()).hexdigest()[:16]
        (d_prod / f"{name}.meta.yaml").write_text(
            meta_yaml(name, f"Sản phẩm nhóm {dm}", len(items), sha,
                      "anser_product", "san_pham"),
            encoding="utf-8")
        tong_chunk += len(items)
        suat = t.get("suat", "CHƯA XÁC ĐỊNH")
        print(f"  {dm:<22}{len(items):>3} SP   thuế {suat}")

    # --- bảng thuế suất ---------------------------------------------
    lines = [
        "BẢNG THUẾ SUẤT GTGT THEO DANH MỤC SẢN PHẨM NGỌC DUY",
        "",
        "Áp dụng cho kỳ 01/7/2025 đến 31/12/2026.",
        "Bảng này nối TÊN SẢN PHẨM với NHÓM NGÀNH mà văn bản pháp luật quy định.",
        "",
    ]
    for dm, items in sorted(theo_dm.items()):
        t = THUE_SUAT.get(dm)
        lines.append(f"--- {dm} ({len(items)} sản phẩm) ---")
        if t:
            lines.append(f"Thuế suất GTGT: {t['suat']}")
            lines.append(f"Căn cứ pháp lý: {t['can_cu']}")
            lines.append(f"Giải thích: {t['ly_do']}")
        else:
            lines.append("Thuế suất: CHƯA XÁC ĐỊNH — cần rà soát trước khi áp dụng.")
        vd = ", ".join(str(sp.get("Tên sản phẩm"))[:40] for sp in items[:3])
        lines.append(f"Ví dụ sản phẩm: {vd}")
        lines.append("")

    lines += ["", CANH_BAO_KHAU_TRU, "", RANH_GIOI]
    text = "\n".join(lines)
    (d_int / "thue_suat_san_pham.txt").write_text(text, encoding="utf-8")
    sha = hashlib.sha256(text.encode()).hexdigest()[:16]
    (d_int / "thue_suat_san_pham.meta.yaml").write_text(
        meta_yaml("thue_suat_san_pham", "Bảng thuế suất GTGT theo danh mục",
                  len(sps), sha, "anser_internal", "thue_gtgt, san_pham"),
        encoding="utf-8")

    print(f"\n  -> {d_prod}/  ({len(theo_dm)} file, {tong_chunk} sản phẩm)")
    print(f"  -> {d_int}/thue_suat_san_pham.txt")
    print("\n  Nhớ thêm 'product' vào CORPUS_DIRS trong src/core/ingest.py:")
    print('      "product": "anser_product",\n')


if __name__ == "__main__":
    main()
