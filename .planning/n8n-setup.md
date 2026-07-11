# n8n Self-hosted Setup Notes

## Cài đặt

**Môi trường:** Windows 11 + Docker Desktop + WSL2

**Khởi động:**
```powershell
cd d:\new_project
docker compose up -d
```

**Dừng:**
```powershell
docker compose down
```

**Kiểm tra trạng thái:**
```powershell
docker compose ps
```

---

## Cổng & URL

| Service     | URL local                  | Ghi chú                        |
|-------------|----------------------------|--------------------------------|
| n8n UI      | http://localhost:5678      | Đăng nhập bằng tài khoản owner |
| ChromaDB    | http://localhost:8000      | REST API v2                    |
| RAG Service | http://localhost:8001      | /query, /init, /health         |

---

## Dữ liệu & Volume

- n8n lưu workflow, credentials, execution logs trong Docker volume `new_project_n8n_data`
- Workflow **không mất** khi restart container nhờ volume mount
- Backup thủ công: vào n8n UI → Settings → Export workflow JSON

---

## Các khái niệm cốt lõi n8n

| Khái niệm     | Mô tả                                                              |
|---------------|--------------------------------------------------------------------|
| **Workflow**  | Một pipeline gồm nhiều node nối với nhau                           |
| **Node**      | Một bước xử lý: gọi API, chạy code, gửi email, v.v.               |
| **Trigger**   | Node đầu tiên kích hoạt workflow (Webhook / Schedule / Manual)     |
| **Credentials** | Thông tin xác thực (API key, OAuth) lưu mã hóa trong n8n         |
| **Execution** | Một lần chạy workflow — xem log tại tab Executions                 |

---

## Webhook URL

Khi workflow **Active**, Webhook node tạo URL nhận request từ bên ngoài:

**Format:**
```
http://localhost:5678/webhook/<path>
```

**Ví dụ workflow AI Security:**
```
POST http://localhost:5678/webhook/analyze-log
Content-Type: application/json
x-anser-token: <ANSER_WEBHOOK_TOKEN trong .env>   # SEC-3: bắt buộc nếu token đã cấu hình

{ "event_type": "authentication_failure", "source_ip": "1.2.3.4", ... }
```

### Expose ra ngoài cho IoT / thiết bị khác gọi vào

**Option A — n8n tunnel (dev only, không cần cài thêm):**
- Vào n8n Settings → n8n tunnel → bật ON
- n8n tự tạo URL dạng `https://xxxx.hooks.n8n.cloud/webhook/...`

**Option B — ngrok (ổn định hơn):**
```powershell
# Cài ngrok, sau đó:
ngrok http 5678
# Copy URL https://xxxx.ngrok-free.app
# Webhook URL: https://xxxx.ngrok-free.app/webhook/analyze-log
```

---

## 2 Workflow mẫu

### Workflow 1 — Webhook nhận JSON, trả 200

Import file: `workflows/sample_webhook_echo.json`

Luồng: `Webhook (POST /echo)` → `Code (log + return data)` 

Test:
```powershell
curl -X POST http://localhost:5678/webhook/echo `
  -H "Content-Type: application/json" `
  -d '{"test": "hello"}'
```

### Workflow 2 — Schedule 5 phút gọi HTTP Request

Import file: `workflows/sample_schedule_http.json`

Luồng: `Schedule (every 5 min)` → `HTTP Request (GET httpbin.org/get)` → `Code (log result)`

---

## Trạng thái hiện tại (dự án AI Security)

- [x] n8n chạy ổn định
- [x] ChromaDB + RAG Service chạy
- [x] Knowledge base 12 tài liệu MITRE ATT&CK đã nạp
- [x] Workflow "AI Security Log Analyzer" đã import & publish
- [ ] Kết nối LLM (Qwen2.5 trên Colab GPU L4) — cần chạy `colab_llm_server.py`
- [ ] Cập nhật webhook.site URL vào node Mock Alert
- [ ] Test end-to-end với log mẫu
