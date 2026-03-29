# ANSER — Group Project AI/ML · USTH GEN14

> Nền tảng AI/ML tích hợp: OCR hóa đơn, dự báo LSTM, agent AI tự động, quản lý bán lẻ.

---

## Khởi động nhanh

```bash
python app.py                        # App chính (Flask, cổng 5000)
python dl_service/model_app.py       # Deep learning service (OCR, LSTM, cổng 5001)
python ai_agent_service/main.py      # AI agent server (Qwen + Vision)
```

---

## Cấu trúc thư mục

```
app.py                  # Entry point chính — create_app() factory
core/                   # Shared: config, auth, database, extensions, models
  extensions.py         # Flask singletons (login_manager, csrf, limiter, db_manager)
  models.py             # User model
dl_service/             # REST API cho OCR và LSTM forecasting
ai_agent_service/       # Agent tự động (Qwen chat + VisionAgent)
ui/templates/           # Jinja2 HTML templates
secrets/                # OAuth keys — KHÔNG đẩy lên GitHub (đã gitignore)
DOCUMENTS/              # Báo cáo và slide thuyết trình — đọc ở đây trước
```

---

## Quy tắc bắt buộc cho cả nhóm

> Không tuân thủ = bị reject khi merge.

### 1. Chiến lược nhánh (Branch Strategy)

| Nhánh | Mục đích | Ai dùng |
|-------|----------|---------|
| `main` | Production — chỉ merge sau test nặng | Lead |
| `dev` | Canary — tích hợp & test trước khi lên main | Lead |
| `demo` | Bản demo jury — **đóng băng 48h trước khi thuyết trình** | Lead |
| `backend` | Phát triển backend (app.py, services, routes) | Backend dev |
| `frontend` | Phát triển frontend (templates, CSS, JS) | Frontend dev |
| `mixed` | Tích hợp frontend + backend trước khi lên dev | Cả nhóm |

**Luồng merge:**

```
backend ──┐
           ├──> mixed ──> dev ──> main
frontend ──┘                └──> demo (fork từ dev, đóng băng trước jury)
```

**Tuyệt đối không code trực tiếp trên `main` hoặc `demo`.**

---

### 2. Quy tắc Commit (Conventional Commits)

Format bắt buộc:

```
<type>(<scope>): <mô tả ngắn>
```

| Type | Khi nào dùng |
|------|-------------|
| `feat` | Tính năng mới |
| `fix` | Sửa lỗi |
| `docs` | Sửa tài liệu |
| `refactor` | Tái cấu trúc code (không thêm tính năng, không sửa lỗi) |
| `test` | Thêm hoặc sửa test |
| `chore` | Việc vặt (gitignore, config, dependencies) |
| `style` | Format code, không thay đổi logic |

Ví dụ đúng:

```
feat(auth): thêm đăng nhập Google OAuth
fix(ocr): xử lý ảnh hóa đơn bị xoay
docs(readme): cập nhật hướng dẫn khởi động
```

---

### 3. Quy tắc đặt tên (Naming Convention)

**Python (Backend):**

- Biến & hàm: `snake_case` → `process_invoice()`, `user_data`
- Class: `PascalCase` → `AuthManager`, `InvoiceService`
- Hằng số: `UPPER_CASE` → `MAX_UPLOAD_SIZE`, `PROJECT_ROOT`
- File: `snake_case` → `invoice_service.py`, `ocr_routes.py`

**HTML/CSS/JS (Frontend):**

- File component: `PascalCase` hoặc `kebab-case`
- Biến JS: `camelCase`
- CSS class: `kebab-case`

---

### 4. Chuẩn API Response

Mọi API endpoint phải trả về JSON theo cấu trúc:

```json
{
  "success": true,
  "data": { ... },
  "message": "Thông báo"
}
```

HTTP Status Code:

- `200/201` — Thành công
- `400` — Lỗi dữ liệu đầu vào
- `401` — Chưa đăng nhập
- `403` — Không có quyền
- `500` — Lỗi server

---

### 5. Quy tắc bảo mật

- **KHÔNG bao giờ** hardcode secret key, password, API key vào code
- Tất cả secrets để trong `secrets/` (đã gitignore) hoặc biến môi trường `.env`
- File `.env` **KHÔNG** được đẩy lên GitHub
- `.claude/` và `.planning/` đã bị gitignore — chỉ tồn tại local để làm việc

---

### 6. Quy tắc Code sạch

- Hàm không quá **50 dòng** — nếu dài hơn, tách ra service riêng
- Không để `console.log` hay `print()` debug trong production code
- Không commit code đã comment-out — xóa hẳn hoặc ghi vào TODO.md
- Import theo thứ tự: stdlib → third-party → local

---

### 7. Quy trình làm việc hàng ngày

```bash
# Buổi sáng — lấy code mới nhất
git checkout backend          # (hoặc frontend)
git pull origin backend

# Làm việc và commit thường xuyên
git add <files>
git commit -m "feat(wallet): thêm lịch sử giao dịch"

# Khi xong tính năng — merge lên mixed để tích hợp
git checkout mixed
git pull origin mixed
git merge backend
git push origin mixed
```

---

### 8. Công cụ bắt buộc cài đặt

| Công cụ | Dùng cho | Cài đặt |
|---------|----------|---------|
| **Black** | Format Python tự động | `pip install black` |
| **Prettier** | Format HTML/CSS/JS | VS Code extension |
| **Python** 3.x | Runtime | python.org |

```bash
# Chạy trước khi commit Python code
black app.py core/ dl_service/
```

---

## Liên hệ & Issues

Dùng GitHub Forums/ Issues để báo lỗi hoặc đề xuất tính năng. Tag đúng người liên quan.

---

*Dự án: ANSER*
