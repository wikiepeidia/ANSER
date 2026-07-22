"""
validate_seeds.py — Kiểm tra chất lượng seed_prompts.jsonl trước khi gửi lên DeepSeek API.

CHẠY:  python offline_training/validate_seeds.py
"""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
SEED_FILE = ROOT / "offline_training" / "seed_prompts.jsonl"

REQUIRED_KEYS     = {"domain", "difficulty", "prompt"}
VALID_DOMAINS     = {"FINANCIAL", "RETRIEVAL", "TECHNICAL", "GENERAL", "ATISO"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
MIN_PROMPT_LEN    = 30   # ký tự
MAX_PROMPT_LEN    = 600  # ký tự

def validate():
    if not SEED_FILE.exists():
        print(f"❌ File không tồn tại: {SEED_FILE}")
        sys.exit(1)

    entries = []
    errors  = []

    for i, line in enumerate(SEED_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Dòng {i}: JSON không hợp lệ — {e}")
            continue

        # Key check
        missing = REQUIRED_KEYS - set(obj.keys())
        if missing:
            errors.append(f"Dòng {i}: Thiếu keys {missing}")
            continue

        # Domain check
        if obj["domain"] not in VALID_DOMAINS:
            errors.append(f"Dòng {i}: domain '{obj['domain']}' không hợp lệ")

        # Difficulty check
        if obj["difficulty"] not in VALID_DIFFICULTIES:
            errors.append(f"Dòng {i}: difficulty '{obj['difficulty']}' không hợp lệ")

        # Prompt length check
        plen = len(obj["prompt"])
        if plen < MIN_PROMPT_LEN:
            errors.append(f"Dòng {i}: prompt quá ngắn ({plen} ký tự)")
        if plen > MAX_PROMPT_LEN:
            errors.append(f"Dòng {i}: prompt quá dài ({plen} ký tự) — DeepSeek API tốn token")

        entries.append(obj)

    # Duplicate check
    prompts_seen = Counter(e["prompt"] for e in entries)
    for prompt, count in prompts_seen.items():
        if count > 1:
            errors.append(f"DUPLICATE ({count}x): '{prompt[:60]}...'")

    # ── Report ──
    print("\n" + "="*55)
    print("  SEED PROMPT VALIDATION REPORT")
    print("="*55)

    # Distribution
    domain_counts = Counter(e["domain"] for e in entries)
    diff_counts   = Counter(e["difficulty"] for e in entries)

    print(f"\n  Tổng số entries: {len(entries)}")
    print("\n  Phân bố theo domain:")
    for d in sorted(VALID_DOMAINS):
        bar = "█" * domain_counts.get(d, 0)
        print(f"    {d:12s}: {domain_counts.get(d,0):3d}  {bar}")

    print("\n  Phân bố theo độ khó:")
    for diff in ["easy", "medium", "hard"]:
        bar = "█" * diff_counts.get(diff, 0)
        print(f"    {diff:8s}: {diff_counts.get(diff,0):3d}  {bar}")

    # Độ dài prompt
    if entries:
        lens = [len(e["prompt"]) for e in entries]
        print(f"\n  Độ dài prompt:")
        print(f"    Min: {min(lens):4d} ký tự")
        print(f"    Max: {max(lens):4d} ký tự")
        print(f"    Avg: {sum(lens)//len(lens):4d} ký tự")

    # Ước tính chi phí DeepSeek API
    total_input_tokens  = sum(len(e["prompt"].split()) for e in entries) * 1.5
    est_output_tokens   = len(entries) * 1500
    cost_input  = (total_input_tokens  / 1_000_000) * 0.55
    cost_output = (est_output_tokens   / 1_000_000) * 2.19
    print(f"\n  Ước tính chi phí DeepSeek-R1 API (deepseek-reasoner):")
    print(f"    Input  tokens: ~{total_input_tokens:,.0f} → ${cost_input:.3f}")
    print(f"    Output tokens: ~{est_output_tokens:,.0f} (ước tính) → ${cost_output:.2f}")
    print(f"    TỔNG ƯỚC TÍNH: ~${cost_input + cost_output:.2f} USD")

    # Lỗi
    print(f"\n  Lỗi tìm thấy: {len(errors)}")
    if errors:
        for e in errors[:20]:
            print(f"    ❌ {e}")
        if len(errors) > 20:
            print(f"    ... và {len(errors)-20} lỗi khác")
        print("\n  ❌ VALIDATION FAILED — Sửa lỗi trước khi chạy training.py")
        sys.exit(1)
    else:
        print("\n  ✅ VALIDATION PASSED — File sẵn sàng gửi DeepSeek API")
        print(f"\n  Lệnh tiếp theo:")
        print(f"    export DEEPSEEK_API_KEY=sk-xxxx")
        print(f"    python offline_training/training.py")
    print("="*55 + "\n")

if __name__ == "__main__":
    validate()
