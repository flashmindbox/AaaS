# PyInstaller spec for the AaaS Translation service.
#
# Build from the service root with:
#
#     pyinstaller bundle/aaas_translate.spec   # produces dist/aaas-translate/
#
# Default (mock engine) bundle is <50 MB; `[indic]` adds ~1 GB of torch
# + IndicTrans2 weights.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent  # services/translate/
ENTRYPOINT = str(ROOT / "bundle" / "launcher.py")

datas = []
for pkg in ("fastapi", "pydantic", "pydantic-settings", "structlog", "httpx"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# certifi ships the CA bundle httpx needs for HTTPS to translate.googleapis.com.
try:
    import certifi

    datas += [(certifi.where(), "certifi")]
except Exception:
    pass

hiddenimports = []
hiddenimports += collect_submodules("app")
# The google engine reaches Google over HTTPS via httpx; pull httpx and its
# transport stack in explicitly since it's only imported lazily.
hiddenimports += collect_submodules("httpx")
hiddenimports += collect_submodules("httpcore")
hiddenimports += ["certifi", "h11", "anyio", "sniffio", "idna"]

_EXCLUDES = [
    "tkinter",
    "matplotlib",
    "pandas",
    "torch",
    "transformers",
    "sentencepiece",
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
    name="aaas-translate",
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
    name="aaas-translate",
)
