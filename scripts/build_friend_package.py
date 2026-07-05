"""Package the AaaS extension (v0.3.0) for a friend's laptop — two formats.

This does NOT rebuild the heavy bits (the on-device ONNX models, the vendored
transformers.js/ort-web runtime, or the PyInstaller service exes). Those are
unchanged build products already on disk; rebuilding them needs network +
torch + 10 min and would be pointless here. We only repackage.

Outputs (under <repo>/dist):

  1. AaaS-Companion-Extension-v<ver>.zip
       The self-contained Chrome/Edge extension with all on-device models
       and runtime bundled. Friend loads it unpacked. Read-aloud + voice
       work fully offline; "Translate this page" uses Google (needs net).

  2. AaaS-Demo.zip
       The full offline bundle (local gateway + STT/TTS/translate services
       + demo sites). Refreshes the bundle's extension/ copy to v0.3.0 then
       re-zips the existing dist/AaaS-Demo/ folder. Translation works with
       no internet here (bundled IndicTrans2 weights). Friend runs start.bat.

Usage:
    python scripts/build_friend_package.py            # both
    python scripts/build_friend_package.py --ext-only
    python scripts/build_friend_package.py --bundle-only
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXT_DIR = REPO / "apps" / "extension"
DIST = REPO / "dist"
BUNDLE_DIR = DIST / "AaaS-Demo"
BUNDLE_ZIP = DIST / "AaaS-Demo.zip"

# Directory / file names never shipped to a friend.
SKIP_DIR_NAMES = {".git", "__pycache__", ".cache", "node_modules", ".idea", ".vscode"}
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}

# Extension code files (small) that get refreshed into the full bundle. The
# big stuff (models/, vendor/, icons/) is identical to what's already there.
EXT_CODE_FILES = [
    "manifest.json",
    "background.js",
    "inject-config.js",
    "widget.js",
    "ondevice.js",
    "popup.html",
    "popup.css",
    "popup.js",
    "README.md",
]


def info(msg: str) -> None:
    print(f"     {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n>> {msg}", flush=True)


def _included(path: Path, root: Path) -> bool:
    """True if `path` should be shipped (no junk/cache dirs or files)."""
    rel_parts = path.relative_to(root).parts
    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return False
    if path.name in SKIP_FILE_NAMES or path.name.endswith(".env"):
        return False
    return True


def ext_version() -> str:
    data = json.loads((EXT_DIR / "manifest.json").read_text(encoding="utf-8"))
    return str(data.get("version", "0.0.0"))


INSTALL_TXT = """\
AaaS Accessibility Companion — install on your friend's laptop
==============================================================

WHAT IT DOES
  Adds a floating button to EVERY website. Click it to:
    - Read this page aloud in Odia, Hindi or English (real neural voice).
    - Translate this page into Odia/Hindi (Google Translate, in place).
    - Speak to fill forms by voice.
    - Turn on a dyslexia-friendly reading mode.

  The Odia / Hindi / English voices run ENTIRELY ON THIS LAPTOP (offline) —
  the models are inside this folder. "Translate this page" uses Google
  Translate, so it needs an internet connection.

REQUIREMENTS
  - Google Chrome, Microsoft Edge, Brave, or any Chromium browser (v111+).
  - Internet connection (only for the translation feature).

INSTALL (takes about a minute)
  1. Unzip this file somewhere permanent (e.g. Documents) and DO NOT delete
     the folder afterwards — Chrome loads the extension from this folder.
  2. Open your browser and go to:   chrome://extensions
     (in Edge:  edge://extensions )
  3. Turn ON "Developer mode" (toggle, top-right).
  4. Click "Load unpacked".
  5. Select the  AaaS-Companion-Extension  folder (the one with
     manifest.json inside it).
  6. Done. A blue "ଅ" button appears on web pages. Pin the toolbar icon
     to change the default language.

TRY IT
  - Open any English website (e.g. en.wikipedia.org).
  - Click the blue "ଅ" button (bottom-right).
  - Click "Read this page" to hear it in Odia, or "Translate this page".

NOTES
  - First read in each language takes a few seconds while the voice model
    loads; after that it's fast.
  - No account, no setup, no server. Everything is in this folder.
"""


def build_extension_zip() -> Path:
    ver = ext_version()
    step(f"packaging extension-only zip (v{ver})")
    if not (EXT_DIR / "models").is_dir():
        info("WARNING: apps/extension/models is missing — on-device voices "
             "will NOT work offline in this package.")
    if not (EXT_DIR / "vendor").is_dir():
        info("WARNING: apps/extension/vendor is missing — on-device mode "
             "will NOT work in this package.")

    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / f"AaaS-Companion-Extension-v{ver}.zip"
    if zip_path.exists():
        zip_path.unlink()

    top = "AaaS-Companion-Extension"  # friend points "Load unpacked" here
    n = 0
    total = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        # Install guide at the zip root, above the extension folder.
        zf.writestr("INSTALL.txt", INSTALL_TXT)
        for p in sorted(EXT_DIR.rglob("*")):
            if p.is_dir() or not _included(p, EXT_DIR):
                continue
            arc = f"{top}/{p.relative_to(EXT_DIR).as_posix()}"
            zf.write(p, arc)
            n += 1
            total += p.stat().st_size
    info(f"wrote {zip_path.name}: {n} files, {total/1e6:.0f} MB raw -> "
         f"{zip_path.stat().st_size/1e6:.0f} MB zip")
    return zip_path


def refresh_bundle_extension() -> None:
    """Copy the v0.3.0 extension code files into dist/AaaS-Demo/extension/."""
    import shutil

    dst = BUNDLE_DIR / "extension"
    if not dst.is_dir():
        raise SystemExit(
            f"missing {dst} — run scripts/build_bundle.py first to build the "
            "full offline bundle (services + demo), then re-run this."
        )
    for name in EXT_CODE_FILES:
        src = EXT_DIR / name
        if not src.is_file():
            info(f"skip (absent): {name}")
            continue
        shutil.copy2(src, dst / name)
    info(f"refreshed {len(EXT_CODE_FILES)} extension files in bundle -> v{ext_version()}")


def build_bundle_zip() -> Path:
    step("re-zipping full offline bundle (AaaS-Demo.zip)")
    if not BUNDLE_DIR.is_dir():
        raise SystemExit(
            f"missing {BUNDLE_DIR} — run scripts/build_bundle.py first."
        )
    refresh_bundle_extension()
    if BUNDLE_ZIP.exists():
        BUNDLE_ZIP.unlink()
    n = 0
    total = 0
    with zipfile.ZipFile(BUNDLE_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for p in sorted(BUNDLE_DIR.rglob("*")):
            if p.is_dir() or not _included(p, BUNDLE_DIR):
                continue
            arc = f"AaaS-Demo/{p.relative_to(BUNDLE_DIR).as_posix()}"
            zf.write(p, arc)
            n += 1
            total += p.stat().st_size
    info(f"wrote {BUNDLE_ZIP.name}: {n} files, {total/1e6:.0f} MB raw -> "
         f"{BUNDLE_ZIP.stat().st_size/1e6:.0f} MB zip")
    return BUNDLE_ZIP


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext-only", action="store_true", help="only the extension zip")
    ap.add_argument("--bundle-only", action="store_true", help="only the full bundle zip")
    args = ap.parse_args()

    made = []
    if not args.bundle_only:
        made.append(build_extension_zip())
    if not args.ext_only:
        made.append(build_bundle_zip())

    print("\nDONE. Hand these to your friend:")
    for p in made:
        print(f"  - {p}  ({p.stat().st_size/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
