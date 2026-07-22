"""
day1_test_batch.py — Test batch 20 prompts với DeepSeek-R1 thật.

MỤC TIÊU NGÀY HÔM NAY:
  Xác nhận deepseek-reasoner trả về reasoning_content đúng format,
  và output của mình tương thích 100% với data hiện có.

CÁCH CHẠY (trong Colab cell):
  import os
  from google.colab import userdata
  os.environ['DEEPSEEK_API_KEY'] = userdata.get('DEEPSEEK_API_KEY')

  !cd /content/ANSER_AI_FIX && python offline_training/day1_test_batch.py

KẾT QUẢ:
  src/data/distillation_v2_test.jsonl — 20 entries với real reasoning traces
"""

import os, sys, json, asyncio, time
from pathlib import Path
from openai import AsyncOpenAI

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Config ────────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL            = "deepseek-reasoner"   # DeepSeek-R1 với reasoning_content
TEMPERATURE      = 0.6                   # khuyến nghị cho R1
MAX_TOKENS       = 4096
CONCURRENT       = 4                     # request song song (free tier safe)
N_PER_DOMAIN     = 4                     # 4 prompts × 5 domains = 20 total

SYSTEM_PROMPT = (
    "You are Project A, an expert Retail Consultant for Vietnamese SMEs "
    "using the ANSER platform. Trả lời bằng tiếng Việt, chi tiết và có căn cứ."
)

OUT_FILE = ROOT / "src" / "data" / "distillation_v2_test.jsonl"

# ── Chọn 20 prompts đại diện từ seed_prompts.jsonl ───────────────────────────
def pick_test_prompts(seed_file: Path, n_per_domain: int) -> list[dict]:
    seeds = [json.loads(l) for l in seed_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    selected = []
    from collections import defaultdict
    by_domain = defaultdict(list)
    for s in seeds:
        by_domain[s["domain"]].append(s)
    # Lấy n_per_domain prompts từ mỗi domain (mix easy + medium + hard)
    for domain, items in by_domain.items():
        easy   = [x for x in items if x["difficulty"] == "easy"][:1]
        medium = [x for x in items if x["difficulty"] == "medium"][:2]
        hard   = [x for x in items if x["difficulty"] == "hard"][:1]
        selected.extend((easy + medium + hard)[:n_per_domain])
    return selected

# ── Gọi API ──────────────────────────────────────────────────────────────────
SEM = asyncio.Semaphore(CONCURRENT)

async def call_deepseek(client: AsyncOpenAI, prompt: str, domain: str, difficulty: str) -> dict | None:
    async with SEM:
        try:
            t0 = time.time()
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            elapsed = time.time() - t0
            msg = resp.choices[0].message

            reasoning = getattr(msg, "reasoning_content", None) or ""
            answer    = msg.content or ""

            if not reasoning:
                print(f"  ⚠ WARN: reasoning_content rỗng cho prompt: {prompt[:60]}...")

            entry = {
                "messages": [
                    {"role": "system",    "content": SYSTEM_PROMPT},
                    {"role": "user",      "content": prompt},
                    {"role": "assistant", "content": f"<think>\n{reasoning}\n</think>\n{answer}"},
                ],
                "_meta": {
                    "domain":           domain,
                    "difficulty":       difficulty,
                    "reasoning_chars":  len(reasoning),
                    "answer_chars":     len(answer),
                    "elapsed_s":        round(elapsed, 1),
                    "model":            MODEL,
                    "input_tokens":     resp.usage.prompt_tokens     if resp.usage else 0,
                    "output_tokens":    resp.usage.completion_tokens if resp.usage else 0,
                }
            }
            print(f"  ✓ [{domain:10s}/{difficulty:6s}] "
                  f"think={len(reasoning):4d}c  ans={len(answer):3d}c  {elapsed:.1f}s")
            return entry

        except Exception as e:
            print(f"  ✗ FAIL [{domain}]: {e}")
            return None

# ── Kiểm tra output ───────────────────────────────────────────────────────────
def quality_report(entries: list[dict]):
    print("\n" + "═"*55)
    print("  QUALITY REPORT — distillation_v2_test.jsonl")
    print("═"*55)

    think_lens = [e["_meta"]["reasoning_chars"] for e in entries]
    ans_lens   = [e["_meta"]["answer_chars"]    for e in entries]
    in_tok     = sum(e["_meta"]["input_tokens"]  for e in entries)
    out_tok    = sum(e["_meta"]["output_tokens"] for e in entries)
    cost       = (in_tok / 1_000_000) * 0.55 + (out_tok / 1_000_000) * 2.19

    print(f"\n  Entries thành công : {len(entries)}/20")
    print(f"\n  Reasoning traces:")
    print(f"    Min  : {min(think_lens):5d} ký tự")
    print(f"    Max  : {max(think_lens):5d} ký tự")
    print(f"    Avg  : {sum(think_lens)//len(think_lens):5d} ký tự")

    short = [e for e in entries if e["_meta"]["reasoning_chars"] < 200]
    if short:
        print(f"  ⚠ {len(short)} entries có reasoning < 200 chars — kiểm tra lại prompt")

    print(f"\n  Tokens dùng:")
    print(f"    Input  : {in_tok:,}")
    print(f"    Output : {out_tok:,}")
    print(f"    Chi phí thực: ${cost:.4f} USD")
    print(f"\n  → Nếu scale lên 400 prompts: ~${cost/len(entries)*400:.2f} USD")

    # Domain breakdown
    from collections import Counter
    domains = Counter(e["_meta"]["domain"] for e in entries)
    print(f"\n  Phân bố domain:")
    for d, n in sorted(domains.items()):
        print(f"    {d:12s}: {n} entries")

    # Compatibility check với existing data
    existing = ROOT / "src" / "data" / "distilled_reasoning_deepseek.jsonl"
    if existing.exists():
        ex = json.loads(existing.read_text(encoding="utf-8").splitlines()[0])
        new = entries[0]
        ex_keys  = set(ex.get("messages", [{}])[0].keys())
        new_keys = set(new["messages"][0].keys())
        compat = ex_keys == new_keys
        print(f"\n  Format compatibility với existing data: {'✅ OK' if compat else '❌ MISMATCH'}")
        if not compat:
            print(f"    Existing: {ex_keys}")
            print(f"    New:      {new_keys}")

    print(f"\n  ✅ File: {OUT_FILE}")
    print("═"*55 + "\n")

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY chưa set!")
        print("   Chạy trong Colab:")
        print("   import os; from google.colab import userdata")
        print("   os.environ['DEEPSEEK_API_KEY'] = userdata.get('DEEPSEEK_API_KEY')")
        sys.exit(1)

    seed_file = ROOT / "offline_training" / "seed_prompts.jsonl"
    if not seed_file.exists():
        print(f"❌ {seed_file} không tồn tại. Chạy gen_seed_prompts.py trước.")
        sys.exit(1)

    prompts = pick_test_prompts(seed_file, N_PER_DOMAIN)
    print(f"Đã chọn {len(prompts)} prompts test ({N_PER_DOMAIN}/domain)")
    print(f"Model: {MODEL} | Concurrent: {CONCURRENT} | Temp: {TEMPERATURE}\n")

    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

    t_start = time.time()
    tasks   = [call_deepseek(client, p["prompt"], p["domain"], p["difficulty"])
               for p in prompts]
    results = await asyncio.gather(*tasks)
    entries = [r for r in results if r is not None]
    elapsed = time.time() - t_start

    print(f"\nHoàn thành {len(entries)}/{len(prompts)} trong {elapsed:.0f}s")

    # Lưu — không có _meta field trong JSONL cuối (chỉ messages)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean_entries = [{"messages": e["messages"]} for e in entries]
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for e in clean_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    quality_report(entries)


if __name__ == "__main__":
    asyncio.run(main())
