@echo off
REM ============================================================
REM  AaaS - START-HERE.bat   *** DOUBLE-CLICK THIS ONE ***
REM  One click does everything:
REM    - first time: installs (5-10 min, needs internet once)
REM    - every time after: just launches the demo
REM  Keep this file in the folder that also contains the
REM  "services" and "apps" folders.
REM ============================================================
setlocal
set "ROOT=%~dp0"
title AaaS - Start Here

echo.
echo  ============================================================
echo   AaaS Accessibility Platform
echo  ============================================================
echo.

REM --- Are we in the real project folder? -------------------------------
REM Check for pyproject.toml (a full install has it; the update pack's
REM _update folder does NOT) so this never runs from inside _update.
if not exist "%ROOT%services\gateway\pyproject.toml" (
  echo  [X] This is not the project folder.
  echo.
  echo      START-HERE.bat must sit in the main AaaS-Portable folder -
  echo      the one that contains the "services" and "apps" folders.
  echo      Do NOT run it from inside an "_update" folder.
  echo.
  pause
  exit /b 1
)

REM --- First-time install if needed -------------------------------------
if exist "%ROOT%.venv-portable\Scripts\python.exe" (
  echo  Already set up. Launching the demo...
  echo.
) else (
  echo  First-time setup. This takes 5-10 minutes and needs internet
  echo  once to download the software libraries. Please wait...
  echo.
  call "%ROOT%SETUP-FRIEND.bat"
)

REM --- Confirm setup actually produced a working environment ------------
if not exist "%ROOT%.venv-portable\Scripts\python.exe" (
  echo.
  echo  [X] Setup did not finish. Double-click DIAGNOSE.bat and send the
  echo      report ^(diagnose-report.txt^) to whoever is helping you.
  echo.
  pause
  exit /b 1
)

REM --- Launch the four services + open the browser ----------------------
echo.
echo  Booting services (four windows will open). Closing those windows
echo  stops the demo. Leave them open while you use it.
echo.
call "%ROOT%RUN-DEMO.bat"

exit /b 0
