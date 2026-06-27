"""Vendor transformers.js + onnxruntime-web WASM into apps/extension/vendor/.

The browser extension's main-world widget dynamic-imports these via
chrome-extension:// URLs to run ONNX inference inside the page. MV3's
``content_security_policy.extension_pages`` only permits ``'self'`` and
``'wasm-unsafe-eval'`` — jsdelivr / unpkg loads are rejected at
runtime — so we MUST host transformers.js and ort-web locally.

Idempotent: if vendor/VERSION.txt already matches the pinned version,
skips the download. Use ``--force`` to refetch.

Usage:

    python scripts/build_extension_vendor.py            # default: skip if current
    python scripts/build_extension_vendor.py --force    # always redownload
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / "apps" / "extension" / "vendor"

# Bump manually after testing a newer transformers.js. The jsdelivr path
# below mirrors npm, so whichever version the on-device adapter (ondevice.js)
# was written against is what should ship.
TJS_VERSION = "3.0.2"
TJS_CDN = f"https://cdn.jsdelivr.net/npm/@huggingface/transformers@{TJS_VERSION}/dist"

# transformers.js v3 bundles ort-web's JS glue into transformers.min.js;
# only the WebAssembly binary is loaded separately at inference time from
# env.backends.onnx.wasm.wasmPaths. v3.0.2's dist/ ships exactly one WASM
# variant (jsep — the WebGPU-capable SIMD+threaded build) and ort-web's
# runtime code falls back to the non-threaded path automatically when the
# content-script main world has no SharedArrayBuffer.
FILES = [
    "transformers.min.js",
    "ort-wasm-simd-threaded.jsep.wasm",
]

STAMP_PATH = VENDOR / "VERSION.txt"
STAMP_TEXT = f"@huggingface/transformers {TJS_VERSION}\n"


def log(msg: str) -> None:
    print(f"[extension-vendor] {msg}", flush=True)


def fetch(url: str, dest: Path) -> int:
    log(f"GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "aaas-ext-build"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        sys.exit(
            f"fetch failed for {url}: {exc}\n"
            "the vendor step needs network access to jsdelivr.net — "
            "retry once your connection is back, or set up an HTTPS proxy."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="refetch even if up-to-date")
    args = ap.parse_args()

    VENDOR.mkdir(parents=True, exist_ok=True)

    if not args.force and STAMP_PATH.exists():
        if STAMP_PATH.read_text(encoding="utf-8") == STAMP_TEXT and all(
            (VENDOR / f).exists() for f in FILES
        ):
            log(f"already at {STAMP_TEXT.strip()} — skipping (pass --force to refetch)")
            return 0

    # Wipe any prior version's files so a version bump doesn't leave
    # stale .wasm blobs that the fresh .mjs loader no longer matches.
    for child in VENDOR.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    total = 0
    for name in FILES:
        total += fetch(f"{TJS_CDN}/{name}", VENDOR / name)

    STAMP_PATH.write_text(STAMP_TEXT, encoding="utf-8")
    log(
        f"vendor ready  {len(FILES)} files, "
        f"{total / (1024**2):.1f} MB -> {VENDOR}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
