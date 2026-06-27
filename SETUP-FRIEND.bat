@echo off
REM ============================================================
REM  AaaS portable setup - one-shot installer for a fresh laptop.
REM  Usually you do NOT run this directly - just double-click
REM  START-HERE.bat, which calls this once and then launches.
REM  Only Python is required. Node/pnpm are optional (the demo
REM  runs without them), so this never aborts just because Node
REM  or some optional model is missing.
REM ============================================================
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv-portable"
set "PIP_CACHE=%ROOT%.pip-cache"

echo.
echo ============================================================
echo  AaaS Accessibility Platform - Portable Setup
echo ============================================================
echo.

REM --- 1. Check prerequisites --------------------------------------------
echo [1/6] Checking prerequisites...

where python >nul 2>&1
if errorlevel 1 (
  echo   [X] Python is not on PATH. Install Python 3.12 or 3.13 from
  echo       https://www.python.org/downloads/ and tick "Add to PATH".
  goto :fail
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 (
  echo   [X] Python 3.12 or newer is required. Current version:
  python --version
  goto :fail
)
echo   [OK] Python found:
python --version

set "NODE_OK=1"
where node >nul 2>&1
if errorlevel 1 set "NODE_OK=0"
if "!NODE_OK!"=="1" (
  echo   [OK] Node found:
  node --version
) else (
  echo   [!] Node not found - skipping Node steps. The demo runs fine without it.
)

if "!NODE_OK!"=="1" (
  where pnpm >nul 2>&1
  if errorlevel 1 (
    echo   [!] pnpm not found - enabling it via corepack...
    call corepack enable >nul 2>&1
    call corepack prepare pnpm@10.24.0 --activate >nul 2>&1
  )
)

REM --- 2. Create shared Python venv --------------------------------------
echo.
echo [2/6] Creating shared Python venv at .venv-portable ...
if exist "%VENV%" (
  echo   [OK] Venv already exists - reusing.
) else (
  python -m venv "%VENV%"
  if errorlevel 1 goto :fail
)
call "%VENV%\Scripts\activate.bat"

python -m pip install --upgrade pip --cache-dir "%PIP_CACHE%"
if errorlevel 1 goto :fail

REM --- 3. Install Python service deps (shared venv) ----------------------
echo.
echo [3/6] Installing Python dependencies (this downloads ~2 GB once).
echo        Go make a coffee - first run takes 5-10 minutes.

python -m pip install --cache-dir "%PIP_CACHE%" -e "%ROOT%services\gateway"
if errorlevel 1 goto :fail

python -m pip install --cache-dir "%PIP_CACHE%" -e "%ROOT%services\tts"
if errorlevel 1 goto :fail

python -m pip install --cache-dir "%PIP_CACHE%" -e "%ROOT%services\stt[indic]"
if errorlevel 1 goto :fail

python -m pip install --cache-dir "%PIP_CACHE%" -e "%ROOT%services\translate[indic]"
if errorlevel 1 goto :fail

REM --- 4. Seed .env files -------------------------------------------------
echo.
echo [4/6] Seeding .env files from examples...
for %%S in (gateway tts stt translate) do (
  if not exist "%ROOT%services\%%S\.env" (
    copy /y "%ROOT%services\%%S\.env.example" "%ROOT%services\%%S\.env" >nul
    echo   [OK] services\%%S\.env created.
  ) else (
    echo   [--] services\%%S\.env already exists - kept.
  )
)

REM --- 5. Node / frontend deps (OPTIONAL - not needed to run) -------------
echo.
echo [5/6] Installing Node frontend deps (optional)...
if "!NODE_OK!"=="1" (
  pushd "%ROOT%"
  call pnpm install
  popd
  echo   [OK] Node step finished ^(any warnings above are harmless^).
) else (
  echo   [--] Skipped - Node not installed. The demo does not need it.
)

REM --- 6. Verify models (non-fatal - mock fallback covers gaps) ----------
echo.
echo [6/6] Verifying AI models...
"%VENV%\Scripts\python.exe" "%ROOT%scripts\ensure_ready.py"
if errorlevel 1 (
  echo.
  echo   [!] Some models could not be verified. The demo will still run,
  echo       using safe mock fallbacks where a model is missing. Run
  echo       DIAGNOSE.bat to see which, then ENSURE-READY.bat to retry.
)

REM --- Done --------------------------------------------------------------
echo.
echo ============================================================
echo  SETUP COMPLETE
echo ============================================================
echo.
echo  The demo will start next. In future, just double-click
echo  START-HERE.bat - it skips setup and launches straight away.
echo.
exit /b 0

:fail
echo.
echo ============================================================
echo  SETUP FAILED - scroll up for the error.
echo  Run DIAGNOSE.bat and send the report for help.
echo ============================================================
pause
exit /b 1
