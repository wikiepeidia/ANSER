# ANSER rag_service 0.3.0 — deps pin, không pip install lúc runtime (OPS-1)
FROM python:3.11-slim

WORKDIR /app

# Cài deps ở layer riêng để cache; build-essential cho psycopg2 nếu cần
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8001

# Healthcheck thật (OPS-3) — compose depends_on service_healthy dựa vào đây
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=3).status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
