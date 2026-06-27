@echo off
REM Double-click launcher for the portable AaaS TTS bundle.
REM Assumes this .bat sits next to aaas-tts.exe inside dist/aaas-tts/.

setlocal
cd /d "%~dp0"
echo Starting AaaS TTS on http://127.0.0.1:8001
echo (close this window to stop the service)
echo.
aaas-tts.exe
endlocal
