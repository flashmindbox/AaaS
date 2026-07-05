"""Quick verification that the portable zip has the right stuff
and nothing leaky.
"""

from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path

ZIP = Path(r"C:\My Apps\AaaS-Portable.zip")


REQUIRED = [
    "AaaS-Portable/README-FOR-FRIEND.md",
    "AaaS-Portable/START-HERE.bat",
    "AaaS-Portable/SETUP-FRIEND.bat",
    "AaaS-Portable/RUN-DEMO.bat",
    "AaaS-Portable/ENSURE-READY.bat",
    "AaaS-Portable/DIAGNOSE.bat",
    "AaaS-Portable/scripts/ensure_ready.py",
    "AaaS-Portable/package.json",
    "AaaS-Portable/pnpm-lock.yaml",
    "AaaS-Portable/pnpm-workspace.yaml",
    "AaaS-Portable/turbo.json",
    "AaaS-Portable/tsconfig.base.json",
    "AaaS-Portable/services/gateway/pyproject.toml",
    "AaaS-Portable/services/gateway/app/main.py",
    "AaaS-Portable/services/tts/pyproject.toml",
    "AaaS-Portable/services/stt/pyproject.toml",
    "AaaS-Portable/services/translate/pyproject.toml",
    "AaaS-Portable/apps/widget/dist/widget.js",
    "AaaS-Portable/apps/extension/manifest.json",
]

FORBIDDEN_PREFIXES = [
    "AaaS-Portable/node_modules/",
    "AaaS-Portable/.git/",
    "AaaS-Portable/.claude/",
    "AaaS-Portable/.venv-portable/",
    "AaaS-Portable/.pip-cache/",
    "AaaS-Portable/dist/",  # root dist
]

FORBIDDEN_CONTAINING = [
    "/.venv/",
    "/__pycache__/",
    "/.pytest_cache/",
    "/.mypy_cache/",
    "/.ruff_cache/",
    "/.turbo/",
]

FORBIDDEN_SUFFIXES = (".pyc", ".tsbuildinfo")

# We DO expect these model caches
EXPECTED_MODELS = [
    "AaaS-Portable/services/tts/models/models--facebook--mms-tts-ory/",
    "AaaS-Portable/services/tts/models/models--facebook--mms-tts-hin/",
    "AaaS-Portable/services/tts/models/models--facebook--mms-tts-eng/",
    "AaaS-Portable/services/translate/models/models--ai4bharat--indictrans2-en-indic-dist-200M/",
    "AaaS-Portable/services/translate/models/models--ai4bharat--indictrans2-indic-en-dist-200M/",
    "AaaS-Portable/apps/extension/models/",
]


def main() -> int:
    if not ZIP.exists():
        print(f"ERROR: {ZIP} missing")
        return 2

    print(f"Verifying {ZIP} ({ZIP.stat().st_size / 1024**3:.2f} GB)")
    names: list[str] = []
    sizes: dict[str, int] = {}
    with zipfile.ZipFile(ZIP) as zf:
        for info in zf.infolist():
            names.append(info.filename)
            sizes[info.filename] = info.file_size

    total = sum(sizes.values())
    print(f"  {len(names)} entries, uncompressed {total / 1024**3:.2f} GB")

    bad = 0

    # REQUIRED files
    for r in REQUIRED:
        if r not in sizes:
            print(f"  [MISS] required: {r}")
            bad += 1
    # FORBIDDEN prefixes
    for p in FORBIDDEN_PREFIXES:
        leak = [n for n in names if n.startswith(p)]
        if leak:
            print(f"  [LEAK] {p} present ({len(leak)} entries, first: {leak[0]})")
            bad += 1
    # FORBIDDEN containing
    for sub in FORBIDDEN_CONTAINING:
        leak = [n for n in names if sub in n]
        if leak:
            print(f"  [LEAK] {sub} present ({len(leak)} entries, first: {leak[0]})")
            bad += 1
    # FORBIDDEN suffixes
    for suf in FORBIDDEN_SUFFIXES:
        leak = [n for n in names if n.endswith(suf)]
        if leak:
            print(f"  [LEAK] *{suf} present ({len(leak)} entries, first: {leak[0]})")
            bad += 1

    # EXPECTED model dirs
    for m in EXPECTED_MODELS:
        hit = [n for n in names if n.startswith(m)]
        sub_total = sum(sizes[n] for n in hit)
        if not hit:
            print(f"  [MISS] expected model dir: {m}")
            bad += 1
        else:
            print(f"  [OK]  {m}  ({len(hit)} files, {sub_total / 1024**2:.0f} MB)")

    # Top-size report
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:10]
    print("\n  Top 10 largest files in zip:")
    for n, s in top:
        print(f"    {s / 1024**2:8.1f} MB  {n}")

    # Per-top-level-dir size
    buckets: Counter[str] = Counter()
    for n, s in sizes.items():
        parts = n.split("/", 2)
        if len(parts) >= 2:
            buckets[parts[1]] += s
    print("\n  Size by top-level dir:")
    for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]):
        print(f"    {v / 1024**2:8.1f} MB  {k}")

    if bad:
        print(f"\n  {bad} issues found.")
        return 1
    print("\n  All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
