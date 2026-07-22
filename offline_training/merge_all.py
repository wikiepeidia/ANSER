"""
merge_all.py — NGÀY 5, bước 1
Gộp 5 nguồn dữ liệu thành train_retail_v2.jsonl

Lọc bỏ:
  - Mẫu không có <think>
  - Mẫu trùng lặp (theo hash nội dung assistant)
  - Mẫu Module C sai format n8n (thiếu connections / typeVersion / position sai)
  - Mẫu có JSON bị cắt giữa chừng

CHẠY:  python offline_training/merge_all.py
"""
import json, re, hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
DATA = ROOT / "src" / "data"
OUT  = DATA / "train_retail_v2.jsonl"

SOURCES = [
    ("train_retail_base.jsonl", "base",     None),
    ("module_a_clean.jsonl",    "module_a", None),
    ("module_b.jsonl",          "module_b", None),
    ("module_c.jsonl",          "module_c", "n8n"),   # cần validate format n8n
    ("module_d.jsonl",          "module_d", None),
]


def split_think(content: str) -> tuple[str, str]:
    """Tách reasoning / answer, dùng </think> cuối cùng."""
    last = content.rfind("</think>")
    if last == -1:
        return "", content.strip()
    return content[:last].replace("<think>", "").strip(), content[last + 8:].strip()


def extract_json(text: str):
    """Parse JSON: markdown fence → brace matching."""
    for m in re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    depth, start = 0, -1
    for i, c in enumerate(text):
        if c == '{':
            if depth == 0:
                start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    start = -1
    return None


def validate_n8n(answer: str) -> tuple[bool, str]:
    obj = extract_json(answer)
    if obj is None:
        return False, "không parse được JSON"
    if "nodes" not in obj:
        return False, "thiếu nodes"
    if "connections" not in obj:
        return False, "thiếu connections"
    for n in obj.get("nodes", []):
        if "typeVersion" not in n:
            return False, "node thiếu typeVersion"
        if not isinstance(n.get("position"), list):
            return False, "position không phải mảng"
    return True, "ok"


def is_truncated(answer: str) -> bool:
    if "{" not in answer:
        return False
    return answer.count("{") != answer.count("}")


def main():
    seen, merged = set(), []
    report, reasons = {}, Counter()

    for fname, tag, check in SOURCES:
        path = DATA / fname
        if not path.exists():
            print(f"  ⚠ Không thấy {fname} — bỏ qua")
            report[tag] = (0, 0)
            continue

        n_in, n_ok = 0, 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            n_in += 1
            try:
                obj = json.loads(line)
            except Exception:
                reasons[f"{tag}: JSON dòng lỗi"] += 1
                continue

            msgs = obj.get("messages", [])
            if len(msgs) < 3:
                reasons[f"{tag}: thiếu messages"] += 1
                continue

            asst = msgs[-1].get("content", "")
            if "<think>" not in asst:
                reasons[f"{tag}: thiếu <think>"] += 1
                continue

            reasoning, answer = split_think(asst)

            if len(reasoning) < 150:
                reasons[f"{tag}: reasoning quá ngắn"] += 1
                continue

            if is_truncated(answer):
                reasons[f"{tag}: JSON bị cắt"] += 1
                continue

            if check == "n8n":
                valid, why = validate_n8n(answer)
                if not valid:
                    reasons[f"{tag}: n8n {why}"] += 1
                    continue

            # Dedup theo CÂU HỎI (khóa định danh thật) + đầu câu trả lời
            user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
            key  = (user.strip() + "||" + answer[:120]).encode("utf-8")
            h = hashlib.md5(key).hexdigest()
            if h in seen:
                reasons[f"{tag}: trùng lặp"] += 1
                continue
            seen.add(h)

            # Chuẩn hóa: 1 think block duy nhất
            msgs[-1]["content"] = f"<think>\n{reasoning}\n</think>\n{answer}"
            obj["_source"] = tag
            merged.append(obj)
            n_ok += 1

        report[tag] = (n_ok, n_in)
        print(f"  ✓ {fname:28s} {n_ok:4d} / {n_in:4d}")

    # ── Lưu (bỏ trường _source khỏi file cuối) ───────────────────────────
    OUT.write_text(
        "\n".join(json.dumps({"messages": m["messages"]}, ensure_ascii=False) for m in merged),
        encoding="utf-8"
    )

    # ── Thống kê ─────────────────────────────────────────────────────────
    lens = []
    for m in merged:
        a = m["messages"][-1]["content"]
        s, e = a.find("<think>") + 7, a.rfind("</think>")
        if e > s:
            lens.append(e - s)

    src_count = Counter(m["_source"] for m in merged)

    print(f"\n{'='*58}")
    print(f"  MERGE — train_retail_v2.jsonl")
    print(f"{'='*58}")
    print(f"\n  Phân bố nguồn:")
    for tag, (ok, total) in report.items():
        pct = ok / len(merged) * 100 if merged else 0
        bar = "█" * int(pct / 2)
        print(f"    {tag:12s} {ok:4d}  ({pct:4.1f}%)  {bar}")
    print(f"    {'TỔNG':12s} {len(merged):4d}")

    if reasons:
        print(f"\n  Lý do loại bỏ:")
        for r, c in reasons.most_common(12):
            print(f"    {c:4d}  {r}")

    if lens:
        print(f"\n  Chuỗi suy luận:")
        print(f"    Min {min(lens):6,}  Avg {sum(lens)//len(lens):6,}  Max {max(lens):6,} ký tự")

    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"\n  ✅ {OUT.name} — {len(merged)} mẫu, {size_mb:.1f} MB")

    if len(merged) < 1200:
        print(f"\n  ⚠ Dưới 1.200 mẫu — kiểm tra lại lý do loại bỏ ở trên")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    main()
