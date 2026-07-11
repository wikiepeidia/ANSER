# ANSER Sprint 1 — chạy toàn bộ: up stack → setup → test matrix → evidence → screenshot.
# Dùng: powershell -File tests\smoke\run_all.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Đã tạo .env từ .env.example — điền secret nếu cần" }

Write-Host "== 1. docker compose up -d (build nếu cần) =="
docker compose up -d --build

Write-Host "== 2. Chờ n8n sẵn sàng =="
do { Start-Sleep 2 } until ((try { (Invoke-WebRequest "http://localhost:5678/healthz" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { $false }))
Start-Sleep 4

Write-Host "== 3. Setup owner + import + activate =="
python tests\smoke\setup.py

Write-Host "== 4. Chạy test matrix + sinh evidence =="
python tests\smoke\gen_evidence.py
$code = $LASTEXITCODE

Write-Host "== 5. Chụp ảnh report =="
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (Test-Path $edge) {
  & $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1400,3100 `
    --screenshot="$root\tests\evidence\report.png" "file:///$root/tests/evidence/report.html" 2>$null
}
Write-Host "Xong. Xem tests\evidence\report.html + report.png (exit=$code)"
exit $code
