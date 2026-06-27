"""Build the portable AaaS demo zip for a friend's laptop.

Usage (from repo root):
    python scripts/make_portable_zip.py

Output:
    C:/My Apps/AaaS-Portable.zip

Ships source + pre-downloaded HF model caches. Excludes venvs,
node_modules, caches, PyInstaller build output, git history, and
other regenerable/ephemeral state.
"""

from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(r"C:\My Apps\Hackathon")
OUT = Path(r"C:\My Apps\AaaS-Portable.zip")
TOP = "AaaS-Portable"

EXCLUDE_DIR_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    ".venv-portable",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".next",
    ".cache",
    ".git",
    ".claude",
    ".pip-cache",
    ".run-logs",
}

EXCLUDE_REL_DIRS = {
    "dist",
    "infra/volumes",
    "infra/.data",
    # NLLB-200 orphan snapshot — not referenced by refs/main (which
    # points at f8d333...). Keeping it would waste 2.3 GB in the zip.
    "services/translate/models/models--facebook--nllb-200-distilled-600M/snapshots/a3e77be725cf30383f1faeb8d2f0b0ea98ac554e",
}

EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo", ".log")

EXCLUDE_FILES = {
    "services/gateway/out-through-gateway.wav",
    "diagnose-report.txt",
    "Thumbs.db",
    ".DS_Store",
    "Desktop.ini",
}


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def skip_dir(p: Path) -> bool:
    r = rel(p)
    if p.name in EXCLUDE_DIR_NAMES:
        return True
    if r in EXCLUDE_REL_DIRS:
        return True
    parts = r.split("/")
    # services/*/dist and services/*/build are PyInstaller artefacts
    if len(parts) >= 3 and parts[0] == "services" and parts[2] in ("dist", "build"):
        return True
    return False


def skip_file(p: Path) -> bool:
    r = rel(p)
    if r in EXCLUDE_FILES:
        return True
    if p.suffix in EXCLUDE_SUFFIXES:
        return True
    if p.name in {".DS_Store", "Thumbs.db", "Desktop.ini"}:
        return True
    return False


def human(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    if not ROOT.is_dir():
        print(f"ERROR: {ROOT} does not exist.")
        return 1

    if OUT.exists():
        print(f"Removing old {OUT} ...")
        OUT.unlink()

    print(f"Walking {ROOT} ...")
    files: list[Path] = []
    total_bytes = 0
    for cur, dirs, names in __import__("os").walk(ROOT):
        cur_path = Path(cur)
        dirs[:] = [d for d in dirs if not skip_dir(cur_path / d)]
        for n in names:
            fp = cur_path / n
            if skip_file(fp):
                continue
            try:
                total_bytes += fp.stat().st_size
            except OSError:
                continue
            files.append(fp)

    print(f"Found {len(files)} files totalling {human(total_bytes)}.")
    print(f"Writing {OUT} (this takes a while for large model weights)...")

    t0 = time.time()
    next_log = t0 + 5.0
    done_bytes = 0

    with zipfile.ZipFile(
        OUT,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=1,
        allowZip64=True,
    ) as zf:
        for i, fp in enumerate(files, 1):
            arcname = f"{TOP}/{rel(fp)}"
            try:
                zf.write(fp, arcname)
                done_bytes += fp.stat().st_size
            except OSError as e:
                print(f"  skip {rel(fp)}: {e}", file=sys.stderr)
                continue
            now = time.time()
            if now >= next_log:
                pct = 100 * done_bytes / max(1, total_bytes)
                print(
                    f"  {i}/{len(files)} files  "
                    f"{human(done_bytes)}/{human(total_bytes)} ({pct:.1f}%)  "
                    f"elapsed {int(now - t0)}s"
                )
                next_log = now + 5.0

    final = OUT.stat().st_size
    print(f"\nDone in {int(time.time() - t0)}s.")
    print(f"Output: {OUT}  ({human(final)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
