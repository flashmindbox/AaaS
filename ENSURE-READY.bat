@echo off
REM ============================================================
REM  AaaS readiness check + auto-heal.
REM  Run this any time models seem incomplete or after setting
REM  HF_TOKEN for real Odia STT. Idempotent — safe to re-run.
REM ============================================================

setlocal
set ROOT=%~dp0
set VENV=%ROOT%.venv-portable

if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo [X] .venv-portable not found. Run SETUP-FRIEND.bat first.
  echo     The portable venv is where huggingface_hub lives —
  echo     auto-heal can't run without it.
  echo.
  pause
  exit /b 1
)

call "%VENV%\Scripts\activate.bat"
"%VENV%\Scripts\python.exe" "%ROOT%scripts\ensure_ready.py"
set RC=%errorlevel%

echo.
if "%RC%"=="0" (
  echo   Done. You can now run RUN-DEMO.bat.
) else (
  echo   One or more checks failed. Scroll up for details.
)
echo.
pause
exit /b %RC%
