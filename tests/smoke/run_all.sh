#!/usr/bin/env bash
# ANSER Sprint 1 — chạy toàn bộ: up → setup → test matrix → evidence.
# Dùng: bash tests/smoke/run_all.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

[ -f .env ] || { cp .env.example .env; echo "Đã tạo .env từ .env.example"; }

echo "== 1. docker compose up -d --build =="
docker compose up -d --build

echo "== 2. Chờ n8n sẵn sàng =="
until curl -sf -o /dev/null --max-time 3 http://localhost:5678/healthz; do sleep 2; done
sleep 4

echo "== 3. Setup owner + import + activate =="
python tests/smoke/setup.py

echo "== 4. Test matrix + evidence =="
python tests/smoke/gen_evidence.py
code=$?

echo "Xong. Xem tests/evidence/report.html (exit=$code)"
exit $code
