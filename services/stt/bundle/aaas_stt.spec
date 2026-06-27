# PyInstaller spec for the AaaS STT service.
#
# Build from the service root with:
#
#     pyinstaller bundle/aaas_stt.spec   # produces dist/aaas-stt/
#
# The default mock engine has no torch/transformers dependency, so the
# resulting bundle is small (~50 MB). If you ship with the real Indic
# backend, rebuild after ``pip install -e .[indic]`` and the torch
# wheels get picked up automatically — but expect ~1 GB on disk.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent  # services/stt/
ENTRYPOINT = str(ROOT / "bundle" / "launcher.py")

datas = []
# FastAPI/pydantic look up metadata at runtime.
for pkg in ("fastapi", "pydantic", "pydantic-settings", "structlog", "soundfile"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = []
# Uvicorn loads `app.main:app` by string at runtime.
hiddenimports += collect_submodules("app")

# Exclude heavy optional deps from the mock-only bundle. If a future
# build pulls in `[indic]` or `[whisper]`, remove from this list.
_EXCLUDES = [
    "tkinter",
    "matplotlib",
    "pandas",
    "torch",
    "transformers",
    "torchaudio",
    "faster_whisper",
]

block_cipher = None

a = Analysis(
    [ENTRYPOINT],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="aaas-stt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="aaas-stt",
)
