@echo off
title Local Command Bot — Multi-Cloud AI Document Orchestrator
cd /d "%~dp0"

echo ========================================================
echo   LOCAL COMMAND BOT — MULTI-CLOUD AI ORCHESTRATOR
echo ========================================================
echo.

IF NOT EXIST "..\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at ..\.venv
    echo Vui long chay cai dat truoc.
    pause
    exit /b 1
)

echo Dang khoi chay ung dung Desktop...
"..\.venv\Scripts\python.exe" -m app.main

pause
