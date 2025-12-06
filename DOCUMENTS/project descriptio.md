# 🧠 Group Project: RPAaaS — Workflow Automation for Retail Industry

## ⚡ TL;DR – Nói nhanh gọn

- **Vai trò:** Chủ Web → Manager → User, truyền quyền theo tầng.  
- **Chuỗi giá trị:** Nguồn dữ liệu (KH/SP/NP/XP + Webhook/API) → AI Agent & Template xử lý → Workspace/Bot + Dashboard xuất kết quả.  
- **Admin:** Gán quyền, quản lý workspace/bot/model, đính dataset và giới hạn tài nguyên.  
- **Một câu:** *"Hệ thống gồm: Người quản lý → Dữ liệu → AI Agent → Workspace → Dashboard, kèm API & Webhook để lấy dữ liệu tự động."*

---

## 🔹 TÓM TẮT HỆ THỐNG (BẢN ĐƠN GIẢN NHẤT)

### 1. Vai trò trong hệ thống

- **Chủ Web (Admin)** — quản lý cao nhất, thêm/xóa Manager, đặt giới hạn bot/model.
- **Manager** — nhận quyền từ Admin, quản tài nguyên, user, báo cáo, cấp/thu hồi permission.
- **User** — sử dụng hệ thống: tạo bot/agent, thao tác workspace, hỏi đáp dữ liệu.

### 2. Hệ thống chính gồm 3 phần

**(A) Dữ liệu đầu vào**  

- Danh mục chuẩn: KH (Khách hàng), SP (Sản phẩm), NP (Nhập), XP (Xuất), …  
- Nạp thêm bằng **Webhook** (nhập URL nhận dữ liệu tự động) hoặc **API Maker** (kết nối API ngoài).  
- File nội bộ (CSV/Excel) hoặc dữ liệu thủ công qua màn CRUD.

**(B) Xử lý**  

- AI Agent lấy dữ liệu đã gắn để tạo câu trả lời.  
- Có **Template** dựng bot nhanh + builder kéo thả để chỉnh logic.  
- Người dùng hỏi trong **chat box**, hệ thống phản hồi realtime, hiển thị lịch sử.

**(C) Đầu ra**  

- **Workspace**: chứa bot/agent, trạng thái chạy, nhật ký.  
- **Dashboard**: báo cáo tổng hợp, KPI nhập/xuất/bot.  
- Bot có thể phản hồi trực tiếp hoặc gọi Webhook/API trả dữ liệu đi nơi khác.

### 3. Admin / Quản trị hệ thống

- Quản lý user & workspace, phân bổ quota bot/sub-bot.  
- Chọn model AI, version, nhiệt độ.  
- Gắn dataset (KH/SP/NP/XP hoặc file ngoài) cho từng bot.  
- Kiểm soát API/Webhook đã cấp quyền và nhật ký hoạt động.

---

## 🧭 Flow Overview

```text
Chủ Web → Manager → User ───────────────┐
                                        ↓
           [INPUT] Datasets / Webhook / API Maker
                                        ↓
                        AI Agent + Templates + Builder
                                        ↓
           Workspace (Bot runtime) + Dashboard (Reports)
                                        ↓
                    API / Webhook / Chat Output Layer
```

---

## 📦 Current Implementation Status (Nov 2025)

| Domain | Trạng thái | Đã có | Còn thiếu |
| --- | --- | --- | --- |
| **Authentication & Roles** | ✅ Live | Flask auth, login/signup, role-based views, Manager permission UI (`/manager/permissions`) | MFA, audit log, invitation flow |
| **Data Modules (KH/SP/NP/XP)** | ⚙️ Backend ready | REST APIs + DB schema (`app.py`, `core/database.py`) | Final UI pages (customers/products/import/export templates noted TODO) |
| **Workspace & Builder** | ✅ UI v1 | Drag-drop builder (`workspace_builder.html`, `static/builder.css`), light/dark theme, property panel | Persist node graph, execution engine, collaboration |
| **Scenarios / Automation** | ⚙️ Basic | Scenario list page, theme sync, placeholder CRUD API | Scheduler, webhook triggers, runtime logs |
| **AI Layer** | 💤 Not started | Slots reserved in config for future model selection | Model hosting, prompt orchestration, data-grounding pipeline |
| **Integrations (API/Webhook)** | 💤 Not started | Concept + placeholders in README | Actual connector marketplace, OAuth handshake, webhook listener service |
| **Dashboard & Reporting** | 💤 Not started | Basic stats endpoint (`/api/admin/stats`) | Visual reports, KPI cards, export CSV/PDF |

> **Database:** SQLite via `create_database.py`/`migrate_database.py` today; migration path to MongoDB or Postgres still open.

---

## 🛠️ Tech Stack Snapshot

- **Backend:** Flask, SQLAlchemy-style helpers in `core/database.py`, Flask-Login for sessions.
- **Frontend:** Server-rendered Jinja templates in `templates/` + enhanced UI in `ui/templates/`, CSS/JS under `static/` (builder/scenario/workspace themes, toast system, drag-drop logic in `script.js`).
- **Tooling:** Python 3.x, simple scripts (`create_database.py`, `migrate_database.py`) to bootstrap data, MIT License.

---

## 📈 Roadmap & Next Steps

1. **Finish CRUD UIs** for Customers/Products/Imports/Exports and hook to existing APIs.  
2. **Persist Builder Graphs** (DB schema for nodes/edges, execution timeline).  
3. **Automation Runtime** — scheduler + webhook listener + retry strategy.  
4. **AI Assistant MVP** — pick model, expose suggestion sidebar, add dataset-grounded answers.  
5. **Integration Hub** — connectors gallery, OAuth/API-key vault, monitoring dashboard.  
6. **Analytics Dashboard** — charts for inventory, workflow success, bot usage, exportable reports.

---

## 📚 References & Inspiration

- [Make.com](https://www.make.com) · [Zapier](https://www.zapier.com) · [n8n](https://n8n.io)  
- [Wikipedia: Business Process Automation](https://en.wikipedia.org/wiki/Business_process_automation)

---

> ✨ *“Workflow Automation is creativity — we provide the canvas, users create the masterpiece.”*
