# Setup cho teammate

## Yêu cầu
- Docker Desktop đã cài và đang chạy
- Python 3.10+ (để chạy scripts)

## Bước 1: Chạy containers
```powershell
cd docker_project
docker compose up -d
```
Lần đầu sẽ tải images (~2-3 phút). Sau đó 4 container sẽ chạy:
- **n8n** (port 5678) — workflow automation
- **n8n-proxy** (port 5679) — proxy cho iframe
- **rag-service** (port 8001) — API microservice
- **chromadb** (port 8000) — vector database

## Bước 2: Tạo bảng database
```powershell
pip install psycopg2-binary alembic
python -m alembic upgrade head
```

## Bước 3: Import workflows vào n8n
```powershell
pip install requests
python scripts/import_workflows.py
```

## Bước 4: Test
```powershell
python scripts/pos_simulator.py invoice
```
Kết quả mong đợi: `HTTP 201` + Discord notification

## Truy cập
- n8n: http://localhost:5678
- n8n (qua ANSER): trang "n8n Workflows" trong sidebar
- RAG API: http://localhost:8001/docs

## Tài khoản n8n
Khi truy cập qua ANSER, proxy tự đăng nhập.
Nếu truy cập trực tiếp localhost:5678, tài khoản được tạo tự động lần đầu — xem file `.n8n_creds.json` trong thư mục ANSER.
