# PyInstaller spec for the AaaS TTS service.
#
# Build from the service root with:
#
#     python bundle/prefetch_model.py   # one-time, pulls weights
#     pyinstaller bundle/aaas_tts.spec  # produces dist/aaas-tts/
#
# The resulting folder is self-contained: Python runtime, torch,
# transformers, and the MMS-TTS-ory weights all travel together.

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

ROOT = Path(SPECPATH).resolve().parent  # services/tts/
ENTRYPOINT = str(ROOT / "bundle" / "launcher.py")

# transformers looks up package metadata at runtime (for version
# comparisons) — PyInstaller needs to be told explicitly to include it.
datas = []
datas += copy_metadata("transformers")
datas += copy_metadata("torch")
datas += copy_metadata("numpy")
datas += copy_metadata("tokenizers")
datas += copy_metadata("regex")
datas += copy_metadata("filelock")
datas += copy_metadata("huggingface-hub")
datas += copy_metadata("safetensors")
datas += copy_metadata("pyyaml")
# Ship the pre-fetched weights so first run is truly offline.
datas.append((str(ROOT / "models"), "models"))

hiddenimports = []
# Uvicorn loads `app.main:app` by string at runtime — PyInstaller's static
# analysis can't see it, so we pull the whole `app` package in explicitly.
hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("transformers.models.vits")
hiddenimports += collect_submodules("transformers.models.auto")

block_cipher = None

a = Analysis(
    [ENTRYPOINT],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas"],  # trim bundle size
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
    name="aaas-tts",
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
    name="aaas-tts",
)
