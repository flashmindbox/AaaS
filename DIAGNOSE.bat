@echo off
REM ============================================================
REM  AaaS - DIAGNOSE.bat
REM  Read-only health check for a fresh laptop. Run this if the
REM  setup or demo isn't working. It writes diagnose-report.txt
REM  next to itself - send that file to whoever is helping you.
REM  Place this file in the same folder as SETUP-FRIEND.bat.
REM ============================================================
setlocal enabledelayedexpansion
title AaaS Diagnostic
set "ROOT=%~dp0"
set "REPORT=%ROOT%diagnose-report.txt"
set "ISSUES=0"
type nul > "%REPORT%"

echo.
echo  Running AaaS diagnostic, please wait...
echo.

call :hdr "AaaS ACCESSIBILITY PLATFORM - DIAGNOSTIC REPORT"
call :say "Folder : %ROOT%"
call :say "Date   : %DATE% %TIME%"

REM --- 0. Install folder ----------------------------------------------------
call :sec "0. Install folder"
echo %ROOT%|find " " >nul
if errorlevel 1 (
  call :ok "Folder path has no spaces."
) else (
  call :warn "Folder path has spaces. Usually fine; if setup fails, unzip to C:\AaaS\ instead."
)

REM --- 1. Python ------------------------------------------------------------
call :sec "1. Python (required)"
where python >nul 2>&1
if errorlevel 1 (
  call :bad "Python is NOT on PATH. Install Python 3.12 or 3.13 from python.org and TICK 'Add Python to PATH'."
) else (
  set "PYVER="
  for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
  python -c "import sys; sys.exit(0 if sys.version_info>=(3,12) else 1)" >nul 2>&1
  if errorlevel 1 (
    call :bad "Found '!PYVER!' but version 3.12 or newer is required."
  ) else (
    call :ok "!PYVER! found and on PATH."
  )
)

REM --- 2. Node + pnpm -------------------------------------------------------
call :sec "2. Node.js and pnpm (optional - developer tooling only)"
where node >nul 2>&1
if errorlevel 1 (
  call :warn "Node.js not found - optional; the demo runs fine without it (SETUP-FRIEND skips the Node steps)."
) else (
  set "NODEVER="
  for /f "tokens=*" %%v in ('node --version 2^>^&1') do set "NODEVER=%%v"
  call :ok "Node !NODEVER! found."
)
where pnpm >nul 2>&1
if errorlevel 1 (
  call :warn "pnpm not found yet - SETUP-FRIEND.bat installs it automatically via corepack."
) else (
  set "PNPMVER="
  for /f "tokens=*" %%v in ('pnpm --version 2^>^&1') do set "PNPMVER=%%v"
  call :ok "pnpm !PNPMVER! found."
)

REM --- 3. Setup status -----------------------------------------------------
call :sec "3. Setup status (has SETUP-FRIEND.bat finished?)"
set "VPY=%ROOT%.venv-portable\Scripts\python.exe"
if not exist "%VPY%" (
  REM Dev checkouts use one .venv per service instead of .venv-portable.
  set "DEVVENVS=1"
  for %%S in (gateway tts stt translate) do (
    if not exist "%ROOT%services\%%S\.venv\Scripts\python.exe" set "DEVVENVS=0"
  )
  REM TTS venv has the full stack (fastapi + torch), so probe that one.
  if "!DEVVENVS!"=="1" set "VPY=%ROOT%services\tts\.venv\Scripts\python.exe"
)
if exist "%VPY%" (
  echo %VPY%|find ".venv-portable" >nul
  if errorlevel 1 (
    call :ok "Per-service dev venvs found - .venv-portable not needed on a dev machine."
  ) else (
    call :ok "Python environment .venv-portable exists."
  )
  "%VPY%" -c "import fastapi, uvicorn, structlog" >nul 2>&1
  if errorlevel 1 (
    call :bad "Core Python libraries are missing. Re-run SETUP-FRIEND.bat."
  ) else (
    call :ok "Core service libraries installed."
  )
  "%VPY%" -c "import torch, transformers" >nul 2>&1
  if errorlevel 1 (
    call :warn "AI libraries torch/transformers not found - voice and translation need them. Re-run SETUP-FRIEND.bat."
  ) else (
    call :ok "AI libraries torch + transformers installed."
  )
) else (
  call :bad "Setup not complete - .venv-portable is missing. Run SETUP-FRIEND.bat first."
)
if exist "%ROOT%node_modules\" (
  call :ok "Node modules installed."
) else (
  call :warn "node_modules missing - run SETUP-FRIEND.bat, which runs pnpm install."
)

REM --- 4. AI models --------------------------------------------------------
call :sec "4. AI models (bundled with the zip)"
call :model "TTS Odia"            "services\tts\models\models--facebook--mms-tts-ory\snapshots"
call :model "TTS Hindi"           "services\tts\models\models--facebook--mms-tts-hin\snapshots"
call :model "TTS English"         "services\tts\models\models--facebook--mms-tts-eng\snapshots"
call :model "Translation IndicTrans2 en-or" "services\translate\models\models--ai4bharat--indictrans2-en-indic-dist-200M\snapshots"
call :model "Translation IndicTrans2 or-en" "services\translate\models\models--ai4bharat--indictrans2-indic-en-dist-200M\snapshots"
call :model "STT Odia"            "services\stt\models\models--ai4bharat--indicwav2vec-odia\snapshots" opt

REM --- 5. Web widget -------------------------------------------------------
call :sec "5. Web widget and extension files"
if exist "%ROOT%apps\widget\dist\widget.js" (
  set "WSZ=0"
  for %%A in ("%ROOT%apps\widget\dist\widget.js") do set "WSZ=%%~zA"
  if !WSZ! GTR 100000 (
    call :ok "widget.js present, !WSZ! bytes."
  ) else (
    call :bad "widget.js is only !WSZ! bytes - looks corrupt. Re-extract the zip."
  )
) else (
  call :bad "widget.js missing - re-extract the zip."
)
if exist "%ROOT%apps\extension\manifest.json" (
  call :ok "Browser extension folder present."
) else (
  call :warn "Browser extension folder incomplete - re-extract the zip."
)

REM --- 6. Ports ------------------------------------------------------------
call :sec "6. Ports 8000-8003 (info)"
call :port 8000 Gateway
call :port 8001 TTS
call :port 8002 STT
call :port 8003 Translate

REM --- 7. Live services ----------------------------------------------------
call :sec "7. Services responding (only meaningful while RUN-DEMO is running)"
call :health 8000 Gateway
call :health 8001 TTS
call :health 8002 STT
call :health 8003 Translate

REM --- summary -------------------------------------------------------------
call :hdr "SUMMARY"
if "!ISSUES!"=="0" (
  call :say "No blocking problems found. If the demo still fails, run RUN-DEMO.bat and send the red text from the service windows."
) else (
  call :say "!ISSUES! blocking problem(s) marked [X] above. Each line says how to fix it. Fix those, then run this again."
)
call :nl
call :say "This report was saved to:"
call :say "  %REPORT%"
call :say "Send that file (or a screenshot of this window) to whoever is helping you."

echo.
echo  ----------------------------------------------------------------
echo   Done. The report is saved as diagnose-report.txt in this folder.
echo  ----------------------------------------------------------------
echo.
pause
exit /b 0

REM ====================== helper subroutines ==============================
:hdr
echo.
>>"%REPORT%" echo.
echo ==================================================================
>>"%REPORT%" echo ==================================================================
echo  %~1
>>"%REPORT%" echo  %~1
echo ==================================================================
>>"%REPORT%" echo ==================================================================
goto :eof

:sec
echo.
>>"%REPORT%" echo.
echo --- %~1 ---
>>"%REPORT%" echo --- %~1 ---
goto :eof

:say
echo %~1
>>"%REPORT%" echo %~1
goto :eof

:nl
echo.
>>"%REPORT%" echo.
goto :eof

:ok
echo   [OK] %~1
>>"%REPORT%" echo   [OK] %~1
goto :eof

:warn
echo   [WARN] %~1
>>"%REPORT%" echo   [WARN] %~1
goto :eof

:bad
set /a ISSUES+=1
echo   [X] %~1
>>"%REPORT%" echo   [X] %~1
goto :eof

:model
if exist "%ROOT%%~2\" (
  call :ok "%~1 model present."
) else (
  if "%~3"=="opt" (
    call :warn "%~1 model missing - optional; speech-to-text will use mock mode."
  ) else (
    call :bad "%~1 model MISSING - run ENSURE-READY.bat to download it."
  )
)
goto :eof

:port
netstat -ano -p TCP 2>nul | findstr "LISTENING" | findstr ":%~1 " >nul 2>&1
if errorlevel 1 (
  call :say "   [i] Port %~1 %~2: free"
) else (
  call :say "   [i] Port %~1 %~2: in use"
)
goto :eof

:health
set "HBODY="
for /f "delims=" %%b in ('curl -s -f --max-time 2 "http://127.0.0.1:%~1/healthz" 2^>nul') do set "HBODY=%%b"
if not defined HBODY (
  call :say "   [--] %~2 on port %~1: not responding - normal if RUN-DEMO is not running."
) else (
  echo   [OK] %~2 on port %~1 is UP: !HBODY!
  >>"%REPORT%" echo   [OK] %~2 on port %~1 is UP: !HBODY!
  echo !HBODY! | findstr /i "mock" >nul 2>&1
  if not errorlevel 1 (
    call :warn "%~2 is running in MOCK mode - responses are canned. Run ENSURE-READY.bat to enable the real engine."
  )
)
goto :eof
