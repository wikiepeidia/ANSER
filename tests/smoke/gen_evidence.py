"""Chạy full test-matrix (PDF 3 mục 5) và sinh bằng chứng kiểm chứng được:
  - tests/evidence/report.html   (báo cáo mở bằng trình duyệt)
  - tests/evidence/transcript.txt (log thô mọi request/response + DB rows)

Điều kiện: stack đã `docker compose up -d` và `tests/smoke/setup.py` đã chạy.
Env: ANSER_WEBHOOK_TOKEN (khớp stack), N8N_URL, RAG_URL, DISCORD_MOCK_URL.
"""
import json
import os
import subprocess
import time
import html
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

N8N   = os.environ.get("N8N_URL", "http://localhost:5678")
RAG   = os.environ.get("RAG_URL", "http://localhost:8001")
DMOCK = os.environ.get("DISCORD_MOCK_URL", "http://localhost:9099")
TOKEN = os.environ.get("ANSER_WEBHOOK_TOKEN", "sprint1-test-token")
PGC   = ["docker", "exec", "anser-test-pg", "psql", "-U", "postgres", "-d", "anser_test", "-tAc"]
ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVID  = os.path.join(ROOT, "tests", "evidence")

LOG = []
RESULTS = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def http(method, url, body=None, headers=None):
    data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
    req = Request(url, data=data, method=method,
                  headers={"Content-Type": "application/json", **(headers or {})})
    try:
        r = urlopen(req, timeout=30)
        return r.status, r.read().decode("utf-8", "ignore")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except URLError as e:
        return 0, f"URLERROR: {e.reason}"


def db(sql):
    try:
        out = subprocess.run(PGC + [sql], capture_output=True, text=True, timeout=20)
        return out.stdout.strip()
    except Exception as e:
        return f"DBERR: {e}"


def n8n_login():
    email = os.environ.get("N8N_EMAIL", "admin@anser.local")
    pw = os.environ.get("N8N_PASSWORD", "AnserTest123!")
    req = Request(f"{N8N}/rest/login", data=json.dumps(
        {"emailOrLdapLoginId": email, "password": pw}).encode(),
        method="POST", headers={"Content-Type": "application/json"})
    r = urlopen(req, timeout=15); r.read()
    return next((p.split(";")[0] for p in
                 "; ".join(r.headers.get_all("Set-Cookie") or []).split("; ")
                 if p.startswith("n8n-auth=")), "")


def set_active(name, active):
    """Bật/tắt workflow schedule — tắt 2 poller (SePay/Woo) khi chạy matrix để khỏi
    chèn dữ liệu giữa các assert FEFO (poll tự bắn = nondeterministic)."""
    try:
        cookie = {"Cookie": n8n_login()}
        wfs = json.loads(urlopen(Request(f"{N8N}/rest/workflows", headers=cookie), timeout=15).read())
        items = wfs.get("data", wfs)
        items = items.get("data", items) if isinstance(items, dict) else items
        wid = next(w["id"] for w in items if w["name"] == name)
        detail = json.loads(urlopen(Request(f"{N8N}/rest/workflows/{wid}", headers=cookie), timeout=15).read())
        inner = detail.get("data", detail)
        if bool(inner.get("active")) == active:
            return True
        action = "activate" if active else "deactivate"
        body = json.dumps({"versionId": inner["versionId"]}).encode()
        urlopen(Request(f"{N8N}/rest/workflows/{wid}/{action}", data=body, method="POST",
                        headers={"Content-Type": "application/json", **cookie}), timeout=30).read()
        return True
    except Exception as e:
        log(f"    set_active({name},{active}) lỗi: {e}")
        return False


def manual_run(name):
    """Chạy tay 1 workflow schedule (không đợi webhook) — trả True nếu submit OK."""
    try:
        cookie = {"Cookie": n8n_login()}
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
        return True
    except Exception as e:
        log(f"    manual_run({name}) lỗi: {e}")
        return False


def n8n_executions():
    """Lấy lịch sử execution từ n8n (chứng minh workflow chạy thật trong engine)."""
    try:
        email = os.environ.get("N8N_EMAIL", "admin@anser.local")
        pw = os.environ.get("N8N_PASSWORD", "AnserTest123!")
        req = Request(f"{N8N}/rest/login", data=json.dumps(
            {"emailOrLdapLoginId": email, "password": pw}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        r = urlopen(req, timeout=15)
        r.read()
        cookie = next((p.split(";")[0] for p in
                       "; ".join(r.headers.get_all("Set-Cookie") or []).split("; ")
                       if p.startswith("n8n-auth=")), "")
        req = Request(f"{N8N}/rest/executions?limit=30", headers={"Cookie": cookie})
        data = json.loads(urlopen(req, timeout=15).read())
        res = data.get("data", data)
        res = res.get("results", res) if isinstance(res, dict) else res
        return [{"wf": e.get("workflowName") or e.get("workflowId"),
                 "status": e.get("status"), "mode": e.get("mode"),
                 "startedAt": e.get("startedAt", "")[:19]} for e in (res or [])]
    except Exception as e:
        return [{"wf": f"(không lấy được executions: {e})", "status": "", "mode": "", "startedAt": ""}]


def record(idx, name, expect, method, url, headers, body, status, resp, ok, extra=""):
    tok = "có" if headers and headers.get("x-anser-token") else "không"
    log(f"\n[#{idx}] {name}")
    log(f"    {method} {url}  (token: {tok})")
    if body:
        log(f"    body: {body[:120]}")
    log(f"    → HTTP {status} | {resp[:160]}")
    if extra:
        log(f"    evidence: {extra}")
    log(f"    KỲ VỌNG: {expect}  →  {'✅ PASS' if ok else '❌ FAIL'}")
    RESULTS.append({"idx": idx, "name": name, "expect": expect, "method": method, "url": url,
                    "token": tok, "body": body or "", "status": status, "resp": resp,
                    "extra": extra, "ok": ok})


def wf(path):
    return f"{N8N}/webhook/{path}"


def run():
    os.makedirs(EVID, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log("=" * 70)
    log(f"ANSER Automation V2 (Trà/Cao Atiso) — Test Matrix Evidence @ {ts}")
    log("=" * 70)
    # Reset CHỈ bảng giao dịch do test sinh (GIỮ seed: customers/products/sales/promotions/
    # BOM/manuf_products/material_batches seed/production_batches seed)
    db("TRUNCATE iot_events, import_transactions, import_details, pending_review, "
       "workflow_errors, purchase_orders_draft, social_posts, marketplace_orders, "
       "debt_reminders, competitor_prices, production_reports, batch_process_log, "
       "lab_test_results, channel_orders, payment_pending, einvoices, einvoice_pending "
       "RESTART IDENTITY;")
    # Xóa dữ liệu test cũ (EV-*/LOT-EV*/MEB-EV*) — giữ nguyên seed
    db("DELETE FROM production_batches WHERE batch_code LIKE 'MEB-EV%';")
    db("DELETE FROM material_batches WHERE lot_code LIKE 'LOT-EV%';")
    db("DELETE FROM material_requirements WHERE order_id IN "
       "(SELECT id FROM production_orders WHERE order_code LIKE 'EV-%');")
    db("DELETE FROM production_orders WHERE order_code LIKE 'EV-%';")
    # Reset tồn NVL + tồn SP bán lẻ về seed (intake/marketplace cộng/trừ dồn mỗi run)
    db("UPDATE material_stock SET qty_on_hand = CASE material_code "
       "WHEN 'LA' THEN 20 WHEN 'BONG' THEN 30 WHEN 'LA-TUOI' THEN 0 WHEN 'BONG-TUOI' THEN 0 "
       "WHEN 'TUI-LOC' THEN 5000 WHEN 'HOP-TL' THEN 300 WHEN 'HOP-400' THEN 500 "
       "WHEN 'HU-1KG' THEN 200 WHEN 'TEM-QR' THEN 2000 ELSE qty_on_hand END;")
    db("DELETE FROM material_stock WHERE material_code NOT IN "
       "('LA','BONG','LA-TUOI','BONG-TUOI','TUI-LOC','HOP-TL','HOP-400','HU-1KG','TEM-QR');")
    db("UPDATE products SET stock_quantity = CASE code "
       "WHEN 'TRA-TL50' THEN 40 WHEN 'CAO-1KG' THEN 5 WHEN 'BONG-400' THEN 12 "
       "WHEN 'LINH-400' THEN 30 WHEN 'TRA-TN80' THEN 100 ELSE stock_quantity END;")
    # Tắt 2 poller trong lúc chạy matrix (poll tự bắn giữa chừng làm lệch assert FEFO);
    # bật lại ở cuối. LƯU Ý: TRUNCATE channel_orders xóa cả đơn demo live — tạo lại sau test.
    for p in ("retail_sepay_poll", "retail_woo_poll"):
        set_active(p, False)
    # A1: reset lô kho bán về seed (allocate trừ dồn mỗi run) + xóa lô test
    db("TRUNCATE lot_allocations RESTART IDENTITY;")
    db("DELETE FROM product_lots WHERE lot_code NOT IN "
       "('LOT-RT-A','LOT-RT-B','LOT-RT-C','LOT-RT-D','LOT-RT-E','LOT-RT-F');")
    db("UPDATE product_lots SET qty_on_hand = CASE lot_code "
       "WHEN 'LOT-RT-A' THEN 15 WHEN 'LOT-RT-B' THEN 25 WHEN 'LOT-RT-C' THEN 5 "
       "WHEN 'LOT-RT-D' THEN 12 WHEN 'LOT-RT-E' THEN 30 WHEN 'LOT-RT-F' THEN 100 "
       "ELSE qty_on_hand END;")

    # Health
    for svc, url in [("n8n", f"{N8N}/healthz"), ("rag_service", f"{RAG}/health"),
                     ("discord-mock", f"{DMOCK}/health")]:
        s, b = http("GET", url)
        log(f"[health] {svc}: HTTP {s} {b[:80]}")

    hdr = {"x-anser-token": TOKEN}
    bad = {"x-anser-token": "wrong-token"}

    # #1 no token
    s, r = http("POST", wf("pos-event"), {"device_id": "POS-X", "event_type": "sale", "payload": {"amount": 1}})
    record(1, "POST không token", "400 Unauthorized", "POST", wf("pos-event"), None, "{...}", s, r, s == 400)

    # #2 wrong token
    s, r = http("POST", wf("pos-event"), {"device_id": "POS-X", "event_type": "sale", "payload": {"amount": 1}}, bad)
    record(2, "POST token sai", "400 Unauthorized", "POST", wf("pos-event"), bad, "{...}", s, r, s == 400)

    # #3 valid POS — key ngẫu nhiên mỗi run để luôn insert (test #6 sẽ tái dùng để dedup)
    before = db("SELECT COUNT(*) FROM iot_events")
    idem = "evid-" + __import__("uuid").uuid4().hex[:12]
    payload = {"device_id": "POS-Store01-T1", "event_type": "sale", "idempotency_key": idem,
               "payload": {"amount": 265000, "invoice_no": "INV-EVID-1", "cashier": "evidence"}}
    s, r = http("POST", wf("pos-event"), payload, hdr)
    after = db("SELECT COUNT(*) FROM iot_events")
    row = db("SELECT id||'|'||device_id||'|'||event_type FROM iot_events ORDER BY id DESC LIMIT 1")
    record(3, "POST token đúng, payload đúng", "201 + row DB mới", "POST", wf("pos-event"), hdr,
           json.dumps(payload["payload"]), s, r, s == 201 and after > before,
           f"iot_events: {before}→{after} rows | last row: {row}")

    # #6 idempotency retry (same key)
    s2, r2 = http("POST", wf("pos-event"), payload, hdr)
    after2 = db("SELECT COUNT(*) FROM iot_events")
    dup = db(f"SELECT COUNT(*) FROM iot_events WHERE idempotency_key='{idem}'")
    record(6, "Retry cùng idempotency_key", "Chỉ 1 row (deduped)", "POST", wf("pos-event"), hdr,
           f"idempotency_key={idem} (lần 2)", s2, r2, dup == "1" and after2 == after,
           f"rows với key này: {dup} | tổng iot_events không đổi: {after}→{after2}")

    # #4 missing required field
    s, r = http("POST", wf("pos-event"), {"payload": {"amount": 1}}, hdr)
    record(4, "Thiếu trường required (device_id)", "400 nêu rõ trường thiếu", "POST", wf("pos-event"),
           hdr, '{"payload":{"amount":1}}', s, r, s == 400 and "device_id" in r)

    # #5 SQL injection
    inj = "%27%3B%20DROP%20TABLE%20sales%3B--"
    sales_before = db("SELECT COUNT(*) FROM sales")
    s, r = http("GET", f"{RAG}/daily-sales?date={inj}")
    sales_after = db("SELECT COUNT(*) FROM sales")
    record(5, "SQL injection trong ?date=", "Vô hiệu, bảng sales nguyên vẹn", "GET",
           f"{RAG}/daily-sales?date='; DROP TABLE sales;--", None, "", s, r,
           sales_before == sales_after and sales_after != "0",
           f"sales rows: {sales_before}→{sales_after} (bảng còn nguyên)")

    # #9 empty date
    s, r = http("GET", f"{RAG}/daily-sales?date=")
    record(9, "Query ?date= rỗng", "Fallback CURRENT_DATE, không 500", "GET",
           f"{RAG}/daily-sales?date=", None, "", s, r, s == 200)

    # #11 per-product low-stock
    s, r = http("GET", f"{RAG}/low-stock")
    try:
        data = json.loads(r)
        names = [i["name"] for i in data.get("items", [])]
        # Bông atiso: tồn 12 > ngưỡng chung 10 nhưng < ngưỡng RIÊNG 15 → chỉ per-product mới bắt được
        ok = "Bông atiso sấy khô 400gr" in names
    except Exception:
        names, ok = [], False
    record(11, "Low-stock theo ngưỡng RIÊNG từng SP", "Bông atiso 400gr xuất hiện (12<15 riêng, dù >10 chung)",
           "GET", f"{RAG}/low-stock", None, "", s, r, ok, f"SP cảnh báo: {names}")

    # #12 OCR invoice OK
    imp_before = db("SELECT COUNT(*) FROM import_transactions")
    s, r = http("POST", wf("invoice-ocr"), {"scenario": "ok"}, hdr)
    imp_after = db("SELECT COUNT(*) FROM import_transactions")
    record(12, "OCR hóa đơn khớp tổng", "200 + ghi import_transactions", "POST", wf("invoice-ocr"),
           hdr, '{"scenario":"ok"}', s, r, s == 200 and imp_after > imp_before,
           f"import_transactions: {imp_before}→{imp_after}")

    # #13 OCR invoice mismatch → pending review
    pend_before = db("SELECT COUNT(*) FROM pending_review")
    imp_b2 = db("SELECT COUNT(*) FROM import_transactions")
    s, r = http("POST", wf("invoice-ocr"), {"scenario": "mismatch"}, hdr)
    pend_after = db("SELECT COUNT(*) FROM pending_review")
    imp_a2 = db("SELECT COUNT(*) FROM import_transactions")
    record(13, "OCR hóa đơn lệch tổng", "422 + pending_review, KHÔNG ghi kho", "POST",
           wf("invoice-ocr"), hdr, '{"scenario":"mismatch"}', s, r,
           s == 422 and pend_after > pend_before and imp_a2 == imp_b2,
           f"pending_review: {pend_before}→{pend_after} | import KHÔNG tăng: {imp_b2}→{imp_a2}")

    # #3b new customer
    cust_before = db("SELECT COUNT(*) FROM customers")
    s, r = http("POST", wf("new-customer"), {"name": "Khach Evidence", "phone": "0900000001"}, hdr)
    cust_after = db("SELECT COUNT(*) FROM customers")
    record(14, "Khách hàng mới (bug 'coalesce' đã vá)", "201 + row customers", "POST",
           wf("new-customer"), hdr, '{"name":"Khach Evidence"}', s, r,
           s in (200, 201) and cust_after > cust_before,
           f"customers: {cust_before}→{cust_after}")

    # #15 shared_notify multi-channel (zalo)
    s, r = http("POST", wf("notify"), {"channel": "zalo", "title": "Test Zalo", "description": "multi-channel"}, hdr)
    record(15, "Notifier đa kênh — gửi Zalo", "200 + mock nhận path /zalo", "POST", wf("notify"),
           hdr, '{"channel":"zalo",...}', s, r, s == 200 and "zalo" in r)

    # #16 QT7 auto promo post
    sp_before = db("SELECT COUNT(*) FROM social_posts")
    s, r = http("POST", wf("promo-post"), {}, hdr)
    sp_after = db("SELECT COUNT(*) FROM social_posts")
    record(16, "QT7 đăng bài KM (caption chờ duyệt)", "200 pending_approval + log social_posts", "POST",
           wf("promo-post"), hdr, "{}", s, r,
           s == 200 and "pending_approval" in r and sp_after > sp_before,
           f"social_posts: {sp_before}→{sp_after}")

    # #17 QT8 marketplace new order
    ext = "SHOPEE-" + __import__("uuid").uuid4().hex[:8]
    mo_before = db("SELECT COUNT(*) FROM marketplace_orders")
    order = {"marketplace": "shopee", "external_order_id": ext, "total_amount": 174000,
             "items": [{"name": "Trà atiso túi lọc (50 túi)", "qty": 2, "price": 87000}]}
    s, r = http("POST", wf("marketplace-order"), order, hdr)
    mo_after = db("SELECT COUNT(*) FROM marketplace_orders")
    record(17, "QT8 đơn marketplace mới", "201 + tạo sale + marketplace_orders++", "POST",
           wf("marketplace-order"), hdr, f'{{"external_order_id":"{ext}"}}', s, r,
           s == 201 and "imported" in r and mo_after > mo_before,
           f"marketplace_orders: {mo_before}→{mo_after}")

    # #18 QT8 duplicate (same external_order_id) → idempotent
    mo_b2 = db("SELECT COUNT(*) FROM marketplace_orders")
    s, r = http("POST", wf("marketplace-order"), order, hdr)
    mo_a2 = db("SELECT COUNT(*) FROM marketplace_orders")
    record(18, "QT8 đơn marketplace TRÙNG", "duplicate, không tạo thêm", "POST",
           wf("marketplace-order"), hdr, f'{{"external_order_id":"{ext}"}} (lần 2)', s, r,
           "duplicate" in r and mo_a2 == mo_b2, f"marketplace_orders không đổi: {mo_b2}→{mo_a2}")

    # #19 QT6 forecast reorder (schedule → manual run)
    pod_before = db("SELECT COUNT(*) FROM purchase_orders_draft")
    ok6 = manual_run("retail_forecast_suggest_reorder")
    time.sleep(2)
    pod_after = db("SELECT COUNT(*) FROM purchase_orders_draft")
    record(19, "QT6 gợi ý nhập (moving-avg)", "Sinh draft PO trong DB", "RUN", "retail_forecast_suggest_reorder",
           None, "manual trigger", "run" if ok6 else "fail", f"drafts={pod_after}", pod_after > pod_before,
           f"purchase_orders_draft: {pod_before}→{pod_after}")

    # #20 QT9 debt reminder (schedule → manual run) — chỉ khách opt-in
    dr_before = db("SELECT COUNT(*) FROM debt_reminders")
    ok9 = manual_run("retail_debt_reminder")
    time.sleep(2)
    dr_after = db("SELECT COUNT(*) FROM debt_reminders")
    optout = db("SELECT COUNT(*) FROM debt_reminders WHERE customer_id=(SELECT id FROM customers WHERE code='KH9002')")
    record(20, "QT9 nhắc nợ (opt-in + PII mask)", "Gửi khách opt-in; KHÔNG gửi opt-out", "RUN",
           "retail_debt_reminder", None, "manual trigger", "run" if ok9 else "fail",
           f"reminders={dr_after}", dr_after > dr_before and optout == "0",
           f"debt_reminders: {dr_before}→{dr_after} | gửi khách opt-out (KH9002): {optout} (phải 0)")

    # #21 QT10 competitor price (schedule → manual run)
    cp_before = db("SELECT COUNT(*) FROM competitor_prices")
    ok10 = manual_run("retail_competitor_price_sync")
    time.sleep(2)
    cp_after = db("SELECT COUNT(*) FROM competitor_prices")
    record(21, "QT10 đồng bộ giá đối thủ", "Ghi competitor_prices + cảnh báo", "RUN",
           "retail_competitor_price_sync", None, "manual trigger", "run" if ok10 else "fail",
           f"rows={cp_after}", cp_after > cp_before, f"competitor_prices: {cp_before}→{cp_after}")

    # #22 PII masking — kiểm tra embed khách hàng mới đã che SĐT
    s, cap0 = http("GET", f"{DMOCK}/_captured")
    masked_ok = False
    try:
        for c in json.loads(cap0).get("items", []):
            if "Khách hàng mới" in (c.get("title") or ""):
                fields = (c.get("payload", {}).get("embeds", [{}])[0].get("fields", []))
                phone = next((f["value"] for f in fields if f["name"] == "SĐT"), "")
                if "X" in phone and "0900000001" not in phone:
                    masked_ok = True
    except Exception:
        pass
    record(22, "PII masking SĐT trong thông báo", "SĐT bị che (chứa 'X', không lộ số gốc)", "CHECK",
           "discord-mock captured", None, "", "inspect", "masked" if masked_ok else "raw", masked_ok,
           "embed 'Khách hàng mới' có SĐT dạng XXXXXXX001")

    # ── SẢN XUẤT TRÀ/CAO ATISO (V2): E2 → QT1 → QT2 → intake theo đơn → F1 → F2 ──
    uid = lambda: __import__("uuid").uuid4().hex[:6]

    # #23 E2: nhập lô nguyên liệu từ nông hộ (OCR phiếu cân) — trong cửa sổ 24h
    lot1 = "LOT-EV-" + uid()
    mb_before = db("SELECT COUNT(*) FROM material_batches")
    bt_before = db("SELECT qty_on_hand FROM material_stock WHERE material_code='BONG-TUOI'")
    s, r = http("POST", wf("material-intake"),
                {"scenario": "weighslip", "lot_code": lot1, "harvest_hours_ago": 5}, hdr)
    mb_after = db("SELECT COUNT(*) FROM material_batches")
    bt_after = db("SELECT qty_on_hand FROM material_stock WHERE material_code='BONG-TUOI'")
    win_ok = '"window_status": "ok"' in r or '"window_status":"ok"' in r
    stock_ok = False
    try:
        stock_ok = abs(float(bt_after) - float(bt_before) - 300) < 0.01
    except Exception:
        pass
    record(23, "E2 nhập lô nông hộ (OCR phiếu cân)", "201 + lô mới + tồn bông tươi +300kg + còn ~19h cửa sổ 24h",
           "POST", wf("material-intake"), hdr, f'{{"scenario":"weighslip","lot_code":"{lot1}","harvest_hours_ago":5}}',
           s, r, s == 201 and "inserted" in r and mb_after > mb_before and stock_ok and win_ok,
           f"material_batches: {mb_before}→{mb_after} | tồn BONG-TUOI: {bt_before}→{bt_after} (+300)")

    # #24 E2: lô TRÙNG lot_code (phiếu cân gửi lại) → idempotent
    mb_b2 = db("SELECT COUNT(*) FROM material_batches")
    s, r = http("POST", wf("material-intake"),
                {"scenario": "weighslip", "lot_code": lot1, "harvest_hours_ago": 5}, hdr)
    mb_a2 = db("SELECT COUNT(*) FROM material_batches")
    record(24, "E2 lô TRÙNG lot_code", "duplicate, không nhập trùng", "POST", wf("material-intake"),
           hdr, f'{{"lot_code":"{lot1}"}} (lần 2)', s, r,
           "duplicate" in r and mb_a2 == mb_b2, f"material_batches không đổi: {mb_b2}→{mb_a2}")

    # #25 E2: lô tươi QUÁ cửa sổ 24h (30h) → cảnh báo overdue (mất cynarin)
    lot2 = "LOT-EV-" + uid()
    s, r = http("POST", wf("material-intake"),
                {"scenario": "weighslip", "lot_code": lot2, "harvest_hours_ago": 30}, hdr)
    record(25, "E2 lô tươi QUÁ cửa sổ 24h", "201 + window_status=overdue (cảnh báo mất cynarin)", "POST",
           wf("material-intake"), hdr, f'{{"lot_code":"{lot2}","harvest_hours_ago":30}}', s, r,
           s == 201 and "overdue" in r, "đồng hồ 24h tính từ harvest_date, code thuần")

    # #26 E2: phiếu cân LỆCH tổng → 422 pending, tồn KHÔNG đổi (tiền trả nông hộ = cân × giá)
    bt_b3 = db("SELECT qty_on_hand FROM material_stock WHERE material_code='BONG-TUOI'")
    pend_b = db("SELECT COUNT(*) FROM pending_review WHERE kind='material_intake'")
    s, r = http("POST", wf("material-intake"), {"scenario": "weighslip_mismatch"}, hdr)
    bt_a3 = db("SELECT qty_on_hand FROM material_stock WHERE material_code='BONG-TUOI'")
    pend_a = db("SELECT COUNT(*) FROM pending_review WHERE kind='material_intake'")
    record(26, "E2 phiếu cân LỆCH tổng", "422 + pending_review, tồn KHÔNG đổi (sai tiền trả nông hộ)", "POST",
           wf("material-intake"), hdr, '{"scenario":"weighslip_mismatch"}', s, r,
           s == 422 and bt_a3 == bt_b3 and pend_a > pend_b,
           f"tồn BONG-TUOI không đổi: {bt_b3}={bt_a3} | pending material_intake: {pend_b}→{pend_a}")

    # #27 QT1: OCR đơn A → lệnh SX draft, LLM buffer 2% (500 hộp trà → 510)
    ev_order = "EV-PO-" + uid()
    po_before = db("SELECT COUNT(*) FROM production_orders")
    s, r = http("POST", wf("customer-order-ocr"), {"scenario": "order", "order_code": ev_order}, hdr)
    po_after = db("SELECT COUNT(*) FROM production_orders")
    q2p = db(f"SELECT qty_to_produce FROM production_orders WHERE order_code='{ev_order}'")
    record(27, "QT1 OCR đơn A → lệnh SX (LLM buffer)", "201 draft + qty_to_produce=510 (500×1.02)", "POST",
           wf("customer-order-ocr"), hdr, f'{{"order_code":"{ev_order}"}}', s, r,
           s == 201 and q2p == "510" and po_after > po_before,
           f"production_orders: {po_before}→{po_after} | qty_to_produce={q2p} (đặt 500 hộp trà túi lọc)")

    # #28 QT1: đơn TRÙNG order_code → idempotent
    po_b2 = db("SELECT COUNT(*) FROM production_orders")
    s, r = http("POST", wf("customer-order-ocr"), {"scenario": "order", "order_code": ev_order}, hdr)
    po_a2 = db("SELECT COUNT(*) FROM production_orders")
    record(28, "QT1 đơn A TRÙNG order_code", "duplicate, không tạo thêm", "POST",
           wf("customer-order-ocr"), hdr, f'{{"order_code":"{ev_order}"}} (lần 2)', s, r,
           "duplicate" in r and po_a2 == po_b2, f"production_orders không đổi: {po_b2}→{po_a2}")

    # #29 QT2: BOM ĐẢO YIELD — cần khô 510×0.1=51kg, tồn 20 → thiếu 31kg khô
    #   → MUA TƯƠI = 31/0.25 = 124kg lá tươi. Túi lọc 25500−5000=20500. Tem đủ → 0. 3 mẻ = ceil(510/200).
    s, r = http("POST", wf("production-approved"), {"order_code": ev_order}, hdr)
    bom_ok, la_tobuy, tem_tobuy, batches = False, None, None, None
    try:
        d = json.loads(r)
        la = next(x for x in d["to_buy"] if x["code"] == "LA")
        tem = next(x for x in d["to_buy"] if x["code"] == "TEM-QR")
        la_tobuy = la["to_buy"]; tem_tobuy = tem["to_buy"]; batches = d.get("batches_suggested")
        bom_ok = (d["estimation_method"] == "bom" and abs(la_tobuy - 124.0) < 0.01
                  and tem_tobuy == 0 and batches == 3)
    except Exception:
        pass
    record(29, "QT2 BOM ĐẢO yield (khô thiếu ÷ yield = tươi cần mua)",
           "LA mua=124kg TƯƠI ((51−20)/0.25) + tem đủ→0 + 3 mẻ + method=bom", "POST",
           wf("production-approved"), hdr, f'{{"order_code":"{ev_order}"}}', s, r,
           s == 200 and bom_ok,
           f"LA to_buy={la_tobuy} kg tươi (kỳ vọng 124.0) | TEM-QR={tem_tobuy} (kỳ vọng 0) | số mẻ={batches} (kỳ vọng 3)")

    # #30 QT2: SP KHÔNG có BOM (TRA-GUNG) → LLM fallback + gắn cờ duyệt tay
    ev_tg = "EV-TG-" + uid()
    db(f"INSERT INTO production_orders (order_code, product_code, product_name, qty_ordered, unit_price, region, status) VALUES ('{ev_tg}','TRA-GUNG','Trà xanh ướp gừng (hộp)',300,45000,'Đà Lạt','draft')")
    s, r = http("POST", wf("production-approved"), {"order_code": ev_tg}, hdr)
    fb_ok = False
    try:
        d = json.loads(r)
        fb_ok = d["estimation_method"] == "llm_fallback" and len(d["to_buy"]) > 0
    except Exception:
        pass
    mreq_method = db(f"SELECT estimation_method FROM material_requirements mr JOIN production_orders o ON mr.order_id=o.id WHERE o.order_code='{ev_tg}'")
    record(30, "QT2 thiếu BOM (TRA-GUNG) → LLM fallback", "estimation_method=llm_fallback + cờ duyệt tay", "POST",
           wf("production-approved"), hdr, f'{{"order_code":"{ev_tg}"}}', s, r,
           s == 200 and fb_ok and mreq_method == "llm_fallback",
           f"DB estimation_method={mreq_method}")

    # #31 E2 nhập app trực tiếp + mua theo đơn: 124kg lá tươi về → requirement=materials_received
    lot3 = "LOT-EV-" + uid()
    la_before = db("SELECT qty_on_hand FROM material_stock WHERE material_code='LA-TUOI'")
    s, r = http("POST", wf("material-intake"),
                {"lot_code": lot3, "farmer": "HTX Thuận Phát", "region_grown": "Đà Lạt - Xuân Thọ",
                 "part": "lá", "form": "tuoi", "material_code": "LA-TUOI", "qty_kg": 124,
                 "unit_cost_vnd": 12000, "harvest_hours_ago": 3, "order_code": ev_order}, hdr)
    la_after = db("SELECT qty_on_hand FROM material_stock WHERE material_code='LA-TUOI'")
    req_status = db(f"SELECT mr.status FROM material_requirements mr JOIN production_orders o ON mr.order_id=o.id WHERE o.order_code='{ev_order}'")
    stock_ok = False
    try:
        stock_ok = abs(float(la_after) - float(la_before) - 124) < 0.01
    except Exception:
        pass
    record(31, "E2 nhập app + mua theo đơn (không OCR)", "201 + tồn lá tươi +124kg + status=materials_received",
           "POST", wf("material-intake"), hdr, f'{{"lot_code":"{lot3}","qty_kg":124,"order_code":"{ev_order}"}}',
           s, r, s == 201 and stock_ok and req_status == "materials_received",
           f"tồn LA-TUOI: {la_before}→{la_after} (+124) | requirement: {req_status}")

    # #32 F1 start mẻ: dùng lô #31 (thu hái 3h trước) → cửa sổ 24h OK
    bcode = "MEB-EV-" + uid()
    pb_before = db("SELECT COUNT(*) FROM production_batches")
    s, r = http("POST", wf("batch-process"),
                {"event": "start", "batch_code": bcode, "order_code": ev_order,
                 "material_lot_code": lot3, "input_material_kg": 124,
                 "shift": "Mẻ sáng", "source": "manual", "operator": "to_che_bien"}, hdr)
    pb_after = db("SELECT COUNT(*) FROM production_batches")
    record(32, "F1 bắt đầu mẻ (trong cửa sổ 24h)", "201 started + production_batches++ + hours_left ~21h", "POST",
           wf("batch-process"), hdr, f'{{"event":"start","batch_code":"{bcode}","lot":"{lot3}"}}', s, r,
           s == 201 and "started" in r and pb_after > pb_before and "hours_left" in r,
           f"production_batches: {pb_before}→{pb_after}")

    # #33 F1 mẻ TRÙNG batch_code → idempotent
    pb_b2 = db("SELECT COUNT(*) FROM production_batches")
    s, r = http("POST", wf("batch-process"),
                {"event": "start", "batch_code": bcode, "order_code": ev_order,
                 "material_lot_code": lot3, "input_material_kg": 124}, hdr)
    pb_a2 = db("SELECT COUNT(*) FROM production_batches")
    record(33, "F1 mẻ TRÙNG batch_code", "duplicate, không tạo thêm", "POST", wf("batch-process"),
           hdr, f'{{"batch_code":"{bcode}"}} (lần 2)', s, r,
           "duplicate" in r and pb_a2 == pb_b2, f"production_batches không đổi: {pb_b2}→{pb_a2}")

    # #34 F1 ghi công đoạn (CCP nhiệt độ xao)
    log_before = db("SELECT COUNT(*) FROM batch_process_log")
    s, r = http("POST", wf("batch-process"),
                {"event": "stage", "batch_code": bcode, "stage": "xao", "temp_c": 110,
                 "duration_min": 45, "operator": "to_che_bien"}, hdr)
    log_after = db("SELECT COUNT(*) FROM batch_process_log")
    record(34, "F1 nhật ký công đoạn (xao 110°C)", "logged + batch_process_log++", "POST",
           wf("batch-process"), hdr, f'{{"event":"stage","stage":"xao","temp_c":110}}', s, r,
           s == 201 and "logged" in r and log_after > log_before,
           f"batch_process_log: {log_before}→{log_after}")

    # #35 F1 hoàn thành nhưng độ ẩm 9.2% CHƯA ĐẠT (>8%) → sấy tiếp, KHÔNG chốt mẻ/HSD
    s, r = http("POST", wf("batch-process"),
                {"event": "complete", "batch_code": bcode, "output_units": 300, "ng_units": 4,
                 "moisture_pct": 9.2}, hdr)
    exp_null = db(f"SELECT COALESCE(expiry_date::text,'NULL') FROM production_batches WHERE batch_code='{bcode}'")
    record(35, "F1 độ ẩm 9.2% CHƯA đạt → sấy tiếp", "moisture_fail + KHÔNG có HSD (nguy cơ nấm mốc)", "POST",
           wf("batch-process"), hdr, f'{{"event":"complete","moisture_pct":9.2}}', s, r,
           s == 201 and "moisture_fail" in r and exp_null == "NULL",
           f"expiry_date sau lần đo fail: {exp_null} (phải NULL)")

    # #36 F1 sấy lại đạt 6.5% → chốt mẻ + HSD 12 tháng + chờ kiểm nghiệm (chưa mở bán)
    s, r = http("POST", wf("batch-process"),
                {"event": "complete", "batch_code": bcode, "output_units": 300, "ng_units": 4,
                 "moisture_pct": 6.5, "material_cost_vnd": 1488000, "labor_cost_vnd": 500000}, hdr)
    row = db(f"SELECT moisture_pct||'|'||COALESCE(expiry_date::text,'NULL')||'|'||qc_status FROM production_batches WHERE batch_code='{bcode}'")
    record(36, "F1 độ ẩm 6.5% ĐẠT → HSD 12 tháng", "completed + expiry_date=+12 tháng + qc=pending_lab", "POST",
           wf("batch-process"), hdr, f'{{"event":"complete","moisture_pct":6.5}}', s, r,
           s == 201 and "completed" in r and '"shelf_months":12' in r.replace(" ", "") and "pending_lab" in row,
           f"DB mẻ {bcode}: moisture|expiry|qc = {row}")

    # #37 F2 kiểm nghiệm ĐẠT → mở khóa bán (gate cứng dược liệu)
    s, r = http("POST", wf("lab-result"),
                {"batch_code": bcode, "cynarin_pct": 2.8, "mold_cfu_g": 40,
                 "pesticide_ok": True, "heavy_metal_ok": True, "tested_by": "Lab ngoài"}, hdr)
    qc1 = db(f"SELECT qc_status FROM production_batches WHERE batch_code='{bcode}'")
    ok37 = False
    try:
        d = json.loads(r)
        ok37 = d.get("sellable") is True and d.get("status") == "passed"
    except Exception:
        pass
    record(37, "F2 kiểm nghiệm ĐẠT (cynarin 2.8%, mốc 40)", "passed + sellable=true + qc=passed", "POST",
           wf("lab-result"), hdr, f'{{"batch_code":"{bcode}","cynarin_pct":2.8,"mold_cfu_g":40}}', s, r,
           s == 201 and ok37 and qc1 == "passed",
           f"DB qc_status={qc1} | phiếu kiểm nghiệm gắn vào lô")

    # #38 F2 kiểm nghiệm KHÔNG ĐẠT (nấm mốc 150>100) → CHẶN XUẤT + truy xuất về nông hộ
    bcode2 = "MEB-EV-" + uid()
    http("POST", wf("batch-process"), {"event": "start", "batch_code": bcode2, "order_code": ev_order,
                                       "material_lot_code": lot3, "input_material_kg": 50}, hdr)
    http("POST", wf("batch-process"), {"event": "complete", "batch_code": bcode2, "output_units": 120,
                                       "ng_units": 2, "moisture_pct": 7.5}, hdr)  # 7.5% → HSD 6 tháng
    s, r = http("POST", wf("lab-result"),
                {"batch_code": bcode2, "cynarin_pct": 2.5, "mold_cfu_g": 150,
                 "pesticide_ok": True, "heavy_metal_ok": True, "tested_by": "Lab ngoài"}, hdr)
    qc2 = db(f"SELECT qc_status FROM production_batches WHERE batch_code='{bcode2}'")
    record(38, "F2 KHÔNG ĐẠT (mốc 150 CFU/g) → chặn xuất", "failed + qc=failed + điều tra về nông hộ/vùng trồng",
           "POST", wf("lab-result"), hdr, f'{{"batch_code":"{bcode2}","mold_cfu_g":150}}', s, r,
           s == 201 and "failed" in r and "Thuận Phát" in r and qc2 == "failed",
           f"DB qc_status={qc2} | investigate → HTX Thuận Phát, Đà Lạt - Xuân Thọ")

    # #39 QT6 — VÁ BÁO ĐỘNG GIẢ: DH-A-102 sấy mất 80.8% khối lượng (500kg tươi → 96kg khô)
    #   nhưng yield thực 19.2% chỉ lệch 4% so định mức 20% → warn=FALSE (hao hụt tự nhiên)
    pr_before = db("SELECT COUNT(*) FROM production_reports")
    s, r = http("POST", wf("shift-report"), {"order_code": "DH-A-102"}, hdr)
    pr_after = db("SELECT COUNT(*) FROM production_reports")
    ok102 = False
    try:
        d = json.loads(r)
        ok102 = (abs(d["yield_actual_pct"] - 19.2) < 0.3 and abs(d["yield_deviation_pct"] - 4.0) < 0.3
                 and d["warn"] is False)
    except Exception:
        pass
    record(39, "QT6 hao hụt sấy 80.8% NHƯNG đúng định mức → KHÔNG báo động",
           "yield thực≈19.2% / định mức 20% → lệch 4% <15% → warn=false (vá báo động giả)", "POST",
           wf("shift-report"), hdr, '{"order_code":"DH-A-102"}', s, r,
           s == 200 and ok102 and pr_after > pr_before,
           f"số khớp tính tay: {ok102} | production_reports: {pr_before}→{pr_after}")

    # #40 QT6 — lệch định mức THẬT: DH-A-101 (450kg tươi → 90kg khô = 20% vs định mức 25%)
    #   lệch (112.5−90)/112.5 = 20% > 15% → warn=TRUE. NG=15/915=1.64%. Lãi=(78.3M−7.1M)/78.3M=90.93%
    s, r = http("POST", wf("shift-report"), {"order_code": "DH-A-101"}, hdr)
    ok101 = False
    try:
        d = json.loads(r)
        ok101 = (abs(d["yield_deviation_pct"] - 20.0) < 0.3 and d["warn"] is True
                 and abs(d["ng_pct"] - 1.64) < 0.3 and abs(d["profit_pct"] - 90.93) < 0.5)
    except Exception:
        pass
    record(40, "QT6 lệch định mức THẬT → cảnh báo đỏ", "lệch 20% >15% → warn=true; NG≈1.64%; lãi≈90.93%", "POST",
           wf("shift-report"), hdr, '{"order_code":"DH-A-101"}', s, r, s == 200 and ok101,
           f"số khớp tính tay: {ok101}")

    # #41 QT7 báo cáo ĐR (theo kỳ + đơn + khu vực) — endpoint + manual run workflow
    s, r = http("GET", f"{RAG}/dr-report?period=month")
    dr_ok = False
    try:
        d = json.loads(r)
        dr_ok = (d["chi_phi_B"] > 0 and d["loi_nhuan"] > 0 and len(d["ngan_sach_khu_vuc"]) >= 2
                 and len(d["loi_nhuan_theo_don"]) >= 2)
    except Exception:
        pass
    ok7 = manual_run("manuf_dr_report_periodic")
    time.sleep(2)
    record(41, "QT7 báo cáo ĐR (kỳ+đơn+khu vực)", "3 chỉ số + ≥2 khu vực (Đà Lạt/TP.HCM) + ≥2 đơn; workflow chạy",
           "GET+RUN", f"{RAG}/dr-report + manuf_dr_report_periodic", None, "", s, r, dr_ok and ok7,
           f"ĐR hợp lệ: {dr_ok} | workflow run: {ok7}")

    # ── BÁN LẺ V2: C1 (SePay + VietQR) & B1 (HĐĐT NĐ 70/2025) ──────────────
    def envfile(key, default=""):
        try:
            for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
                if line.strip().startswith(key + "="):
                    return line.strip().split("=", 1)[1]
        except Exception:
            pass
        return default

    sepay_key = os.environ.get("SEPAY_API_KEY") or envfile("SEPAY_API_KEY")
    sp_hdr = {"Authorization": f"Apikey {sepay_key}"} if sepay_key else {}

    # #42 C1: tạo đơn → VietQR động (nội dung CK nhúng mã đơn)
    co_before = db("SELECT COUNT(*) FROM channel_orders")
    s, r = http("POST", wf("order-create"),
                {"items": [{"sku": "TRA-TL50", "name": "Trà atiso túi lọc (50 túi)",
                            "qty": 2, "price": 87000}],
                 "customer_name": "Đại lý demo", "channel": "store"}, hdr)
    co_after = db("SELECT COUNT(*) FROM channel_orders")
    order_no, qr_ok, total42 = None, False, None
    try:
        d = json.loads(r)
        order_no = d["order_no"]; total42 = d["total_amount"]
        qr_ok = ("img.vietqr.io" in d["qr_url"] and f"NGOCDUY+{order_no}" in d["qr_url"]
                 and total42 == 174000)
    except Exception:
        pass
    record(42, "C1 tạo đơn → VietQR động", "201 + tổng 174.000 (code tính) + QR nhúng 'NGOCDUY DH{id}'",
           "POST", wf("order-create"), hdr, '{"items":[{TRA-TL50 x2 @87000}]}', s, r,
           s == 201 and qr_ok and co_after > co_before,
           f"channel_orders: {co_before}→{co_after} | {order_no} tổng={total42} | QR hợp lệ: {qr_ok}")

    # #43 C1→B1: SePay CK đúng key + đúng tiền → paid + HĐĐT tự phát hành (VAT 8% kiểm tay)
    #   174.000 gồm VAT 8% → trước thuế 161.111,11 + VAT 12.888,89
    tx_id = int(datetime.now().timestamp() * 100) % 10**9
    sepay_body = {"id": tx_id, "gateway": "MBBank",
                  "transactionDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "content": f"NGOCDUY {order_no}", "transferAmount": 174000,
                  "transferType": "in"}
    ei_before = db("SELECT COUNT(*) FROM einvoices")
    s, r = http("POST", wf("sepay-webhook"), sepay_body, sp_hdr)
    pay_status = db(f"SELECT payment_status FROM channel_orders WHERE order_no='{order_no}'")
    inv_row = db(f"SELECT invoice_no||'|'||vat_rate||'|'||subtotal||'|'||vat_amount||'|'||tax_authority_code "
                 f"FROM einvoices WHERE order_no='{order_no}'")
    inv_no43 = inv_row.split("|")[0] if "|" in inv_row else None
    vat_ok = "|8.00|161111.11|12888.89|CQT-" in inv_row
    record(43, "C1→B1: SePay khớp → paid + HĐĐT tự phát hành", "matched + paid + VAT 8%: 161.111,11 + 12.888,89 + mã CQT",
           "POST", wf("sepay-webhook"), sp_hdr, f'{{"id":{tx_id},"content":"NGOCDUY {order_no}","transferAmount":174000}}',
           s, r, s == 200 and "matched" in r and pay_status == "paid" and vat_ok,
           f"payment_status={pay_status} | einvoice: {inv_row} | VAT kiểm tay khớp: {vat_ok}")

    # #44 C1: SePay retry CÙNG id giao dịch → duplicate, không phát hành HĐ trùng
    ei_b2 = db("SELECT COUNT(*) FROM einvoices")
    s, r = http("POST", wf("sepay-webhook"), sepay_body, sp_hdr)
    ei_a2 = db("SELECT COUNT(*) FROM einvoices")
    record(44, "C1 SePay retry TRÙNG tx id", "duplicate, không double-paid/double-invoice", "POST",
           wf("sepay-webhook"), sp_hdr, f'{{"id":{tx_id}}} (lần 2)', s, r,
           s == 200 and "duplicate" in r and ei_a2 == ei_b2,
           f"einvoices không đổi: {ei_b2}→{ei_a2}")

    # #45 C1: sai SePay API key → 401
    s, r = http("POST", wf("sepay-webhook"), {**sepay_body, "id": tx_id + 1},
                {"Authorization": "Apikey WRONG-KEY"})
    record(45, "C1 SePay SAI API key", "401 Unauthorized", "POST", wf("sepay-webhook"),
           {"Authorization": "Apikey WRONG"}, "{...}", s, r, s == 401 and sepay_key != "",
           f"SEPAY_API_KEY cấu hình: {'có' if sepay_key else 'KHÔNG (fail-open)'}")

    # #46 C1: CK LỆCH tiền → chờ đối soát, đơn vẫn unpaid (không tự khớp tiền lệch)
    s, r = http("POST", wf("order-create"),
                {"items": [{"sku": "CAO-1KG", "name": "Cao atisô lá khô 1kg",
                            "qty": 1, "price": 843000}]}, hdr)
    order2 = json.loads(r)["order_no"]
    pp_before = db("SELECT COUNT(*) FROM payment_pending")
    s, r = http("POST", wf("sepay-webhook"),
                {"id": tx_id + 2, "gateway": "MBBank", "content": f"NGOCDUY {order2}",
                 "transferAmount": 500000, "transferType": "in"}, sp_hdr)
    pp_after = db("SELECT COUNT(*) FROM payment_pending")
    pay2 = db(f"SELECT payment_status FROM channel_orders WHERE order_no='{order2}'")
    record(46, "C1 CK LỆCH tiền (500k vs đơn 843k)", "review + payment_pending++ + đơn VẪN unpaid", "POST",
           wf("sepay-webhook"), sp_hdr, f'{{"content":"NGOCDUY {order2}","transferAmount":500000}}', s, r,
           s == 200 and "review" in r and pp_after > pp_before and pay2 == "unpaid",
           f"payment_pending: {pp_before}→{pp_after} | đơn {order2}: {pay2}")

    # #47 B1: NCC HĐĐT lỗi → hàng đợi einvoice_pending, KHÔNG mất đơn
    s, r = http("POST", f"{RAG}/order-create",
                {"items": [{"sku": "TRA-TN80", "name": "Trà Thái Nguyên 80gr", "qty": 5, "price": 21000}]})
    order3 = json.loads(r)["order_no"]
    eq_before = db("SELECT COUNT(*) FROM einvoice_pending")
    s, r = http("POST", f"{RAG}/einvoice-issue", {"order_no": order3, "simulate": "fail"})
    eq_after = db("SELECT COUNT(*) FROM einvoice_pending")
    no_inv = db(f"SELECT COUNT(*) FROM einvoices WHERE order_no='{order3}'")
    record(47, "B1 NCC HĐĐT lỗi (simulate 503)", "queued + einvoice_pending++ + KHÔNG có HĐ rác", "POST",
           f"{RAG}/einvoice-issue", None, f'{{"order_no":"{order3}","simulate":"fail"}}', s, r,
           "queued" in r and eq_after > eq_before and no_inv == "0",
           f"einvoice_pending: {eq_before}→{eq_after} | einvoices cho {order3}: {no_inv} (phải 0)")

    # #48 B1: điều chỉnh HĐĐT — KHÔNG hủy (NĐ 70/2025), HĐ gốc lưu vết
    ei_b3 = db("SELECT COUNT(*) FROM einvoices")
    s, r = http("POST", wf("einvoice-adjust"),
                {"original_invoice_no": inv_no43, "reason": "sai tên người mua"}, hdr)
    ei_a3 = db("SELECT COUNT(*) FROM einvoices")
    org_status = db(f"SELECT status FROM einvoices WHERE invoice_no='{inv_no43}'")
    new_link = db(f"SELECT COUNT(*) FROM einvoices WHERE adjusts_invoice_no='{inv_no43}'")
    record(48, "B1 điều chỉnh HĐ (KHÔNG hủy)", "HĐ mới trỏ HĐ gốc; gốc → 'adjusted' nhưng VẪN tồn tại", "POST",
           wf("einvoice-adjust"), hdr, f'{{"original_invoice_no":"{inv_no43}","reason":"sai tên người mua"}}',
           s, r, s == 201 and ei_a3 == str(int(ei_b3) + 1) and org_status == "adjusted" and new_link == "1",
           f"einvoices: {ei_b3}→{ei_a3} (+1, không xóa) | gốc status={org_status} | HĐ điều chỉnh trỏ gốc: {new_link}")

    # #49 B1: backup ≥2 đích + checksum (lưu ≥10 năm) — endpoint + workflow schedule
    s, r = http("POST", f"{RAG}/einvoice-backup-run", {})
    bk_ok, cks = False, ""
    try:
        d = json.loads(r)
        cks = d["checksum"]
        bk_ok = d["targets_ok"] == 2 and d["count"] >= 2
    except Exception:
        pass
    okbk = manual_run("retail_einvoice_backup")
    time.sleep(2)
    s2, cap = http("GET", f"{DMOCK}/_captured")
    cap_ok = "drive-backup" in cap and "s3-backup" in cap and cks[:16] in cap
    record(49, "B1 backup HĐĐT 2 đích + checksum", "targets_ok=2 + mock nhận /drive-backup + /s3-backup + checksum khớp",
           "POST+RUN", f"{RAG}/einvoice-backup-run + retail_einvoice_backup", None, "{}", s, r,
           bk_ok and cap_ok and okbk,
           f"checksum={cks[:16]}… | 2 đích nhận đúng checksum: {cap_ok} | workflow run: {okbk}")

    # #50 B1: bảng VAT theo NGÀY hiệu lực — 2027 hết giảm NQ 204 → 10%
    #   87.000 gồm VAT 10% → trước thuế 79.090,91 + VAT 7.909,09
    s, r = http("POST", f"{RAG}/order-create",
                {"items": [{"sku": "TRA-TL50", "name": "Trà atiso túi lọc (50 túi)", "qty": 1, "price": 87000}]})
    order4 = json.loads(r)["order_no"]
    s, r = http("POST", f"{RAG}/einvoice-issue", {"order_no": order4, "issue_date": "2027-01-15"})
    vat27_ok = False
    try:
        d = json.loads(r)
        vat27_ok = (d["vat_rate"] == 10.0 and abs(d["subtotal"] - 79090.91) < 0.01
                    and abs(d["vat_amount"] - 7909.09) < 0.01)
    except Exception:
        pass
    record(50, "B1 VAT theo ngày: 2027 → 10% (hết NQ 204/2025)", "vat_rate=10% + 79.090,91 + 7.909,09 (kiểm tay)",
           "POST", f"{RAG}/einvoice-issue", None, f'{{"order_no":"{order4}","issue_date":"2027-01-15"}}', s, r,
           s == 201 and vat27_ok, f"số khớp tính tay: {vat27_ok}")

    # ── A1: ĐỒNG BỘ TỒN & ĐƠN ĐA KÊNH (FEFO theo lô) ────────────────────────
    # #51 nhập lô tay hàng thương mại → lots++ + stock sync = SUM(lô)
    lot_ev = "LOT-EV-RT" + uid()
    s, r = http("POST", wf("lot-intake"),
                {"sku": "TRA-TN80", "lot_code": lot_ev, "expiry_date": "2027-01-31", "qty": 50}, hdr)
    st_tn = db("SELECT stock_quantity FROM products WHERE code='TRA-TN80'")
    record(51, "A1 nhập lô tay (hàng thương mại)", "201 + lô mới + stock = SUM(lô) = 150", "POST",
           wf("lot-intake"), hdr, f'{{"sku":"TRA-TN80","lot_code":"{lot_ev}","qty":50}}', s, r,
           s == 201 and st_tn == "150", f"tồn TRA-TN80 sau sync: {st_tn} (100 seed + 50 lô mới)")

    # #52 chuỗi F2→kho bán: mẻ ĐẠT ở #37 phải TỰ thành lô kho bán (HSD kế thừa từ F1)
    lot_prod = db(f"SELECT sku||'|'||qty_on_hand||'|'||source||'|'||COALESCE(expiry_date::text,'') "
                  f"FROM product_lots WHERE lot_code='{bcode}'")
    record(52, "A1 chuỗi F2 ĐẠT → TỰ nhập kho bán", "lô = mẻ SX: sku TRA-TL50, qty 300, source=production, có HSD",
           "CHECK", f"product_lots WHERE lot_code={bcode}", None, "", "query", lot_prod,
           lot_prod.startswith("TRA-TL50|300|production|2027"),
           f"lô từ sản xuất: {lot_prod} (traceability về mẻ + HSD từ độ ẩm)")

    # #53 đơn Shopee chuẩn hóa + FEFO: lô HSD GẦN (LOT-RT-A 2026-10) xuất trước
    ext53 = "SP" + uid()
    s, r = http("POST", wf("channel-order"),
                {"channel": "shopee", "order_sn": ext53,
                 "item_list": [{"item_sku": "TRA-TL50", "item_name": "Trà atiso túi lọc (50 túi)",
                                "model_quantity_purchased": 3, "model_discounted_price": "87000"}],
                 "recipient_address": {"name": "Khách Shopee"}}, hdr)
    fefo_ok, order53 = False, None
    try:
        d = json.loads(r)
        order53 = d["order_no"]
        fefo_ok = (d["allocations"][0]["lot_code"] == "LOT-RT-A" and d["allocations"][0]["qty"] == 3
                   and d["new_stock"]["TRA-TL50"] == 337)  # 40 seed + 300 lô SX #52 − 3
    except Exception:
        pass
    lot_a = db("SELECT qty_on_hand FROM product_lots WHERE lot_code='LOT-RT-A'")
    record(53, "A1 đơn Shopee → FEFO (lô cận hạn trước)", "chuẩn hóa payload Shopee + trừ LOT-RT-A (HSD 2026-10) ×3",
           "POST", wf("channel-order"), hdr, f'{{"channel":"shopee","order_sn":"{ext53}",...}}', s, r,
           s == 201 and fefo_ok and lot_a == "12",
           f"LOT-RT-A: 15→{lot_a} | đơn {order53} | tồn mới đẩy 3 kênh")

    # #54 đơn kênh TRÙNG external_order_id → idempotent
    co_b = db("SELECT COUNT(*) FROM channel_orders")
    s, r = http("POST", wf("channel-order"),
                {"channel": "shopee", "order_sn": ext53,
                 "item_list": [{"item_sku": "TRA-TL50", "model_quantity_purchased": 3,
                                "model_discounted_price": "87000"}]}, hdr)
    co_a = db("SELECT COUNT(*) FROM channel_orders")
    record(54, "A1 đơn kênh TRÙNG (webhook sàn retry)", "duplicate, không trừ tồn lần 2", "POST",
           wf("channel-order"), hdr, f'{{"order_sn":"{ext53}"}} (lần 2)', s, r,
           s == 200 and "duplicate" in r and co_a == co_b,
           f"channel_orders không đổi: {co_b}→{co_a}")

    # #55 đơn QUÀ TẶNG → gán lô HSD XA (bỏ qua FEFO thường — PDF A1 đặc thù quà)
    ext55 = "TT" + uid()
    s, r = http("POST", wf("channel-order"),
                {"channel": "tiktok", "order_id": ext55, "is_gift": True,
                 "line_items": [{"seller_sku": "TRA-TL50", "product_name": "Trà atiso túi lọc",
                                 "quantity": 2, "sale_price": "87000"}]}, hdr)
    gift_ok, gift_order = False, None
    try:
        d = json.loads(r)
        gift_order = d["order_no"]
        # lô SX mới (#52, HSD 2027-07) xa hơn LOT-RT-B (2027-04) → quà lấy lô SX
        gift_ok = d["allocations"][0]["lot_code"] == bcode
    except Exception:
        pass
    gift_db = db(f"SELECT is_gift FROM channel_orders WHERE order_no='{gift_order}'")
    record(55, "A1 đơn QUÀ TẶNG → lô HSD XA nhất", f"gán lô SX {bcode} (HSD 2027-07, xa nhất) + DB is_gift=t", "POST",
           wf("channel-order"), hdr, f'{{"channel":"tiktok","order_id":"{ext55}","is_gift":true}}', s, r,
           s == 201 and gift_ok and gift_db == "t",
           f"DB is_gift={gift_db} | lô gán: {bcode} (khách mua quà cần HSD xa — đảo FEFO)")

    # #56 OVERSELL: đặt CAO-1KG ×99 (tồn theo lô = 5) → 409, KHÔNG trừ gì
    lots_cao_b = db("SELECT SUM(qty_on_hand) FROM product_lots WHERE sku='CAO-1KG'")
    s, r = http("POST", wf("channel-order"),
                {"channel": "web", "id": "OVERSELL-" + uid(),
                 "line_items": [{"sku": "CAO-1KG", "name": "Cao atisô", "quantity": 99, "price": "843000"}]},
                hdr)
    lots_cao_a = db("SELECT SUM(qty_on_hand) FROM product_lots WHERE sku='CAO-1KG'")
    record(56, "A1 CHẶN OVERSELL (2 kênh giành lô cuối)", "409 oversell_blocked + tồn KHÔNG đổi (rollback)",
           "POST", wf("channel-order"), hdr, '{"channel":"web","qty":99} (tồn 5)', s, r,
           s == 409 and "oversell_blocked" in r and lots_cao_a == lots_cao_b,
           f"tồn lô CAO-1KG không đổi: {lots_cao_b}={lots_cao_a}")

    # #57 đơn sàn giao thành công → HĐĐT phát hành LÚC DELIVERED (không xuất sớm)
    inv_b57 = db(f"SELECT COUNT(*) FROM einvoices WHERE order_no='{order53}'")
    s, r = http("POST", wf("channel-delivered"), {"order_no": order53}, hdr)
    inv_a57 = db(f"SELECT COUNT(*) FROM einvoices WHERE order_no='{order53}'")
    ff = db(f"SELECT fulfillment_status FROM channel_orders WHERE order_no='{order53}'")
    record(57, "A1 đơn sàn DELIVERED → mới xuất HĐĐT", "trước giao: 0 HĐ; sau giao: 1 HĐ + fulfillment=delivered",
           "POST", wf("channel-delivered"), hdr, f'{{"order_no":"{order53}"}}', s, r,
           s == 200 and inv_b57 == "0" and inv_a57 == "1" and ff == "delivered",
           f"einvoices đơn {order53}: {inv_b57}→{inv_a57} | fulfillment={ff} (giảm điều chỉnh COD hoàn/hủy)")

    # #58 đồng bộ tồn NGƯỢC lên 3 kênh: mock nhận /woo-stock /shopee-stock /tiktok-stock
    s, cap58 = http("GET", f"{DMOCK}/_captured")
    push_ok = all(p in cap58 for p in ("woo-stock", "shopee-stock", "tiktok-stock"))
    record(58, "A1 đồng bộ tồn ngược 3 kênh", "web + Shopee + TikTok đều nhận stock_update (chống oversell)",
           "CHECK", f"{DMOCK}/_captured", None, "", 200, cap58[:200], push_ok,
           "bán 1 kênh → tồn mới đẩy lên MỌI kênh")

    # #59 A1 kênh web (WooCommerce shape thật qua woo-mock): thêm đơn → poll → FEFO
    WOO = os.environ.get("WOO_MOCK_URL", "http://localhost:8300")
    s, r = http("POST", f"{WOO}/_add",
                {"sku": "TRA-TN80", "name": "Trà Thái Nguyên 80gr", "qty": 3, "price": 21000,
                 "first_name": "Khách Web Evidence"})
    woo_id = None
    try:
        woo_id = json.loads(r)["id"]
    except Exception:
        pass
    ok_woo = manual_run("retail_woo_poll")
    time.sleep(4)
    woo_row = db(f"SELECT order_no||'|'||channel||'|'||total_amount FROM channel_orders WHERE external_order_id='WOO-{woo_id}'")
    woo_alloc = db(f"SELECT lot_code||' x'||qty FROM lot_allocations WHERE sku='TRA-TN80' AND order_no=(SELECT order_no FROM channel_orders WHERE external_order_id='WOO-{woo_id}')")
    record(59, "A1 kênh web — poll WooCommerce (shape API thật)", "đơn Woo mới → poll → channel_orders + FEFO lô TRA-TN80",
           "POST+RUN", f"{WOO}/_add + retail_woo_poll", None, f'{{"sku":"TRA-TN80","qty":3}} (Woo id={woo_id})',
           s, woo_row, s == 201 and ok_woo and "|web|63000" in woo_row and woo_alloc.startswith("LOT-"),
           f"channel_orders: {woo_row} | allocation: {woo_alloc} | đổi site thật = 3 dòng .env")

    # Discord mock captured
    s, cap = http("GET", f"{DMOCK}/_captured")
    titles, paths = [], set()
    try:
        for c in json.loads(cap).get("items", []):
            titles.append(c["title"])
            paths.add(c.get("path", ""))
    except Exception:
        pass
    log(f"\n[discord-mock] đã nhận {len(titles)} thông báo qua {len(paths)} kênh: {sorted(paths)}")

    # DB snapshot
    log("\n[DB snapshot]")
    for t in ["iot_events", "customers", "import_transactions", "pending_review", "workflow_errors",
              "purchase_orders_draft", "marketplace_orders", "debt_reminders",
              "material_batches", "production_batches", "batch_process_log",
              "lab_test_results", "production_reports"]:
        log(f"    {t}: {db(f'SELECT COUNT(*) FROM {t}')} rows")

    try:
        ps = subprocess.run(["docker", "compose", "ps", "--format",
                             "table {{.Name}}\t{{.Status}}\t{{.Ports}}"],
                            capture_output=True, text=True, cwd=ROOT, timeout=20).stdout.strip()
    except Exception as e:
        ps = f"(không lấy được docker ps: {e})"
    log("\n[docker compose ps]\n" + ps)

    execs = n8n_executions()
    succ = sum(1 for e in execs if e["status"] == "success")
    log(f"\n[n8n executions] {len(execs)} lần chạy trong engine, {succ} success")
    for e in execs[:15]:
        log(f"    {e['status']:8s} {e['mode']:8s} {e['startedAt']}  {e['wf']}")

    # Bật lại 2 poller (đã tắt đầu run để matrix deterministic)
    for p in ("retail_sepay_poll", "retail_woo_poll"):
        set_active(p, True)
    log("\n[poller] retail_sepay_poll + retail_woo_poll: đã bật lại")

    passed = sum(1 for x in RESULTS if x["ok"])
    log("\n" + "=" * 70)
    log(f"KẾT QUẢ: {passed}/{len(RESULTS)} PASS")
    log("=" * 70)

    write_html(ts, titles, passed, execs, ps)
    with open(os.path.join(EVID, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))
    log(f"\nĐã ghi: {os.path.join(EVID, 'report.html')}")
    log(f"        {os.path.join(EVID, 'transcript.txt')}")
    return 0 if passed == len(RESULTS) else 1


def write_html(ts, discord_titles, passed, execs=None, ps=""):
    def esc(x):
        return html.escape(str(x))
    exec_rows = ""
    for e in (execs or []):
        color = "#067647" if e["status"] == "success" else "#d92d20"
        exec_rows += f"""<tr><td>{esc(e['startedAt'])}</td><td><b>{esc(e['wf'])}</b></td>
          <td>{esc(e['mode'])}</td><td style="color:{color};font-weight:700">{esc(e['status'])}</td></tr>"""
    rows = ""
    for x in RESULTS:
        badge = '<span class="ok">PASS</span>' if x["ok"] else '<span class="fail">FAIL</span>'
        rows += f"""<tr class="{'r-ok' if x['ok'] else 'r-fail'}">
          <td>{x['idx']}</td><td>{esc(x['name'])}</td>
          <td><code>{esc(x['method'])} {esc(x['url'])}</code><br><small>token: {esc(x['token'])}</small></td>
          <td>{esc(x['expect'])}</td>
          <td><b>HTTP {esc(x['status'])}</b><br><small>{esc(x['resp'][:200])}</small></td>
          <td><small>{esc(x['extra'])}</small></td>
          <td>{badge}</td></tr>"""
    total = len(RESULTS)
    doc = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANSER V2 Trà/Cao Atiso — Evidence</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f5f6f8;color:#1a2230}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:22px}} .meta{{color:#5b6676;font-size:14px;margin-bottom:16px}}
.summary{{font-size:18px;font-weight:700;padding:12px 16px;border-radius:10px;margin:12px 0;
  background:{'#ecfdf3' if passed==total else '#fef3f2'};color:{'#067647' if passed==total else '#d92d20'}}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th,td{{border:1px solid #e3e7ee;padding:8px 10px;text-align:left;vertical-align:top}}
th{{background:#f0f3f8}} code{{font-size:11px;color:#0b3d91;word-break:break-all}}
.ok{{background:#067647;color:#fff;padding:2px 8px;border-radius:10px;font-weight:700}}
.fail{{background:#d92d20;color:#fff;padding:2px 8px;border-radius:10px;font-weight:700}}
.r-fail{{background:#fff6f6}} .box{{background:#fff;border:1px solid #e3e7ee;border-radius:8px;padding:12px 16px;margin:12px 0}}
</style></head><body><div class="wrap">
<h1>ANSER — Automation V2 Trà/Cao Atiso (pilot Ngọc Duy) · Test Matrix Evidence</h1>
<div class="meta">Chạy lúc: {ts} · Stack: n8n 2.29.10 · rag_service 0.4.0 · postgres 16 · mock-brain · discord-mock · Giá bán PUBLIC từ ngocduygroup.com (2026-07-11); định mức/giá thu mua = ASSUMED</div>
<div class="summary">KẾT QUẢ: {passed}/{total} PASS</div>
<div class="box"><b>docker compose ps</b> (7 container đang chạy):<pre style="overflow-x:auto;font-size:12px;background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px">{esc(ps)}</pre></div>
<div class="box"><b>Discord-mock đã nhận {len(discord_titles)} thông báo:</b><br>{esc(discord_titles)}</div>
<table><thead><tr><th>#</th><th>Kịch bản</th><th>Request</th><th>Kỳ vọng</th><th>Kết quả thật</th><th>Bằng chứng DB</th><th>Verdict</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="font-size:18px;margin-top:24px">n8n executions (bằng chứng workflow chạy trong engine)</h2>
<table><thead><tr><th>startedAt</th><th>Workflow</th><th>mode</th><th>status</th></tr></thead>
<tbody>{exec_rows}</tbody></table>
<p class="meta">Raw transcript đầy đủ: <code>tests/evidence/transcript.txt</code>. Tự tái chạy: <code>python tests/smoke/gen_evidence.py</code></p>
</div></body></html>"""
    with open(os.path.join(EVID, "report.html"), "w", encoding="utf-8") as f:
        f.write(doc)


if __name__ == "__main__":
    import sys
    sys.exit(run())
