"""
POS Simulator — bắn JSON giả lập máy POS vào n8n webhook.
Usage:
  python scripts/pos_simulator.py          # chạy full demo (5 sự kiện)
  python scripts/pos_simulator.py invoice  # chỉ gửi 1 hóa đơn
  python scripts/pos_simulator.py bad      # gửi payload thiếu field (test 400)
  python scripts/pos_simulator.py loop 10  # gửi liên tục 10 lần
"""
import json
import os
import sys
import time
import uuid
import random
import urllib.request
import urllib.error
from datetime import datetime

WEBHOOK = os.environ.get("ANSER_POS_WEBHOOK", "http://localhost:5678/webhook/pos-event")
# SEC-3: token chia sẻ — phải khớp ANSER_WEBHOOK_TOKEN đã cấu hình cho n8n
WEBHOOK_TOKEN = os.environ.get("ANSER_WEBHOOK_TOKEN", "")

DEVICES   = ["POS-001", "POS-002", "POS-003"]
CASHIERS  = ["nguyen_van_a", "tran_thi_b", "le_van_c"]
# SP thật của Ngọc Duy (PUBLIC — ngocduygroup.com); POS cửa hàng đặc sản Đà Lạt
PRODUCTS  = ["Trà atiso túi lọc (50 túi)", "Cao atisô lá khô 1kg", "Bông atiso sấy khô 400gr",
             "Linh chi lát 400gr", "Trà Thái Nguyên 80gr"]

def make_invoice():
    items = random.randint(1, 5)
    return {
        "device_id":  random.choice(DEVICES),
        "event_type": "sale",              # registry PDF3 (rag map sale_completed -> sale)
        "idempotency_key": str(uuid.uuid4()),
        "payload": {
            "amount":      random.randint(25000, 500000),
            "items":       items,
            "cashier":     random.choice(CASHIERS),
            "products":    random.sample(PRODUCTS, min(items, len(PRODUCTS))),
            "payment_method": random.choice(["cash", "card", "qr_code"]),
            "invoice_no":  f"INV-{random.randint(10000, 99999)}",
            "timestamp":   datetime.now().isoformat(),
        }
    }

SCENARIOS = {
    "invoice": make_invoice,
    "cash_low": lambda: {
        "device_id": "POS-002", "event_type": "cash_low",
        "payload": {"remaining": 450000, "threshold": 1000000, "alert": True}
    },
    "heartbeat": lambda: {
        "device_id": random.choice(DEVICES), "event_type": "heartbeat",
        "payload": {"uptime_hours": random.randint(1, 24), "temperature_c": random.randint(38, 55)}
    },
    "refund": lambda: {
        "device_id": "POS-001", "event_type": "refund",
        "payload": {"amount": random.randint(25000, 150000), "reason": "customer_return",
                    "ref_invoice": f"INV-{random.randint(10000, 99999)}"}
    },
    "bad": lambda: {"payload": {"corrupted": True}},  # thiếu device_id và event_type
}

def post(payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if WEBHOOK_TOKEN:
        headers["x-anser-token"] = WEBHOOK_TOKEN
    req  = urllib.request.Request(WEBHOOK, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

def run_demo():
    print("=" * 55)
    print("  POS SIMULATOR — Demo 5 sự kiện")
    print(f"  Target: {WEBHOOK}")
    print("=" * 55)

    sequence = [
        ("sale_completed", make_invoice()),
        ("sale_completed", make_invoice()),
        ("cash_low",   SCENARIOS["cash_low"]()),
        ("sale_completed", make_invoice()),
        ("BAD PAYLOAD", SCENARIOS["bad"]()),
    ]

    for i, (label, payload) in enumerate(sequence, 1):
        print(f"\n[{i}/5] Gửi: {label}")
        print(f"      Payload: {json.dumps(payload, ensure_ascii=False)[:80]}...")
        status, resp = post(payload)
        icon = "✓" if status in (200, 201) else "✗"
        print(f"      {icon} HTTP {status} → {json.dumps(resp, ensure_ascii=False)[:100]}")
        time.sleep(1.5)

    print("\n" + "=" * 55)
    print("  Demo hoàn tất. Kiểm tra:")
    print("  • Discord: xem thông báo mới")
    print("  • n8n Executions: http://localhost:5678")
    print("  • NeonDB: SELECT * FROM iot_events ORDER BY id DESC LIMIT 5;")
    print("=" * 55)

def main():
    args = sys.argv[1:]
    if not args:
        run_demo()
    elif args[0] == "loop":
        count = int(args[1]) if len(args) > 1 else 5
        print(f"Gửi {count} hóa đơn ngẫu nhiên...\n")
        for i in range(count):
            payload = make_invoice()
            status, resp = post(payload)
            print(f"  [{i+1}/{count}] HTTP {status} — {payload['payload'].get('invoice_no')} — {resp.get('id','?')}")
            time.sleep(0.8)
    elif args[0] in SCENARIOS:
        payload = SCENARIOS[args[0]]()
        print(f"Gửi '{args[0]}':", json.dumps(payload, ensure_ascii=False, indent=2))
        status, resp = post(payload)
        print(f"\nHTTP {status}:", json.dumps(resp, ensure_ascii=False, indent=2))
    else:
        print(f"Scenario không hợp lệ. Chọn: {', '.join(SCENARIOS)} | loop <n>")

if __name__ == "__main__":
    main()
