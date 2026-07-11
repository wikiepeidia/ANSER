# Setup — ANSER automation (Docker + n8n)

## Yêu cầu
- Docker Desktop đang chạy
- Python 3.10+ (chạy scripts/tests)

## Chạy nhanh toàn bộ (1 lệnh)
```powershell
copy .env.example .env      # rồi điền N8N_EMAIL/N8N_PASSWORD, ANSER_WEBHOOK_TOKEN...
powershell -File tests\smoke\run_all.ps1
```
Lệnh trên: `docker compose up -d --build` → chờ n8n → `setup.py` (owner + import + activate)
→ `gen_evidence.py` (test matrix) → chụp `tests/evidence/report.png`.

## Chạy từng bước
```powershell
docker compose up -d --build     # build image local (rag 0.3.0, mock-brain, discord-mock) + pull n8n/chroma/pg
```
Sau khi lên, có 7 container (tất cả bind 127.0.0.1):
- **anser-n8n** (5678) — workflow engine (n8n 2.29.10)
- **anser-nginx** (5679) — reverse proxy iframe
- **anser-rag** (8001) — DB gateway FastAPI (idempotency, low-stock, import, ...)
- **anser-test-pg** (15432) — Postgres 16 test (init.sql tự nạp schema + seed)
- **anser-chroma** (8000) — vector DB
- **anser-mock-brain** (8100) — Brain giả lập (OCR/validate/chat) cho dev
- **anser-discord-mock** (9099) — nhận Discord webhook khi test

### Owner + import + activate
Mở http://localhost:5678 tạo owner (email+mật khẩu), điền vào `.env`, rồi:
```powershell
python tests\smoke\setup.py          # tạo owner (nếu chưa) + import 10 workflow + activate 5 retail
```

### Chạy test matrix + bằng chứng
```powershell
python tests\smoke\gen_evidence.py   # -> tests/evidence/report.html + report.png + transcript.txt
python tests\smoke\screenshot_n8n.py # (tuỳ chọn, cần playwright) -> ảnh n8n UI executions
```

## Cấu trúc
```
workflows/retail/    # 10 QT bán lẻ (POS, tồn kho, doanh số, CSKH, OCR nhập, forecast, KM, marketplace, công nợ, giá đối thủ)
workflows/manuf/     # 3 QT sản xuất (ingest mẻ PLC/tay, %thất thoát+%lãi, báo cáo ĐR) — pilot xưởng đồ uống
workflows/shared/    # notifier đa kênh, error handler, ingest chung, mẫu
rag_service/                        # FastAPI DB gateway (Dockerfile + requirements pin)
mock_services/{discord_mock,mock_brain}/
init.sql                            # schema + seed test
tests/{test_matrix.md, smoke/, evidence/}
docs/                               # 3 PDF automation + báo cáo + DEVIATIONS.md
```

## Bảo mật (Sprint 0 + 1)
- **Không commit `.env`** — mọi secret chỉ ở `.env` (đã gitignore).
- Webhook yêu cầu header `x-anser-token` = `ANSER_WEBHOOK_TOKEN` (trống = tắt, chỉ demo local).
- Cổng 5678/5679/8000/8001/8100/9099/15432 đều bind `127.0.0.1`.
- Xem sai khác so với PDF ở `docs/DEVIATIONS.md`.
