# PowerShell launcher for Local Command Bot
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonExe = Join-Path (Split-Path -Parent $ScriptDir) ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[LỖI] Không tìm thấy môi trường Python ảo tại: $PythonExe" -ForegroundColor Red
    Write-Host "Vui lòng cài đặt môi trường bằng uv hoặc python venv trước." -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  LOCAL COMMAND BOT — MULTI-CLOUD AI ORCHESTRATOR" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Đang khởi chạy giao diện Desktop (PySide6)..." -ForegroundColor Green

& $PythonExe -m app.main
