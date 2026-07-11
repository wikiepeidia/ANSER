"""Setup n8n cho test: tạo owner (nếu chưa) → import workflows → activate webhook workflows.
Idempotent — chạy lại nhiều lần an toàn.

Env: N8N_URL (default http://localhost:5678), N8N_EMAIL, N8N_PASSWORD.
"""
import json
import os
import subprocess
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
EMAIL   = os.environ.get("N8N_EMAIL", "admin@anser.local")
PASS    = os.environ.get("N8N_PASSWORD", "AnserTest123!")
ROOT    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Workflow cần activate (có Webhook/Schedule trigger) để test
ACTIVATE = [
    "retail_pos_ingest", "retail_new_customer_welcome", "retail_invoice_ocr_import",
    "retail_low_stock_alert", "retail_daily_sales_report",
    "retail_forecast_suggest_reorder", "retail_auto_promo_post", "retail_marketplace_sync",
    "retail_debt_reminder", "retail_competitor_price_sync", "shared_notify",
    "retail_order_payment_qr", "retail_sepay_payment", "retail_einvoice_adjust",
    "retail_einvoice_backup", "retail_sepay_poll",
    "retail_channel_order_sync", "retail_channel_delivered", "retail_lot_intake",
    "retail_woo_poll",
    "manuf_material_batch_intake", "manuf_batch_process_log", "manuf_lab_test_gate",
    "manuf_waste_profit_report", "manuf_dr_report_periodic",
    "manuf_ocr_customer_order", "manuf_generate_material_list",
]


def call(method, path, data=None, hdrs=None):
    req = Request(N8N_URL + path,
                  data=json.dumps(data).encode() if data is not None else None,
                  method=method, headers={"Content-Type": "application/json", **(hdrs or {})})
    r = urlopen(req, timeout=30)
    raw = r.read()
    return (json.loads(raw) if raw else {}), "; ".join(r.headers.get_all("Set-Cookie") or [])


def ensure_owner():
    try:
        call("POST", "/rest/owner/setup",
             {"email": EMAIL, "firstName": "ANSER", "lastName": "Admin", "password": PASS})
        print("[setup] owner created")
    except HTTPError as e:
        print(f"[setup] owner already exists (HTTP {e.code}) — ok")


def login():
    _, cookies = call("POST", "/rest/login", {"emailOrLdapLoginId": EMAIL, "password": PASS})
    for p in cookies.split("; "):
        if p.startswith("n8n-auth="):
            return {"Cookie": p.split(";")[0]}
    raise SystemExit("[setup] login FAILED")


def main():
    ensure_owner()
    # import qua script chính (đường login email/password)
    env = {**os.environ, "N8N_EMAIL": EMAIL, "N8N_PASSWORD": PASS}
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "import_workflows.py")],
                   check=True, env=env)

    cookie = login()
    wfs, _ = call("GET", "/rest/workflows", hdrs=cookie)
    items = wfs.get("data", wfs)
    if isinstance(items, dict):
        items = items.get("data", [])
    by_name = {w["name"]: w["id"] for w in items}

    # Gắn __error_handler làm error workflow cho mọi workflow (PDF3 mục 4.3)
    err_id = by_name.get("__error_handler")
    if err_id:
        for name, wf_id in by_name.items():
            if name == "__error_handler":
                continue
            try:
                detail, _ = call("GET", f"/rest/workflows/{wf_id}", hdrs=cookie)
                inner = detail.get("data", detail)
                settings = dict(inner.get("settings") or {})
                if settings.get("errorWorkflow") == err_id:
                    continue
                settings["errorWorkflow"] = err_id
                call("PATCH", f"/rest/workflows/{wf_id}",
                     {"settings": settings, "versionId": inner["versionId"]}, cookie)
            except HTTPError as e:
                print(f"[setup] wire error-wf '{name}' FAIL HTTP {e.code}")
        print(f"[setup] đã gắn __error_handler cho {len(by_name)-1} workflow")

    for name in ACTIVATE:
        wf_id = by_name.get(name)
        if not wf_id:
            print(f"[setup] WARN: khong tim thay workflow '{name}'")
            continue
        detail, _ = call("GET", f"/rest/workflows/{wf_id}", hdrs=cookie)
        inner = detail.get("data", detail)
        if inner.get("active"):
            print(f"[setup] '{name}' da active")
            continue
        try:
            call("POST", f"/rest/workflows/{wf_id}/activate", {"versionId": inner["versionId"]}, cookie)
            print(f"[setup] activated '{name}'")
        except HTTPError as e:
            print(f"[setup] activate '{name}' FAIL HTTP {e.code}: {e.read().decode()[:150]}")
    print("[setup] done")


if __name__ == "__main__":
    main()
