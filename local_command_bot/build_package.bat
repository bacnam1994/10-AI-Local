@echo off
title Build Windows Package — Local Command Bot
cd /d "%~dp0"

echo Dang chay dong goi PyInstaller...
"..\.venv\Scripts\python.exe" build_package.py

echo.
pause
