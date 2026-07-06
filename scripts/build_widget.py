"""Build apps/widget/dist/widget.js from the template in apps/widget/src.

Replaces the base64 font placeholders with the real base64 of the bundled
woff2 files, so glyphs render on judge laptops that don't have the fonts
installed:

- `__AAAS_NOTO_ORIYA_B64__` <- noto-sans-oriya-400-subset.woff2
  (Windows ships "Kalinga", which renders Oriya conjuncts poorly)
- `__AAAS_ATKINSON_B64__` <- atkinson-hyperlegible-400-latin.woff2
  (legibility fallback in the Comfortable-letters stack)
- `__AAAS_OPENDYSLEXIC_B64__` / `__AAAS_OPENDYSLEXIC_BOLD_B64__` <-
  opendyslexic-{400,700}.woff (the Comfortable-letters page font,
  user-chosen; SIL-OFL)

Also copies the built file to apps/extension/widget.js so the browser
extension ships the same bundle.

Run manually:

    python scripts/build_widget.py

Or as part of the full bundle rebuild via `scripts/build_bundle.py`.
"""

from __future__ import annotations

import base64
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "apps" / "widget" / "src" / "widget.js"
DIST = REPO / "apps" / "widget" / "dist" / "widget.js"
EXT = REPO / "apps" / "extension" / "widget.js"
FONTS_DIR = REPO / "apps" / "widget" / "src" / "fonts"
FONTS = [
    ("__AAAS_NOTO_ORIYA_B64__", FONTS_DIR / "noto-sans-oriya-400-subset.woff2"),
    ("__AAAS_ATKINSON_B64__", FONTS_DIR / "atkinson-hyperlegible-400-latin.woff2"),
    ("__AAAS_OPENDYSLEXIC_B64__", FONTS_DIR / "opendyslexic-400.woff"),
    ("__AAAS_OPENDYSLEXIC_BOLD_B64__", FONTS_DIR / "opendyslexic-700.woff"),
]


def main() -> int:
    if not SRC.is_file():
        print(f"[build_widget] missing source: {SRC}", file=sys.stderr)
        return 1

    out = SRC.read_text(encoding="utf-8")
    for marker, font in FONTS:
        if not font.is_file():
            print(f"[build_widget] missing font: {font}", file=sys.stderr)
            return 1
        if marker not in out:
            print(
                f"[build_widget] marker {marker!r} not found in {SRC} — "
                "has widget.js been edited to remove it?",
                file=sys.stderr,
            )
            return 2
        font_b64 = base64.b64encode(font.read_bytes()).decode("ascii")
        out = out.replace(marker, font_b64)
        print(f"[build_widget] inlined {font.name} ({len(font_b64):,} b64 chars)")

    DIST.parent.mkdir(parents=True, exist_ok=True)
    DIST.write_text(out, encoding="utf-8")
    print(f"[build_widget] wrote {DIST} ({DIST.stat().st_size:,} bytes)")

    shutil.copyfile(DIST, EXT)
    print(f"[build_widget] synced {EXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
