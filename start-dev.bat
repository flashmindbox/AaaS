@echo off
REM Boot all four services in separate windows, then open the Jajpur demo.
REM Dev-mode launcher - assumes Python 3.12+ and the service venvs
REM are already installed (see services/*/README.md).
REM
REM For the portable, zero-install judge-laptop version, run the
REM orchestrator once on the dev machine:
REM
REM     python scripts\build_bundle.py
REM
REM which produces dist\AaaS-Demo\. That folder (not this script) is
REM what ships on the USB stick. See docs\bundle-build.md.
REM
REM TTS backend: Meta MMS-TTS (facebook/mms-tts-ory/hin/eng). Three VITS
REM checkpoints, ~150 MB each, loaded on demand. See services\tts\README.md.

setlocal
set ROOT=%~dp0

REM All model weights live under services\*\models, so never touch the
REM network at load time - a flaky venue Wi-Fi would otherwise stall
REM startup on Hugging Face lookups. Unset these to download new models.
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set PYTHONIOENCODING=utf-8

REM Resolve the interpreter per service: the service's own .venv first,
REM then the portable env from SETUP-FRIEND.bat, then bare `python`.
call :resolve_py PY_TTS       "%ROOT%services\tts"
call :resolve_py PY_STT       "%ROOT%services\stt"
call :resolve_py PY_TRANSLATE "%ROOT%services\translate"
call :resolve_py PY_GATEWAY   "%ROOT%services\gateway"

start "AaaS TTS"       cmd /k "cd /d %ROOT%services\tts       && "%PY_TTS%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
start "AaaS STT"       cmd /k "cd /d %ROOT%services\stt       && "%PY_STT%" -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
start "AaaS Translate" cmd /k "cd /d %ROOT%services\translate && "%PY_TRANSLATE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8003"
start "AaaS Gateway"   cmd /k "cd /d %ROOT%services\gateway   && "%PY_GATEWAY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for services...
timeout /t 10 /nobreak > nul

echo Opening demo landing page...
start "" "http://127.0.0.1:8000/demo/"

endlocal
exit /b 0

:resolve_py
if exist "%~2\.venv\Scripts\python.exe" (
  set "%~1=%~2\.venv\Scripts\python.exe"
) else if exist "%ROOT%.venv-portable\Scripts\python.exe" (
  set "%~1=%ROOT%.venv-portable\Scripts\python.exe"
) else (
  set "%~1=python"
)
goto :eof
