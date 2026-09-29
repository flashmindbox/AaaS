@echo off
title SUBARNAREKHA - Stop AaaS Demo
echo.
echo   Stopping the AaaS demo services...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,8001,8002,8003 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
taskkill /FI "WINDOWTITLE eq AaaS*" /T /F >nul 2>&1
set "HERE=%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like ($env:HERE + '*') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'uvicorn app.main:app') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo   Done. All services stopped.
echo.
timeout /t 3 >nul
