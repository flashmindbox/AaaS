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

start "AaaS TTS"       cmd /k "cd /d %ROOT%services\tts       && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
start "AaaS STT"       cmd /k "cd /d %ROOT%services\stt       && python -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
start "AaaS Translate" cmd /k "cd /d %ROOT%services\translate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8003"
start "AaaS Gateway"   cmd /k "cd /d %ROOT%services\gateway   && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for services...
timeout /t 10 /nobreak > nul

echo Opening demo landing page...
start "" "http://127.0.0.1:8000/demo/"

endlocal
