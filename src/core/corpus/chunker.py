# -*- coding: utf-8 -*-
"""
chunker.py — Cắt văn bản pháp luật thành hai tầng.

  Tầng CHA  (parent) = Điều, hoặc nhóm Khoản nếu Điều quá dài  <= 1200 token
  Tầng CON  (child)  = Khoản, hoặc Điểm nếu Khoản quá dài      <=  500 token

Vì sao hai tầng: embedding của đoạn ngắn sắc nét hơn nên tìm kiếm chính xác
hơn; nhưng trả lời đúng một câu hỏi pháp lý thường cần cả Điều, vì khoản 1
nêu quy tắc còn khoản 4 nêu ngoại lệ. Index theo Khoản, trả về theo Điều.

Cắt PHÂN CẤP một lượt: Điều -> gom Khoản thành khối cha -> sinh con bên trong
từng khối. Cách này đảm bảo mọi child luôn trỏ đúng parent chứa nó; cắt cha và
con độc lập sẽ làm lệch parent_id khi Điều bị chia nhỏ.

Chỉ khả thi khi max_model_len = 8192.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PARENT_MAX_TOKENS = 1200
CHILD_MAX_TOKENS = 500
CHARS_PER_TOKEN = 3.06        # đo thật bằng tokenizer Qwen2.5 trên corpus tiếng Việt

# Điều phải đứng đầu dòng VÀ có dấu chấm/hai chấm.
# Không có dấu chấm bắt buộc thì "tại Điều 5 của Luật này" giữa câu cũng khớp.
# Hậu tố chữ cái bắt buộc: luật VN dùng Điều 34a, 34b cho điều bổ sung.
RE_DIEU = re.compile(r"^[ \t]*Điều\s+(\d+)([a-zđ]?)\s*[.．:]\s*(.*)$", re.M)

# Văn bản hợp nhất chèn số chú thích ngay sau số khoản: "5.[7] Chứng từ..."
RE_KHOAN = re.compile(r"^[ \t]*(\d{1,2})\s*[.)]\s*(?:\[\d+\])?\s+(?=\S)", re.M)
RE_DIEM = re.compile(r"^[ \t]*([a-zđ])\)\s*(?:\[\d+\])?\s+(?=\S)", re.M)

RE_CHUONG = re.compile(r"^[ \t]*Chương\s+([IVXLCDM]+)\b\s*(.*)$", re.M)
RE_MUC = re.compile(r"^[ \t]*Mục\s+(\d+)\b\s*(.*)$", re.M)

# Nghị định/thông tư sửa đổi gói toàn bộ nội dung vào một Điều duy nhất.
RE_VB_SUA_DOI = re.compile(r"Sửa đổi,?\s*bổ sung|Bãi bỏ một số điều", re.I)

# Dòng đánh dấu phần chưa số hóa — không phải nội dung quy phạm.
RE_CHUA_SO_HOA = re.compile(r"^\s*\[CHƯA SỐ HÓA\]", re.M)


def n_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


@dataclass
class Parent:
    parent_id: str
    dieu: str
    tieu_de: str
    text: str
    chuong: str | None = None
    muc: str | None = None

    @property
    def n_token(self) -> int:
        return n_tokens(self.text)


@dataclass
class Child:
    child_id: str
    parent_id: str
    dieu: str
    khoan: int | None
    diem: str | None
    tieu_de_dieu: str
    text: str
    meta: dict = field(default_factory=dict)

    @property
    def n_token(self) -> int:
        return n_tokens(self.text)


# ------------------------------------------------------------- helpers

def _slug(so_hieu: str) -> str:
    return re.sub(r"[^0-9A-Za-zĐđ]+", "-", so_hieu).strip("-")


def _header(so_hieu: str, dieu: str, tieu_de: str,
            khoan: int | None = None, diem: str | None = None,
            khoan_range: str | None = None) -> str:
    """
    Header định danh gắn vào đầu MỌI chunk.

    Không có nó, chunk trở thành mồ côi: model không biết điều khoản thuộc văn
    bản nào, và reranker mất tín hiệu mạnh nhất để chấm điểm.
    """
    h = f"{so_hieu} — Điều {dieu}"
    if tieu_de:
        h += f". {tieu_de}"
    if khoan_range:
        h += f" — {khoan_range}"
    elif khoan is not None:
        h += f" — Khoản {khoan}"
        if diem:
            h += f" điểm {diem}"
    return h + ":"


def _spans(pattern, text: str):
    """[(start, end, match), ...] — end là start của lần khớp kế tiếp."""
    hits = list(pattern.finditer(text))
    return [(m.start(),
             hits[i + 1].start() if i + 1 < len(hits) else len(text),
             m)
            for i, m in enumerate(hits)]


def _context_marks(text: str):
    marks = [(m.start(), "chuong", m.group(1)) for m in RE_CHUONG.finditer(text)]
    marks += [(m.start(), "muc", m.group(1)) for m in RE_MUC.finditer(text)]
    return sorted(marks)


def _context_at(marks, pos: int):
    chuong = muc = None
    for offset, kind, val in marks:
        if offset > pos:
            break
        if kind == "chuong":
            chuong, muc = val, None      # sang chương mới thì reset mục
        else:
            muc = val
    return chuong, muc


# ------------------------------------------------------------- core

def _khoan_to_children(khoan_text: str, khoan_no: int, parent_id: str,
                       dieu: str, tieu_de: str, so_hieu: str) -> list[Child]:
    """Khoản quá dài -> cắt tiếp theo Điểm a), b), c)."""
    base = dict(parent_id=parent_id, dieu=dieu, tieu_de_dieu=tieu_de)

    if n_tokens(khoan_text) <= CHILD_MAX_TOKENS:
        return [Child(child_id=f"{parent_id}_k{khoan_no}",
                      khoan=khoan_no, diem=None,
                      text=f"{_header(so_hieu, dieu, tieu_de, khoan_no)}\n{khoan_text.strip()}",
                      **base)]

    diem_spans = _spans(RE_DIEM, khoan_text)
    if not diem_spans:
        # Không cắt được nữa (thường là bảng dài). Giữ nguyên; validate cảnh báo.
        return [Child(child_id=f"{parent_id}_k{khoan_no}",
                      khoan=khoan_no, diem=None,
                      text=f"{_header(so_hieu, dieu, tieu_de, khoan_no)}\n{khoan_text.strip()}",
                      **base)]

    out = []
    lead = khoan_text[:diem_spans[0][0]].strip()
    if lead:
        # Câu dẫn trước điểm a) — thường chứa điều kiện áp dụng, phải giữ
        out.append(Child(child_id=f"{parent_id}_k{khoan_no}_lead",
                         khoan=khoan_no, diem=None,
                         text=f"{_header(so_hieu, dieu, tieu_de, khoan_no)}\n{lead}",
                         **base))
    for s, e, m in diem_spans:
        diem = m.group(1)
        out.append(Child(child_id=f"{parent_id}_k{khoan_no}{diem}",
                         khoan=khoan_no, diem=diem,
                         text=f"{_header(so_hieu, dieu, tieu_de, khoan_no, diem)}\n"
                              f"{khoan_text[s:e].strip()}",
                         **base))
    return out


def _process_dieu(dieu_text: str, dieu: str, tieu_de: str, so_hieu: str,
                  chuong, muc) -> tuple[list[Parent], list[Child]]:
    """
    Một Điều -> (các khối cha, các chunk con).

    Child được sinh BÊN TRONG vòng lặp khối cha, nên parent_id luôn khớp.
    """
    slug = _slug(so_hieu)
    base_id = f"{slug}_dieu-{dieu}"
    khoan_spans = _spans(RE_KHOAN, dieu_text)

    if not khoan_spans:
        head = _header(so_hieu, dieu, tieu_de)
        body = dieu_text.strip()
        return ([Parent(base_id, dieu, tieu_de, f"{head}\n{body}", chuong, muc)],
                [Child(f"{base_id}_k0", base_id, dieu, None, None, tieu_de,
                       f"{head}\n{body}")])

    lead = dieu_text[:khoan_spans[0][0]].strip()

    blocks, cur = [], []
    for s, e, m in khoan_spans:
        seg, no = dieu_text[s:e], int(m.group(1))

        # Một Khoản đơn lẻ đã vượt ngân sách cha thì gom nhóm không cứu được.
        # Cắt riêng nó theo Điểm để chunk cha không phình ra vài nghìn token.
        if n_tokens(seg) > PARENT_MAX_TOKENS:
            if cur:
                blocks.append(cur)
                cur = []
            diem_spans = _spans(RE_DIEM, seg)
            if diem_spans:
                lead_seg = seg[:diem_spans[0][0]]
                sub, acc = [], lead_seg
                for ds, de, _dm in diem_spans:
                    piece = seg[ds:de]
                    if acc and n_tokens(acc + piece) > PARENT_MAX_TOKENS:
                        sub.append(acc)
                        acc = ""
                    acc += piece
                if acc.strip():
                    sub.append(acc)
                for piece in sub:
                    blocks.append([(piece, no)])
            else:
                blocks.append([(seg, no)])   # không cắt được, validate cảnh báo
            continue

        if cur and n_tokens("".join(x[0] for x in cur) + seg) > PARENT_MAX_TOKENS:
            blocks.append(cur)
            cur = []
        cur.append((seg, no))
    if cur:
        blocks.append(cur)

    parents, children = [], []
    multi = len(blocks) > 1

    for bi, block in enumerate(blocks, 1):
        nos = [no for _, no in block]
        pid = f"{base_id}_p{bi}" if multi else base_id
        rng = None
        if multi:
            rng = (f"Khoản {nos[0]}" if len(nos) == 1
                   else f"Khoản {nos[0]}–{nos[-1]}")

        head = _header(so_hieu, dieu, tieu_de, khoan_range=rng)
        body = "".join(seg for seg, _ in block).strip()
        if bi == 1 and lead:
            body = f"{lead}\n{body}"

        parents.append(Parent(pid, dieu, tieu_de, f"{head}\n{body}", chuong, muc))
        for seg, no in block:
            children.extend(_khoan_to_children(seg, no, pid, dieu, tieu_de, so_hieu))

    return parents, children


def chunk_flat(text: str, meta: dict, max_tokens: int = CHILD_MAX_TOKENS
               ) -> tuple[list[Parent], list[Child], list[str]]:
    """
    Cắt tài liệu KHÔNG có cấu trúc Điều: phụ lục, bảng danh mục, chính sách.

    Gom dòng liền kề cho tới ngưỡng token. Mỗi chunk mang header định danh để
    không mồ côi — với phụ lục thì header cho biết nó thuộc văn bản nào, thứ mà
    một dòng "2504.90.00 | Loại khác" tự nó không nói lên được.
    """
    so_hieu = meta.get("so_hieu", "?")
    ten = meta.get("ten_phu_luc") or meta.get("loai_vb", "phụ lục")
    slug = _slug(so_hieu)
    head = f"{so_hieu} — {ten}:"

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return [], [], ["File rỗng"]

    blocks, cur = [], []
    for line in lines:
        if cur and n_tokens("\n".join(cur) + line) > max_tokens:
            blocks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)

    parents, children = [], []
    scalar = {k: v for k, v in meta.items()
              if v is None or isinstance(v, (str, int, float, bool))}

    for i, block in enumerate(blocks, 1):
        pid = f"{slug}_flat-{i}"
        body = f"{head}\n" + "\n".join(block)
        parents.append(Parent(pid, "", ten, body))
        children.append(Child(f"{pid}_c", pid, "", None, None, ten, body,
                              meta=dict(scalar)))

    return parents, children, []


def chunk(text: str, meta: dict) -> tuple[list[Parent], list[Child], list[str]]:
    """
    Đầu vào: toàn văn + metadata từ .meta.yaml
    Đầu ra : (chunk cha, chunk con, cảnh báo)

    Mọi trường vô hướng trong meta được gắn vào từng child để Chroma lọc theo
    ngay_hieu_luc mà không phải join bảng.
    """
    so_hieu = meta["so_hieu"]
    warnings: list[str] = []

    # Dòng [CHƯA SỐ HÓA] là ghi chú vận hành, không phải nội dung quy phạm
    text = RE_CHUA_SO_HOA.sub("", text)

    marks = _context_marks(text)
    dieu_spans = _spans(RE_DIEU, text)

    if not dieu_spans:
        # Phụ lục, bảng danh mục, chính sách nội bộ — không có Điều nào.
        # Không phải lỗi; chỉ là loại tài liệu khác.
        return chunk_flat(text, meta)

    if len(dieu_spans) <= 3:
        s, e, m = dieu_spans[0]
        if RE_VB_SUA_DOI.search(m.group(3) or "") and n_tokens(text[s:e]) > 5000:
            warnings.append(
                f"Văn bản SỬA ĐỔI: {n_tokens(text[s:e]):,} token dồn vào Điều "
                f"{m.group(1)}. Mỗi khoản sửa một điều của văn bản gốc, nên chunk "
                "theo Điều không phản ánh đúng ngữ nghĩa. Cân nhắc dùng bản HỢP NHẤT.")

    # Kiểm tra chuỗi Điều liên tục — đứt quãng nghĩa là regex bỏ sót một mốc
    nums = [int(m.group(1)) for _, _, m in dieu_spans if not m.group(2)]
    for a, b in zip(nums, nums[1:]):
        if b > a + 1:
            warnings.append(f"Thiếu Điều {', '.join(str(x) for x in range(a + 1, b))}")
        elif b <= a:
            warnings.append(f"Điều {b} đứng sau Điều {a} — sai thứ tự")

    all_parents, all_children = [], []
    for s, e, m in dieu_spans:
        dieu = m.group(1) + (m.group(2) or "")        # "34" hoặc "34b"
        tieu_de = (m.group(3) or "").strip().rstrip(".")
        chuong, muc = _context_at(marks, s)
        P, C = _process_dieu(text[s:e], dieu, tieu_de, so_hieu, chuong, muc)
        all_parents.extend(P)
        all_children.extend(C)

    scalar = {k: v for k, v in meta.items()
              if v is None or isinstance(v, (str, int, float, bool))}
    hdc = meta.get("huong_dan_cho") or []
    for c in all_children:
        c.meta = {**scalar, "huong_dan_cho": ",".join(str(x) for x in hdc) or None}

    pids = {p.parent_id for p in all_parents}
    orphans = [c.child_id for c in all_children if c.parent_id not in pids]
    if orphans:
        warnings.append(f"LỖI: {len(orphans)} chunk con trỏ tới parent_id không tồn tại")

    over = [p.parent_id for p in all_parents if p.n_token > PARENT_MAX_TOKENS * 1.2]
    if over:
        warnings.append(f"{len(over)} chunk cha vượt ngân sách >20%: {over[:3]}")

    return all_parents, all_children, warnings


def stats(parents: list[Parent], children: list[Child]) -> dict:
    pt = [p.n_token for p in parents] or [0]
    ct = [c.n_token for c in children] or [0]
    return {
        "n_parents": len(parents), "n_children": len(children),
        "parent_avg": sum(pt) // len(pt), "parent_max": max(pt),
        "child_avg": sum(ct) // len(ct), "child_max": max(ct),
        "parents_over": sum(1 for t in pt if t > PARENT_MAX_TOKENS),
        "children_over": sum(1 for t in ct if t > CHILD_MAX_TOKENS),
    }