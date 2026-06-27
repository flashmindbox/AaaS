"""Build a tiny update pack that patches an existing AaaS-Portable install.

Ships only the files that changed (launchers + widget + gateway/admin code),
plus an APPLY-UPDATE.bat that finds the installed folder and copies them in.
No multi-GB re-transfer needed.

Usage:
    python scripts/make_update_pack.py
Output:
    C:/My Apps/AaaS-Update.zip   (~0.6 MB)
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(r"C:\My Apps\Hackathon")
OUT = Path(r"C:\My Apps\AaaS-Update.zip")
TOP = "AaaS-Update"

# repo-relative files that changed and must land in the install
FILES = [
    "START-HERE.bat",
    "SETUP-FRIEND.bat",
    "DIAGNOSE.bat",
    "README-FOR-FRIEND.md",
    "apps/admin/admin.js",
    "apps/extension/widget.js",
    "apps/widget/dist/widget.js",
    "apps/widget/src/widget.js",
    "services/gateway/app/main.py",
    "services/gateway/app/routes/admin_api.py",
]

APPLY_BAT = r"""@echo off
REM ============================================================
REM  AaaS Update - applies the latest fixes to an existing
REM  AaaS-Portable install. No big re-download needed.
REM ============================================================
setlocal enabledelayedexpansion
set "SRC=%~dp0_update"
title AaaS Update

echo.
echo  ============================================================
echo   AaaS Update
echo  ============================================================
echo.

if not exist "%SRC%\START-HERE.bat" (
  echo  [X] Update files are missing. Re-extract AaaS-Update.zip and keep
  echo      APPLY-UPDATE.bat next to its _update folder.
  echo.
  pause
  exit /b 1
)

REM Find the installed AaaS-Portable folder automatically.
set "TARGET="
for %%D in (
  "%~dp0."
  "%~dp0AaaS-Portable"
  "C:\AaaS\AaaS-Portable"
  "%USERPROFILE%\Desktop\AaaS-Portable"
  "%USERPROFILE%\Downloads\AaaS-Portable"
  "%USERPROFILE%\Documents\AaaS-Portable"
) do (
  if not defined TARGET if exist "%%~fD\services\gateway\app\main.py" set "TARGET=%%~fD"
)

if not defined TARGET (
  echo  [X] Could not find your AaaS-Portable folder automatically.
  echo.
  echo      Fix: copy APPLY-UPDATE.bat AND the _update folder INTO your
  echo      AaaS-Portable folder ^(the one that contains "services" and
  echo      "apps"^), then double-click APPLY-UPDATE.bat again.
  echo.
  pause
  exit /b 1
)

echo  Found your install at:
echo     !TARGET!
echo.
echo  Make sure the demo is NOT running ^(close the four service windows^).
echo  Then press a key to apply the update...
pause >nul

xcopy /e /y /i "%SRC%\*" "!TARGET!\" >nul
if errorlevel 1 (
  echo.
  echo  [X] Could not copy the files. Close the demo windows ^(and any
  echo      open file from that folder^), then run APPLY-UPDATE.bat again.
  echo.
  pause
  exit /b 1
)

echo.
echo  [OK] Update applied. Your install now has the latest widget, the
echo       gateway/admin fixes, and the one-click START-HERE.bat.
echo.
echo  Next: open this folder and double-click START-HERE.bat
echo     !TARGET!
echo.
pause
exit /b 0
"""

READ_ME = (
    "AaaS Update Pack\r\n"
    "================\r\n\r\n"
    "1. Right-click AaaS-Update.zip -> Extract All.\r\n"
    "2. Open the extracted AaaS-Update folder.\r\n"
    "3. Double-click APPLY-UPDATE.bat.\r\n\r\n"
    "It finds your installed AaaS-Portable folder and copies the updated\r\n"
    "files in. Then open that folder and double-click START-HERE.bat.\r\n\r\n"
    "If it cannot find your install, copy APPLY-UPDATE.bat and the _update\r\n"
    "folder INTO your AaaS-Portable folder and run APPLY-UPDATE.bat again.\r\n"
)


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    missing = [f for f in FILES if not (ROOT / f).is_file()]
    if missing:
        print("ERROR: missing source files:", missing)
        return 1

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr(f"{TOP}/APPLY-UPDATE.bat", APPLY_BAT.replace("\n", "\r\n").encode("utf-8"))
        zf.writestr(f"{TOP}/READ-ME-FIRST.txt", READ_ME.encode("utf-8"))
        for rel in FILES:
            zf.write(ROOT / rel, f"{TOP}/_update/{rel}")

    size = OUT.stat().st_size
    print(f"Wrote {OUT}  ({size/1024:.0f} KB, {len(FILES)} updated files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
