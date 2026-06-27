@echo off
REM ============================================================
REM  AaaS portable runner - boots all 4 services and opens the
REM  demo page. Run SETUP-FRIEND.bat once before using this.
REM ============================================================

setlocal
set ROOT=%~dp0
set VENV=%ROOT%.venv-portable

if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo [X] .venv-portable not found. Run SETUP-FRIEND.bat first.
  echo.
  pause
  exit /b 1
)

set PY="%VENV%\Scripts\python.exe"

echo Booting AaaS services...
echo   TTS       -^> http://127.0.0.1:8001
echo   STT       -^> http://127.0.0.1:8002
echo   Translate -^> http://127.0.0.1:8003
echo   Gateway   -^> http://127.0.0.1:8000
echo.

start "AaaS TTS"       cmd /k "cd /d %ROOT%services\tts       && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
start "AaaS STT"       cmd /k "cd /d %ROOT%services\stt       && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
start "AaaS Translate" cmd /k "cd /d %ROOT%services\translate && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8003"
start "AaaS Gateway"   cmd /k "cd /d %ROOT%services\gateway   && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting 15 seconds for services to come up...
timeout /t 15 /nobreak > nul

echo Opening demo landing page...
start "" "http://127.0.0.1:8000/demo/"

endlocal
exit /b 0
