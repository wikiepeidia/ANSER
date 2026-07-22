"""
benchmark_integration.py — NGÀY 6, bước 3
Bộ kiểm thử 6 trường hợp cho model vòng 2.

QUAN TRỌNG: các câu hỏi này KHÔNG có trong dữ liệu huấn luyện.
Đây là phép đo khả năng tổng quát hóa thật, không phải kiểm tra thuộc lòng.

CHẠY (sau khi server ANSER đã lên):
  export BRAIN_URL=https://xxx.ngrok-free.dev
  python offline_training/benchmark_integration.py
"""
import os, sys, json, re, time, asyncio
import httpx

BRAIN_URL = os.environ.get("BRAIN_URL", "http://localhost:8000")
HEADERS   = {"ngrok-skip-browser-warning": "true"}
TIMEOUT   = 180
POLL_MAX  = 90


# ══════════════════════════════════════════════════════════════════════════
def extract_json(text: str):
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


def strip_think(text: str) -> str:
    last = text.rfind("</think>")
    return text[last + 8:].strip() if last != -1 else text.strip()


# ══════════════════════════════════════════════════════════════════════════
# 6 trường hợp kiểm thử — KHÔNG có trong dữ liệu huấn luyện
# ══════════════════════════════════════════════════════════════════════════
TESTS = [
    {
        "id":     "T1",
        "name":   "Sinh lệnh tạo workflow",
        "prompt": "Tạo quy trình mỗi 4 tiếng kiểm tra kho, sản phẩm nào còn dưới 15 cái thì báo lên Discord",
        "checks": [
            ("có JSON",            lambda a, j: j is not None),
            ("action đúng",        lambda a, j: j and j.get("action") == "create_workflow"),
            ("có name",            lambda a, j: j and bool(j.get("name"))),
            ("có payload",         lambda a, j: j and isinstance(j.get("payload"), dict)),
            ("payload có nodes",   lambda a, j: j and bool(j.get("payload", {}).get("nodes"))),
        ],
    },
    {
        "id":     "T2",
        "name":   "Sinh truy vấn SQL",
        "prompt": "Cho tôi xem tổng tiền bán được trong 14 ngày vừa rồi",
        "checks": [
            ("có JSON",            lambda a, j: j is not None),
            ("action đúng",        lambda a, j: j and j.get("action") == "query_db"),
            ("có SELECT",          lambda a, j: j and "SELECT" in str(j.get("sql", "")).upper()),
            ("dùng bảng sales",    lambda a, j: j and "sales" in str(j.get("sql", "")).lower()),
            ("cột đúng tên",       lambda a, j: j and "total_amount" in str(j.get("sql", ""))),
        ],
    },
    {
        "id":     "T3",
        "name":   "Workflow n8n có lịch",
        "prompt": "Tạo quy trình gửi tổng kết bán hàng vào 21 giờ mỗi tối qua email",
        "checks": [
            ("có JSON",            lambda a, j: j is not None),
            ("là create_workflow", lambda a, j: j and j.get("action") == "create_workflow"),
            ("có node trigger",    lambda a, j: j and any(
                "trigger" in str(n.get("type", "")).lower()
                for n in j.get("payload", {}).get("nodes", []))),
        ],
    },
    {
        "id":     "T4",
        "name":   "Phát hiện sai số hóa đơn",
        "prompt": (
            "Qwen2-VL đọc được hóa đơn sau, hãy kiểm tra tính hợp lệ:\n"
            '{"supplier_name":"Cửa hàng Tân Phát","items":['
            '{"line":1,"name":"Nước ngọt Coca 330ml","quantity":24,"unit":"lon",'
            '"unit_price":10000,"amount":240000,"confidence":0.95},'
            '{"line":2,"name":"Bánh quy Cosy 132g","quantity":15,"unit":"gói",'
            '"unit_price":20000,"amount":310000,"confidence":0.93}],'
            '"subtotal":550000,"vat_rate":8,"vat_amount":44000,"total_amount":594000}'
        ),
        "checks": [
            ("phát hiện sai",      lambda a, j: any(k in a.lower() for k in
                                    ["sai", "lệch", "không khớp", "không đúng", "chênh"])),
            ("nêu số đúng",        lambda a, j: "300" in a.replace(".", "").replace(",", "")),
            ("không tự sửa",       lambda a, j: not (j and j.get("status") == "completed")),
        ],
    },
    {
        "id":     "T5",
        "name":   "Tính thuế — chỉ văn xuôi",
        "prompt": "Đơn hàng 3 triệu 500 nghìn, thuế GTGT 8% thì phải nộp bao nhiêu tiền thuế?",
        "checks": [
            ("KHÔNG có JSON",      lambda a, j: j is None),
            ("số tiền đúng",       lambda a, j: "280" in a.replace(".", "").replace(",", "")),
        ],
    },
    {
        "id":     "T6",
        "name":   "Chuyển hướng câu ngoài lĩnh vực",
        "prompt": "Giải thích cho tôi thuật toán sắp xếp nổi bọt hoạt động thế nào",
        "checks": [
            ("ngắn gọn",           lambda a, j: len(a) < 600),
            ("có nhắc bán lẻ",     lambda a, j: any(k in a.lower() for k in
                                    ["bán lẻ", "cửa hàng", "kho", "tồn kho", "kinh doanh"])),
            ("không viết code dài",lambda a, j: a.count("def ") + a.count("for ") < 3),
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════
async def ask(client: httpx.AsyncClient, prompt: str) -> tuple[str, float]:
    t0 = time.time()
    r = await client.post(
        f"{BRAIN_URL}/chat",
        json={"message": prompt, "user_id": 1, "store_id": 1},
    )
    r.raise_for_status()
    body = r.json()

    # Trả lời ngay
    if "result" in body and body.get("status") == "completed":
        return body["result"].get("answer", ""), time.time() - t0

    # Trả về task_id — poll
    task_id = body.get("task_id")
    if not task_id:
        return json.dumps(body, ensure_ascii=False), time.time() - t0

    for _ in range(POLL_MAX):
        await asyncio.sleep(2)
        rr = await client.get(f"{BRAIN_URL}/api/v1/task/{task_id}")
        bb = rr.json()
        if bb.get("status") == "completed":
            return bb.get("result", {}).get("answer", ""), time.time() - t0
        if bb.get("status") == "failed":
            return f"[TASK FAILED] {bb}", time.time() - t0

    return "[TIMEOUT]", time.time() - t0


async def main():
    print(f"\n{'='*66}")
    print(f"  BỘ KIỂM THỬ TÍCH HỢP — ANSER Brain vòng 2")
    print(f"{'='*66}")
    print(f"  Endpoint : {BRAIN_URL}")
    print(f"  Số ca    : {len(TESTS)}")
    print(f"{'='*66}\n")

    passed_cases, results = 0, []

    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        # Health check
        try:
            h = await client.get(f"{BRAIN_URL}/health")
            hs = h.json()
            print(f"  Health: engine_ready={hs.get('engine_ready')} "
                  f"degraded={hs.get('degraded')}\n")
        except Exception as e:
            print(f"  ⚠ Không gọi được /health: {str(e)[:80]}\n")

        for t in TESTS:
            print(f"  ── {t['id']}  {t['name']}")
            print(f"     Hỏi: {t['prompt'][:70]}...")
            try:
                raw, dur = await ask(client, t["prompt"])
            except Exception as e:
                print(f"     ✗ LỖI GỌI API: {str(e)[:80]}\n")
                results.append((t["id"], t["name"], 0, len(t["checks"]), 0.0))
                continue

            answer = strip_think(raw)
            obj    = extract_json(answer)

            n_ok = 0
            for label, fn in t["checks"]:
                try:
                    ok = bool(fn(answer, obj))
                except Exception:
                    ok = False
                n_ok += ok
                print(f"     {'✓' if ok else '✗'} {label}")

            all_ok = n_ok == len(t["checks"])
            passed_cases += all_ok
            results.append((t["id"], t["name"], n_ok, len(t["checks"]), dur))

            print(f"     → {n_ok}/{len(t['checks'])} tiêu chí  ·  {dur:.1f}s")
            print(f"     Đáp: {answer[:110]}...\n")

    # ── Tổng kết ────────────────────────────────────────────────────────
    print(f"{'='*66}")
    print(f"  KẾT QUẢ")
    print(f"{'='*66}\n")

    total_checks = sum(r[3] for r in results)
    total_ok     = sum(r[2] for r in results)

    for tid, name, ok, tot, dur in results:
        mark = "✓" if ok == tot else ("~" if ok else "✗")
        print(f"  {mark}  {tid}  {name:32s} {ok}/{tot}   {dur:5.1f}s")

    print(f"\n  Ca đạt hoàn toàn : {passed_cases}/{len(TESTS)}")
    print(f"  Tiêu chí đạt     : {total_ok}/{total_checks} ({total_ok/total_checks*100:.0f}%)")

    durs = [r[4] for r in results if r[4] > 0]
    if durs:
        p95 = sorted(durs)[int(len(durs) * 0.95) - 1] if len(durs) > 1 else durs[0]
        print(f"  Độ trễ trung bình: {sum(durs)/len(durs):.1f}s")
        print(f"  Độ trễ phân vị 95: {p95:.1f}s  {'✓' if p95 <= 5 else '⚠ vượt ngưỡng 5s'}")

    print()
    if passed_cases == len(TESTS):
        print("  ✅ ĐẠT TOÀN BỘ — sẵn sàng triển khai")
    elif passed_cases >= 4:
        print(f"  ⚠ Đạt {passed_cases}/{len(TESTS)} — dùng được, còn điểm cần cải thiện")
    else:
        print(f"  ✗ Chỉ đạt {passed_cases}/{len(TESTS)} — cần xem lại prompt hoặc dữ liệu")
    print(f"{'='*66}\n")

    return 0 if passed_cases >= 4 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
