"""
day2_full_batch.py — Chạy full 400 prompts với DeepSeek-R1.

Điểm khác so với day1_test_batch.py:
  - Lấy TẤT CẢ 400 prompts (không chỉ 4/domain)
  - Incremental save: lưu ngay sau mỗi entry thành công
  - Resume: nếu bị ngắt giữa chừng, chạy lại tự động bỏ qua entry đã có
  - Progress bar đơn giản

CÁCH CHẠY:
  !cd /content/ANSER_AI_FIX && python offline_training/day2_full_batch.py

KẾT QUẢ:
  src/data/distillation_v2.jsonl — 400 entries với real reasoning traces
"""

import os, sys, json, asyncio, time
from pathlib import Path
from openai import AsyncOpenAI

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Config ────────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL            = "deepseek-reasoner"
TEMPERATURE      = 0.6
MAX_TOKENS       = 4096
CONCURRENT       = 5          # 5 requests song song
SLEEP_BETWEEN    = 0.5        # giây chờ giữa các batch

SYSTEM_PROMPT = (
    "You are Project A, an expert Retail Consultant for Vietnamese SMEs "
    "using the ANSER platform. Trả lời bằng tiếng Việt, chi tiết và có căn cứ."
)

SEED_FILE = ROOT / "offline_training" / "seed_prompts.jsonl"
OUT_FILE  = ROOT / "src" / "data" / "distillation_v2.jsonl"

# ── Load seeds ────────────────────────────────────────────────────────────────
def load_seeds() -> list[dict]:
    return [json.loads(l) for l in SEED_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]

# ── Resume: tìm prompts đã xử lý ─────────────────────────────────────────────
def load_done_prompts() -> set[str]:
    if not OUT_FILE.exists():
        return set()
    done = set()
    for line in OUT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            user_msg = next(
                (m["content"] for m in obj.get("messages", []) if m["role"] == "user"),
                None
            )
            if user_msg:
                done.add(user_msg.strip())
        except Exception:
            pass
    return done

# ── Gọi API ──────────────────────────────────────────────────────────────────
SEM = asyncio.Semaphore(CONCURRENT)

async def call_one(client: AsyncOpenAI, seed: dict, file_handle) -> bool:
    async with SEM:
        try:
            t0 = time.time()
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": seed["prompt"]},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            elapsed = time.time() - t0
            msg = resp.choices[0].message
            reasoning = getattr(msg, "reasoning_content", None) or ""
            answer    = msg.content or ""

            entry = {
                "messages": [
                    {"role": "system",    "content": SYSTEM_PROMPT},
                    {"role": "user",      "content": seed["prompt"]},
                    {"role": "assistant", "content": f"<think>\n{reasoning}\n</think>\n{answer}"},
                ]
            }

            # Incremental save — ghi ngay lập tức
            file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            file_handle.flush()

            status = "✓" if reasoning else "⚠"
            print(f"  {status} [{seed['domain']:10s}/{seed['difficulty']:6s}] "
                  f"think={len(reasoning):5d}c  {elapsed:.1f}s")
            return True

        except Exception as e:
            print(f"  ✗ FAIL [{seed['domain']}]: {e}")
            return False

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY chưa set!")
        sys.exit(1)

    if not SEED_FILE.exists():
        print(f"❌ {SEED_FILE} không tồn tại")
        sys.exit(1)

    seeds    = load_seeds()
    done_set = load_done_prompts()

    # Lọc bỏ những prompt đã done (resume)
    todo = [s for s in seeds if s["prompt"].strip() not in done_set]

    print(f"{'='*55}")
    print(f"  DAY 2 — FULL BATCH")
    print(f"{'='*55}")
    print(f"  Tổng seed prompts  : {len(seeds)}")
    print(f"  Đã có (resume)     : {len(done_set)}")
    print(f"  Cần chạy hôm nay   : {len(todo)}")
    print(f"  Model              : {MODEL}")
    print(f"  Concurrent         : {CONCURRENT}")
    print(f"  Output             : {OUT_FILE}")
    print(f"{'='*55}\n")

    if not todo:
        print("✅ Tất cả 400 prompts đã được xử lý. Không cần chạy thêm.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

    t_start   = time.time()
    n_success = len(done_set)
    n_fail    = 0

    # Mở file ở append mode — giữ lại entry cũ nếu resume
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), CONCURRENT):
            batch = todo[i : i + CONCURRENT]
            tasks = [call_one(client, s, f) for s in batch]
            results = await asyncio.gather(*tasks)

            n_success += sum(results)
            n_fail    += results.count(False)

            done_total = n_success + n_fail
            pct        = done_total / len(seeds) * 100
            elapsed    = time.time() - t_start
            eta        = (elapsed / max(done_total - len(done_set), 1)) * (len(todo) - (i + len(batch)))

            print(f"  Progress: {done_total}/{len(seeds)} ({pct:.0f}%)  "
                  f"ETA: {eta/60:.0f} phút\n")

            await asyncio.sleep(SLEEP_BETWEEN)

    # ── Final report ──────────────────────────────────────────────────────────
    total_time = time.time() - t_start
    final_entries = [
        json.loads(l) for l in OUT_FILE.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    think_lens = []
    for e in final_entries:
        asst  = e["messages"][-1]["content"]
        start = asst.find("<think>") + 7
        end   = asst.find("</think>")
        if start > 7 and end > start:
            think_lens.append(end - start)

    print(f"\n{'='*55}")
    print(f"  FINAL REPORT")
    print(f"{'='*55}")
    print(f"  Entries trong file : {len(final_entries)}")
    print(f"  Thất bại hôm nay   : {n_fail}")
    print(f"  Thời gian          : {total_time/60:.1f} phút")
    if think_lens:
        print(f"  Reasoning avg      : {sum(think_lens)//len(think_lens):,} chars")
        print(f"  Reasoning max      : {max(think_lens):,} chars")
    print(f"\n  ✅ {OUT_FILE}")
    print(f"{'='*55}\n")

    if n_fail > 0:
        print(f"  ⚠ {n_fail} entries thất bại — chạy lại script để retry tự động\n")


if __name__ == "__main__":
    asyncio.run(main())
