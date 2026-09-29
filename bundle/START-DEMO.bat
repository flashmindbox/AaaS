@echo off
title SUBARNAREKHA - AaaS Demo
REM ================================================================
REM  AaaS - Accessibility as a Service  |  Team SUBARNAREKHA
REM  Double-click this file to start the demo. Works fully offline.
REM ================================================================

cd /d "%~dp0system"
set "ROOT=%CD%"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set PYTHONIOENCODING=utf-8
set "KEY=aaas_live_33333333333333333333333333333333"
REM Key shipped in the AaaS Companion browser extension (non-operator tenant).
set "EXTENSION_API_KEY=aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18"

REM Use the Python and Tesseract shipped inside this folder, so the demo
REM runs on any Windows laptop without installing anything.
for %%S in (gateway tts stt translate) do call :venvcfg %%S
set "AAAS_TRANSLATE_TESSERACT_CMD=%ROOT%\tesseract\tesseract.exe"

echo.
echo   ==========================================================
echo     AaaS - Accessibility as a Service   ^|  Team SUBARNAREKHA
echo   ==========================================================
echo.

REM Already running? Just open the browser.
curl -s -f -m 2 http://127.0.0.1:8000/healthz >nul 2>&1
if not errorlevel 1 (
  echo   The demo is already running - opening the browser.
  goto :open
)

echo   [1/3] Starting the four AI services (minimised windows)...
start "AaaS TTS"       /min /D "%ROOT%\services\tts"       cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
start "AaaS STT"       /min /D "%ROOT%\services\stt"       cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
start "AaaS Translate" /min /D "%ROOT%\services\translate" cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
start "AaaS Gateway"   /min /D "%ROOT%\services\gateway"   cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo   [2/3] Loading AI models - this takes about 1 minute...
call :wait "Gateway  " http://127.0.0.1:8000/healthz || goto :failed
call :wait "Voice    " http://127.0.0.1:8001/readyz  || goto :failed
call :wait "Speech   " http://127.0.0.1:8002/readyz  || goto :failed
call :wait "Translate" http://127.0.0.1:8003/readyz  || goto :failed

echo   [3/3] Warming up the Odia voice...
curl -s -m 60 -o nul -H "X-API-Key: %KEY%" -H "Content-Type: application/json" --data-binary "@%ROOT%\warmup-tts.json" http://127.0.0.1:8000/tts/synthesise

:open
start "" "http://127.0.0.1:8000/demo/ssepd-odisha/"
start "" "http://127.0.0.1:8000/demo/bse-odisha/"
echo.
echo   ==========================================================
echo     DEMO IS READY.  Click the round blue button on the page.
echo.
echo     Keep this window open during the demo.
echo     To shut down afterwards: double-click STOP-DEMO.bat
echo   ==========================================================
echo.
pause >nul
exit /b 0

:wait
REM %1 = label, %2 = URL. Polls for up to ~3 minutes.
setlocal
set /a tries=0
<nul set /p "=        %~1 "
:wait_loop
curl -s -f -m 2 %2 >nul 2>&1
if not errorlevel 1 (
  echo ready
  endlocal & exit /b 0
)
set /a tries+=1
if %tries% geq 90 (
  echo NOT READY
  endlocal & exit /b 1
)
<nul set /p "=."
timeout /t 2 /nobreak >nul
goto :wait_loop

:failed
echo.
echo   ----------------------------------------------------------
echo   A service did not start. Please:
echo     1. Double-click STOP-DEMO.bat
echo     2. Double-click START-DEMO.bat again
echo   If it still fails, open the "AaaS ..." window on the taskbar
echo   to see the error message.
echo   ----------------------------------------------------------
pause
exit /b 1

:venvcfg
REM %1 = service. Re-points its .venv at system\python wherever the folder lives.
> "%ROOT%\services\%1\.venv\pyvenv.cfg" echo home = %ROOT%\python
>> "%ROOT%\services\%1\.venv\pyvenv.cfg" echo include-system-site-packages = false
>> "%ROOT%\services\%1\.venv\pyvenv.cfg" echo version = 3.14.0
exit /b 0
