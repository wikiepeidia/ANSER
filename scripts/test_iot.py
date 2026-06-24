"""
Test script for IoT Events Ingest workflow.
Usage: python scripts/test_iot.py
"""
import json
import urllib.request
import urllib.error

WEBHOOK = "http://localhost:5678/webhook/iot-event"

PAYLOADS = [
    # 1. Normal sale event
    {"device_id": "POS-001", "event_type": "sale_completed",
     "payload": {"amount": 150000, "items": 3, "cashier": "nguyen_van_a"}},
    # 2. Low cash warning
    {"device_id": "POS-002", "event_type": "cash_low",
     "payload": {"remaining": 500000, "threshold": 1000000}},
    # 3. Device heartbeat
    {"device_id": "POS-003", "event_type": "heartbeat",
     "payload": {"uptime_hours": 12, "temperature_c": 42}},
    # 4. Refund event
    {"device_id": "POS-001", "event_type": "refund",
     "payload": {"amount": 50000, "reason": "customer_return", "ref_id": "TXN-8821"}},
    # 5. INVALID — missing required fields (should get 400)
    {"payload": {"some": "data"}},
]

def post(url, body):
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, method="POST",
                                   headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def main():
    print(f"Sending {len(PAYLOADS)} test payloads to {WEBHOOK}\n")
    for i, payload in enumerate(PAYLOADS, 1):
        status, resp = post(WEBHOOK, payload)
        label = "INVALID (expect 400)" if not payload.get("device_id") else "valid"
        icon  = "OK" if status in (200, 201) else "FAIL" if status == 400 else "ERR"
        print(f"  [{icon}] #{i} {label} → HTTP {status} | {resp}")

    print("\nCheck NeonDB rows:")
    print("  psql $POSTGRES_URL -c 'SELECT id, device_id, event_type, created_at FROM iot_events ORDER BY id DESC LIMIT 10;'")

if __name__ == "__main__":
    main()
