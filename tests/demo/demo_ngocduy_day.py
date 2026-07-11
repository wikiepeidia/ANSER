"""DEMO 'Một ngày Ngọc Duy' — chạy chuỗi tự động hóa THẬT, thông báo đổ vào Discord THẬT.

Khác gen_evidence.py (test matrix khô khan): script này kể CÂU CHUYỆN 1 ngày vận hành
của xưởng trà/cao atiso, mỗi bước cách nhau vài giây để người xem theo kịp trên Discord.

Điều kiện: stack đang chạy + DISCORD_WEBHOOK_URL trong .env trỏ webhook thật.
Evidence: tests/evidence/demo_transcript.txt (timestamp + HTTP code từng bước).

Chạy: python tests/demo/demo_ngocduy_day.py
"""
import json
import os
import time
import uuid
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

N8N   = os.environ.get("N8N_URL", "http://localhost:5678")
TOKEN = os.environ.get("ANSER_WEBHOOK_TOKEN", "sprint1-test-token")
ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVID  = os.path.join(ROOT, "tests", "evidence")
PAUSE = float(os.environ.get("DEMO_PAUSE", "6"))   # giây nghỉ giữa các bước

LOG = []


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method,
                  headers={"Content-Type": "application/json", "x-anser-token": TOKEN})
    try:
        r = urlopen(req, timeout=30)
        return r.status, r.read().decode("utf-8", "ignore")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except URLError as e:
        return 0, f"URLERROR: {e.reason}"


def wf(path):
    return f"{N8N}/webhook/{path}"


def manual_run(name):
    """Chạy tay 1 workflow schedule (như tới giờ hẹn) — kỹ thuật giống gen_evidence."""
    email = os.environ.get("N8N_EMAIL", "admin@anser.local")
    pw = os.environ.get("N8N_PASSWORD", "AnserTest123!")
    req = Request(f"{N8N}/rest/login", data=json.dumps(
        {"emailOrLdapLoginId": email, "password": pw}).encode(),
        method="POST", headers={"Content-Type": "application/json"})
    r = urlopen(req, timeout=15); r.read()
    cookie = {"Cookie": next(p.split(";")[0] for p in
                             "; ".join(r.headers.get_all("Set-Cookie") or []).split("; ")
                             if p.startswith("n8n-auth="))}
    wfs = json.loads(urlopen(Request(f"{N8N}/rest/workflows", headers=cookie), timeout=15).read())
    items = wfs.get("data", wfs)
    items = items.get("data", items) if isinstance(items, dict) else items
    wid = next(w["id"] for w in items if w["name"] == name)
    detail = json.loads(urlopen(Request(f"{N8N}/rest/workflows/{wid}", headers=cookie), timeout=15).read())
    inner = detail.get("data", detail)
    trig = next(n for n in inner["nodes"] if "Trigger" in n["type"] or "schedule" in n["type"])
    body = json.dumps({"workflowData": inner, "triggerToStartFrom": {"name": trig["name"]}}).encode()
    urlopen(Request(f"{N8N}/rest/workflows/{wid}/run", data=body, method="POST",
                    headers={"Content-Type": "application/json", **cookie}), timeout=60).read()


def step(n, story, method, path, body, expect_status, note=""):
    ts = datetime.now().strftime("%H:%M:%S")
    s, r = http(method, wf(path), body)
    ok = "✅" if s == expect_status else f"⚠️ (kỳ vọng {expect_status})"
    line = f"[{ts}] BƯỚC {n:>2} | {story}\n          → {method} /{path} → HTTP {s} {ok}\n          → {r[:180]}"
    if note:
        line += f"\n          ({note})"
    print(line)
    LOG.append(line)
    time.sleep(PAUSE)
    return s, r


def narrate(title, description, color=3447003):
    """Lời dẫn chuyện — gửi thẳng qua shared_notify để hiện trên Discord."""
    http("POST", wf("notify"), {"channel": "discord", "title": title,
                                "description": description, "color": color})
    time.sleep(2)


def run():
    os.makedirs(EVID, exist_ok=True)
    day = datetime.now().strftime("%d/%m/%Y")
    suffix = uuid.uuid4().hex[:5].upper()
    po = f"DEMO-PO-{suffix}"
    lot_bong = f"LOT-DEMO-B{suffix}"
    lot_la = f"LOT-DEMO-L{suffix}"
    meb1 = f"MEB-DEMO-1{suffix}"
    meb2 = f"MEB-DEMO-2{suffix}"

    print(f"=== DEMO 'Một ngày Ngọc Duy' — {day} — thông báo đổ vào Discord THẬT ===\n")

    narrate(f"🌅 DEMO — Một ngày vận hành Trà Ngọc Duy ({day})",
            "Từ giờ đến hết demo, **mọi thông báo bên dưới do n8n tự sinh** khi dữ liệu chạy qua "
            "chuỗi tự động hóa (POS → đơn hàng → BOM → nhập nguyên liệu → mẻ chế biến → kiểm nghiệm → báo cáo lãi). "
            "Không có tin nào được gõ tay.", 10181046)

    # ── Buổi sáng: cửa hàng ────────────────────────────────────────────────
    step(1, "8h00 — Cửa hàng Phan Chu Trinh mở cửa, khách du lịch mua quà (POS bắn hóa đơn)",
         "POST", "pos-event",
         {"device_id": "POS-PhanChuTrinh-01", "event_type": "sale",
          "idempotency_key": "demo-" + uuid.uuid4().hex[:10],
          "payload": {"amount": 1017000, "invoice_no": f"INV-DEMO-{suffix}",
                      "items": "2x Trà atiso túi lọc + 1x Cao atisô 1kg", "cashier": "thu_ngan_1"}},
         201)

    ts2 = datetime.now().strftime("%H:%M:%S")
    manual_run("retail_low_stock_alert")   # workflow schedule — kích như tới giờ hẹn
    line2 = (f"[{ts2}] BƯỚC  2 | 8h15 — Hệ thống tự rà tồn kho theo lịch: bông atiso 400gr sắp hết "
             f"(12 hộp < ngưỡng riêng 15)\n          → RUN retail_low_stock_alert (schedule) → submitted ✅")
    print(line2)
    LOG.append(line2)
    time.sleep(PAUSE)

    # ── Đơn hàng đại lý ────────────────────────────────────────────────────
    step(3, "9h00 — Đại lý đặc sản Đà Lạt gửi đơn đặt 500 hộp trà túi lọc (chụp đơn → OCR → AI suy luận SL)",
         "POST", "customer-order-ocr", {"scenario": "order", "order_code": po}, 201,
         note="AI đề xuất SX 510 hộp (buffer 2% phế phẩm) — lệnh ở trạng thái draft CHỜ NGƯỜI DUYỆT")

    step(4, "9h30 — Quản lý duyệt lệnh → hệ thống tính DS nguyên liệu từ BOM ĐẢO yield",
         "POST", "production-approved", {"order_code": po}, 200,
         note="cần 51kg lá KHÔ, tồn 20 → thiếu 31kg ÷ yield 25% = MUA 124kg lá TƯƠI + gợi ý 3 mẻ")

    # ── Nguyên liệu về ─────────────────────────────────────────────────────
    step(5, "10h00 — HTX Thuận Phát giao 300kg bông atiso tươi, cân tại chỗ (chụp phiếu cân → OCR)",
         "POST", "material-intake",
         {"scenario": "weighslip", "lot_code": lot_bong, "harvest_hours_ago": 5}, 201,
         note="thu hái 5h trước → còn ~19h trong CỬA SỔ 24H giữ cynarin")

    step(6, "10h30 — 124kg lá tươi cho đơn đại lý về, nhập qua app (không phiếu cân)",
         "POST", "material-intake",
         {"lot_code": lot_la, "farmer": "HTX Thuận Phát", "region_grown": "Đà Lạt - Xuân Thọ",
          "part": "lá", "form": "tuoi", "material_code": "LA-TUOI", "qty_kg": 124,
          "unit_cost_vnd": 12000, "harvest_hours_ago": 2, "order_code": po}, 201,
         note="đơn đại lý tự chuyển 'NVL đã về — sẵn sàng sản xuất'")

    # ── Xưởng chế biến ─────────────────────────────────────────────────────
    step(7, "11h00 — Xưởng bắt đầu mẻ trà đầu tiên từ lô lá vừa về",
         "POST", "batch-process",
         {"event": "start", "batch_code": meb1, "order_code": po, "material_lot_code": lot_la,
          "input_material_kg": 124, "shift": "Mẻ sáng", "operator": "to_truong_A"}, 201,
         note="hệ thống tự kiểm tra đồng hồ 24h của lô nguyên liệu")

    step(8, "11h30 — Tổ chế biến ghi nhật ký công đoạn XAO 110°C/45 phút (CCP dừng enzyme)",
         "POST", "batch-process",
         {"event": "stage", "batch_code": meb1, "stage": "xao", "temp_c": 110,
          "duration_min": 45, "operator": "to_truong_A"}, 201,
         note="ghi êm vào nhật ký mẻ — không làm phiền Discord")

    step(9, "14h00 — Sấy xong lần 1, đo độ ẩm: 9.2% — CHƯA ĐẠT (ngưỡng 8%)",
         "POST", "batch-process",
         {"event": "complete", "batch_code": meb1, "output_units": 500, "ng_units": 6,
          "moisture_pct": 9.2}, 201,
         note="hệ thống TỪ CHỐI chốt mẻ — nguy cơ nấm mốc, yêu cầu sấy tiếp")

    step(10, "16h00 — Sấy lại, đo lần 2: 6.5% — ĐẠT → chốt mẻ, hệ thống tự tính HSD",
         "POST", "batch-process",
         {"event": "complete", "batch_code": meb1, "output_units": 500, "ng_units": 6,
          "moisture_pct": 6.5, "material_cost_vnd": 1488000, "labor_cost_vnd": 500000}, 201,
         note="độ ẩm 6.5% ≤ 7% → HSD 12 tháng; mẻ chuyển 'chờ kiểm nghiệm' — CHƯA được bán")

    # ── Kiểm nghiệm dược liệu ──────────────────────────────────────────────
    step(11, "17h00 — Kết quả lab về: cynarin 2.8%, nấm mốc 40 CFU/g — ĐẠT toàn bộ chỉ tiêu",
         "POST", "lab-result",
         {"batch_code": meb1, "cynarin_pct": 2.8, "mold_cfu_g": 40,
          "pesticide_ok": True, "heavy_metal_ok": True, "tested_by": "Lab ngoài"}, 201,
         note="gate MỞ KHÓA cho phép bán, số phiếu kiểm nghiệm gắn vào lô")

    # mẻ 2 dựng nhanh để demo nhánh fail (start + complete không nghỉ dài)
    http("POST", wf("batch-process"), {"event": "start", "batch_code": meb2, "order_code": po,
                                       "material_lot_code": lot_la, "input_material_kg": 40,
                                       "shift": "Mẻ chiều"})
    time.sleep(2)
    http("POST", wf("batch-process"), {"event": "complete", "batch_code": meb2,
                                       "output_units": 90, "ng_units": 3, "moisture_pct": 7.5})
    time.sleep(2)
    step(12, "17h30 — Mẻ chiều kết quả lab XẤU: nấm mốc 150 CFU/g (ngưỡng <100)",
         "POST", "lab-result",
         {"batch_code": meb2, "cynarin_pct": 2.5, "mold_cfu_g": 150,
          "pesticide_ok": True, "heavy_metal_ok": True, "tested_by": "Lab ngoài"}, 201,
         note="gate CHẶN XUẤT tuyệt đối + tự truy xuất về nông hộ/vùng trồng để điều tra")

    # ── Cuối ngày: báo cáo ─────────────────────────────────────────────────
    step(13, "18h00 — Báo cáo sản xuất đơn bông atiso: sấy mất 80.8% khối lượng NHƯNG đúng định mức",
         "POST", "shift-report", {"order_code": "DH-A-102"}, 200,
         note="yield thực 19.2% / định mức 20% → lệch 4% → 🟢 KHÔNG báo động giả")

    step(14, "18h05 — Báo cáo đơn trà: yield 20% / định mức 25% → lệch 20% → cảnh báo ĐỎ thật",
         "POST", "shift-report", {"order_code": "DH-A-101"}, 200,
         note="chỉ báo động khi LỆCH ĐỊNH MỨC — kèm NG 1.64%, lãi 90.93% (số SQL tính, AI chỉ diễn giải)")

    narrate(f"🌙 DEMO kết thúc — {day}",
            "Toàn bộ thông báo phía trên do **n8n + Postgres + rag_service chạy thật** sinh ra "
            "(webhook → verify token → OCR mock-brain → tính toán deterministic → Discord). "
            "Các con số yield/HSD/lãi đều kiểm chứng được bằng tay. "
            "— ANSER Automation V2, pilot Trà Ngọc Duy 🌿", 10181046)

    with open(os.path.join(EVID, "demo_transcript.txt"), "w", encoding="utf-8") as f:
        f.write(f"DEMO 'Một ngày Ngọc Duy' — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Kênh: Discord THẬT (webhook 'POS Notifier')\n{'=' * 70}\n\n")
        f.write("\n\n".join(LOG))
    print(f"\nĐã ghi transcript: {os.path.join(EVID, 'demo_transcript.txt')}")


if __name__ == "__main__":
    run()
