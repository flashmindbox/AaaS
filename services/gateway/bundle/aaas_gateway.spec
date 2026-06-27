# PyInstaller spec for the AaaS Gateway.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent                  # services/gateway/
REPO = ROOT.parent.parent                               # repo root
ENTRYPOINT = str(ROOT / "bundle" / "launcher.py")

datas = []
# Ship the widget + demo sites + exam + admin so the gateway serves them
# even when launched from an isolated temp directory. _mount_demo_assets
# probes these paths at runtime via sys._MEIPASS.
datas.append((str(REPO / "apps" / "widget" / "dist"), "apps/widget/dist"))
datas.append((str(REPO / "apps" / "demo-sites"), "apps/demo-sites"))
datas.append((str(REPO / "apps" / "exam"), "apps/exam"))
datas.append((str(REPO / "apps" / "admin"), "apps/admin"))
# FastAPI/pydantic look up their package metadata at runtime.
for pkg in ("fastapi", "pydantic", "pydantic-settings", "httpx", "structlog"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = []
# Uvicorn loads `app.main:app` by string at runtime — see TTS spec for context.
hiddenimports += collect_submodules("app")

block_cipher = None

a = Analysis(
    [ENTRYPOINT],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "torch", "transformers"],
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
    name="aaas-gateway",
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
    name="aaas-gateway",
)
