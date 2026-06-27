@echo off
REM =====================================================================
REM   AaaS Accessibility Demo - judge-laptop launcher (Team SUBARNAREKHA)
REM
REM   Sequence:
REM     1. Pick free ports (8000/8001/8002/8003 or nearby alternates)
REM     2. Start TTS       - Odia speech synthesis (Meta MMS)
REM     3. Start STT       - Speech-to-text (mock by default)
REM     4. Start Translate - Indic <-> English (mock by default)
REM     5. Start Gateway   - proxies to the three backends + static UI
REM     6. Poll /healthz and /readyz on all four services
REM     7. Prewarm the TTS models (or/hi/en) so the first judge click is instant
REM     8. Open Edge/Chrome at the Jajpur collectorate demo page
REM
REM   Press any key in this window to stop all services cleanly.
REM   Closing the window directly will leave the minimised service
REM   windows running - close those too, or run tools\stop.bat.
REM =====================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo.
echo ==========================================================
echo   AaaS Accessibility Demo
echo   Team SUBARNAREKHA  -  Smart Odisha Hackathon 25
echo ==========================================================
echo.

REM -- 1. Port check --------------------------------------------------
set GATEWAY_PORT=
set TTS_PORT=
set STT_PORT=
set TRANSLATE_PORT=
set PORT_ERR=
for /f "usebackq tokens=1,2 delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File tools\portcheck.ps1 8000 8001 8002 8003`) do (
  if "%%A"=="GATEWAY_PORT"   set GATEWAY_PORT=%%B
  if "%%A"=="TTS_PORT"       set TTS_PORT=%%B
  if "%%A"=="STT_PORT"       set STT_PORT=%%B
  if "%%A"=="TRANSLATE_PORT" set TRANSLATE_PORT=%%B
  if "%%A"=="ERROR"          set PORT_ERR=%%B
)
if defined PORT_ERR (
  echo ERROR: %PORT_ERR%
  echo.
  pause
  exit /b 1
)
if not defined GATEWAY_PORT   set GATEWAY_PORT=8000
if not defined TTS_PORT       set TTS_PORT=8001
if not defined STT_PORT       set STT_PORT=8002
if not defined TRANSLATE_PORT set TRANSLATE_PORT=8003

echo Ports:  gateway=!GATEWAY_PORT!  tts=!TTS_PORT!  stt=!STT_PORT!  translate=!TRANSLATE_PORT!
echo.

REM -- 2. Launch TTS --------------------------------------------------
echo Starting TTS...
start "AaaS TTS" /MIN cmd /c "set TTS_PORT=!TTS_PORT! && services\aaas-tts\aaas-tts.exe > logs\tts.log 2>&1"

REM -- 3. Launch STT --------------------------------------------------
echo Starting STT...
start "AaaS STT" /MIN cmd /c "set STT_PORT=!STT_PORT! && services\aaas-stt\aaas-stt.exe > logs\stt.log 2>&1"

REM -- 4. Launch Translate --------------------------------------------
echo Starting Translate...
start "AaaS Translate" /MIN cmd /c "set TRANSLATE_PORT=!TRANSLATE_PORT! && services\aaas-translate\aaas-translate.exe > logs\translate.log 2>&1"

REM -- 5. Launch Gateway (tell it where the backends are) -------------
echo Starting Gateway...
start "AaaS Gateway" /MIN cmd /c "set GATEWAY_PORT=!GATEWAY_PORT! && set UPSTREAM_TTS_URL=http://127.0.0.1:!TTS_PORT! && set UPSTREAM_STT_URL=http://127.0.0.1:!STT_PORT! && set UPSTREAM_TRANSLATE_URL=http://127.0.0.1:!TRANSLATE_PORT! && services\aaas-gateway\aaas-gateway.exe > logs\gateway.log 2>&1"

REM -- 6. Wait until all four are ready -------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File tools\wait-ready.ps1 -GatewayPort !GATEWAY_PORT! -TtsPort !TTS_PORT! -SttPort !STT_PORT! -TranslatePort !TRANSLATE_PORT! -TimeoutSec 120
if errorlevel 1 (
  echo.
  echo ERROR: services did not start in time.
  echo Look at logs\tts.log, logs\stt.log, logs\translate.log, logs\gateway.log.
  echo.
  pause
  goto :cleanup
)

REM -- 7. Prewarm the TTS models (or/hi/en) ---------------------------
echo Prewarming TTS models (or, hi, en)...
powershell -NoProfile -ExecutionPolicy Bypass -File tools\prewarm.ps1 -GatewayPort !GATEWAY_PORT!

REM -- 8. Open browser ------------------------------------------------
echo.
echo Opening demo in browser...
powershell -NoProfile -ExecutionPolicy Bypass -File tools\open-browser.ps1 -Url "http://127.0.0.1:!GATEWAY_PORT!/demo/jajpur-collectorate/"

echo.
echo ==========================================================
echo   Demo is LIVE
echo     Tenant pages : http://127.0.0.1:!GATEWAY_PORT!/demo/
echo     Exam module  : http://127.0.0.1:!GATEWAY_PORT!/exam/
echo     Admin panel  : http://127.0.0.1:!GATEWAY_PORT!/admin/
echo     API docs     : http://127.0.0.1:!GATEWAY_PORT!/docs
echo.
echo   Press any key in this window to stop the services.
echo   (Or leave the window open for the duration of the demo.)
echo ==========================================================
echo.
pause >nul

:cleanup
echo.
echo Stopping services...
taskkill /f /im aaas-tts.exe       >nul 2>&1
taskkill /f /im aaas-stt.exe       >nul 2>&1
taskkill /f /im aaas-translate.exe >nul 2>&1
taskkill /f /im aaas-gateway.exe   >nul 2>&1
echo Done.
endlocal
exit /b 0
