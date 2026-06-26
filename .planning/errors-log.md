# Error Log — Lỗi phát sinh và cách khắc phục

## Lỗi đã gặp trong quá trình setup

---

### ERR-001: Docker "WSL needs updating"
**Triệu chứng:** Docker Desktop hiện "Your version of WSL is too old"
**Nguyên nhân:** WSL chưa cài hoặc quá cũ
**Khắc phục:**
```powershell
# Chạy PowerShell với quyền Admin
wsl --install
Restart-Computer
```
**Sau restart:** Docker Desktop → "Try Again" là xong

---

### ERR-002: ChromaDB healthcheck "unhealthy"
**Triệu chứng:** `docker compose ps` → chromadb hiện `(unhealthy)`; n8n không start
**Nguyên nhân:** Container không có `curl` hoặc `python` → healthcheck command fail
**Khắc phục:** Bỏ healthcheck khỏi docker-compose.yml, đổi `depends_on` thành đơn giản:
```yaml
depends_on:
  - chromadb   # thay vì condition: service_healthy
```

---

### ERR-003: ChromaDB "v1 API deprecated"
**Triệu chứng:** `{"error":"Unimplemented","message":"The v1 API is deprecated. Please use /v2 apis"}`
**Nguyên nhân:** Image `chromadb/chroma:latest` đã upgrade lên v2 API — URL path thay đổi
**Khắc phục:**
- Đổi tất cả `/api/v1/` → `/api/v2/tenants/default_tenant/databases/default_database/`
- Hoặc dùng chromadb Python client (tự xử lý version)

---

### ERR-004: ChromaDB add documents "missing field embeddings"
**Triệu chứng:** `Failed to deserialize the JSON body: missing field 'embeddings'`
**Nguyên nhân:** ChromaDB v2 REST API yêu cầu embeddings khi add document
**Khắc phục:** Tạo RAG microservice (FastAPI + chromadb Python client) — client tự generate embeddings bằng model all-MiniLM-L6-v2

---

### ERR-005: RAG Service timeout khi init lần đầu
**Triệu chứng:** `TimeoutError` khi chạy `init_chromadb.py`
**Nguyên nhân:** Container đang download embedding model (79.3MB) — lần đầu mất 3-5 phút
**Khắc phục:**
1. Tăng timeout trong script lên 600 giây
2. Theo dõi tiến trình: `docker compose logs rag-service`
3. Chờ thấy `100%` trong log rồi chạy lại

---

### ERR-006: n8n "Problem importing workflow — Required"
**Triệu chứng:** Import JSON vào n8n hiện popup lỗi "Required"
**Nguyên nhân:** Node `respondToWebhook` thiếu field bắt buộc `respondWith`, hoặc `httpRequest` node có tham số không tương thích với version n8n
**Khắc phục:**
- Chuyển tất cả HTTP call sang **Code node** dùng `$http` thay vì httpRequest node
- Dùng `typeVersion: 1` cho `if` node (format conditions đơn giản hơn)
- Đảm bảo `respondToWebhook` có `respondWith: "json"` (trường bắt buộc)

---

### ERR-007: Workflow import tạo nhiều bản trùng
**Triệu chứng:** Canvas có 3-4 pipeline chồng nhau với tên "Receive Log1", "Receive Log2"
**Nguyên nhân:** Import nhiều lần mà không xóa workflow cũ
**Khắc phục:**
1. Ctrl+A → Delete (xóa tất cả node)
2. "..." → Delete (xóa cả workflow)
3. Import lại từ đầu — chỉ 1 lần

---

### ERR-008: Alembic "command not found" trên Bash tool
**Triệu chứng:** `alembic: command not found`
**Nguyên nhân:** Alembic cài trong Python của Windows, không có trong PATH của Bash tool
**Khắc phục:** Dùng PowerShell hoặc `python -m alembic`:
```powershell
python -m alembic upgrade head
```

---

### ERR-009: Docker Desktop không start được sau restart
**Triệu chứng:** `failed to connect to docker API at npipe:///./pipe/dockerDesktopLinuxEngine`
**Nguyên nhân:** Docker Desktop chưa được mở / đang khởi động
**Khắc phục:** Mở Docker Desktop từ Start Menu, chờ "Engine running" ở góc dưới trái (~30 giây), rồi chạy lại lệnh

---

---

### ERR-010: Webhook validation báo "Missing required fields" dù payload có đủ field
**Triệu chứng:** `HTTP 200: {"valid": false, "error": "Missing required fields: device_id, event_type"}` dù request JSON có đủ `device_id` và `event_type`
**Nguyên nhân:** n8n v1 wrap JSON body của POST request vào `$json.body` thay vì để trực tiếp ở `$json`. Code dùng `$input.first().json.device_id` nhưng data thực tế nằm ở `$input.first().json.body.device_id`
**Khắc phục:** Thêm fallback trong Code node:
```js
const raw = $input.first().json;
const body = (raw.body && typeof raw.body === 'object') ? raw.body : raw;
```

---

---

### ERR-011: `$http is not defined` trong Code node
**Triệu chứng:** Node "Save to NeonDB" trả `db_error: "$http is not defined"`
**Nguyên nhân:** `$http` chỉ tồn tại trong n8n Expression context, KHÔNG có trong Code node sandbox
**Khắc phục:** Thay toàn bộ `$http.post(url, body, opts)` bằng native `fetch()`:
```js
// Thay vì:
const res = await $http.post(url, body, { headers: {...} });
const data = res.data;

// Dùng:
const res = await fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body)
});
const data = await res.json();
```

---

### ERR-012: `fetch is not defined` / `$helpers is not defined` trong Code node
**Triệu chứng:** Node lần lượt trả `"fetch is not defined"` rồi `"$helpers is not defined"` khi thử các API khác nhau
**Nguyên nhân:** n8n Code node chạy trong vm2 sandbox bị giới hạn nghiêm: không có `fetch`, không có `$http`, không có `$helpers` (chỉ có ở custom node), không có `axios`
**Khắc phục:** Dùng `require('http')` / `require('https')` — Node.js built-in, luôn được vm2 whitelist:
```js
const reqBody = JSON.stringify({ device_id: d.device_id, ... });
const data = await new Promise((resolve, reject) => {
  const req = require('http').request({
    hostname: 'rag-service', port: 8001, path: '/iot-insert', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(reqBody) }
  }, res => {
    let raw = ''; res.on('data', c => raw += c);
    res.on('end', () => { try { resolve(JSON.parse(raw)); } catch(e) { resolve({}); } });
  });
  req.on('error', reject); req.write(reqBody); req.end();
});
// Dùng require('https') cho URL bên ngoài (Discord, webhook.site, ngrok...)
```
**LƯU Ý QUAN TRỌNG:** `require('http')` cũng bị chặn vì n8n vm2 sandbox có `builtin: []`. Không có cách nào gọi HTTP từ Code node. Giải pháp đúng duy nhất: dùng **HTTP Request node** trong workflow. Code node chỉ được dùng để transform data.

---

### ERR-013: HTTP Request node không execute, workflow trả empty response
**Triệu chứng:** Workflow active, webhook đăng ký đúng, nhưng 0 executions được ghi + response body rỗng (`HTTP 0`)
**Nguyên nhân:** `typeVersion: 4.2` không hợp lệ với n8n v2.20.11 (defaultVersion = **4.4**). n8n từ chối execute workflow khi gặp typeVersion không nhận ra, KHÔNG log bất kỳ error nào.
**Khắc phục:** Đổi tất cả HTTP Request nodes sang `"typeVersion": 4.4`
**Cách kiểm tra version:**
```bash
docker exec new_project-n8n-1 node -e "
const n = require('.../HttpRequest.node.js');
console.log('defaultVersion:', new (Object.values(n)[0])().description?.defaultVersion);
"
```

---

### ERR-014: `relation "iot_events" does not exist` — rag-service HTTP 500
**Triệu chứng:** `rag-service /iot-insert` trả HTTP 500: `"relation \"iot_events\" does not exist"`; workflow n8n fail ở node "Call iot-insert"
**Nguyên nhân:** `alembic_version` ghi `001` (migration đã chạy) nhưng bảng `iot_events` không tồn tại trong schema `public` — bảng có thể đã bị drop thủ công hoặc migration ran trên branch NeonDB khác
**Khắc phục:**
```python
# 1. Xóa version cũ (force Alembic re-run migration 001)
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("DELETE FROM alembic_version WHERE version_num = '001'")
conn.commit()

# 2. Chạy lại migration
# python -m alembic upgrade head
```
**Kết quả:** Bảng `iot_events` được tạo, pipeline chạy hoàn toàn — HTTP 201 + NeonDB insert + Discord notification

---

## Template ghi lỗi mới

```
### ERR-XXX: <Tên lỗi ngắn gọn>
**Triệu chứng:** <Thông báo lỗi hoặc hành vi quan sát được>
**Nguyên nhân:** <Tại sao xảy ra>
**Khắc phục:** <Các bước fix>
```
