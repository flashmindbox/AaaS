"""Build apps/widget/dist/widget.js from the template in apps/widget/src.

Replaces the `__AAAS_NOTO_ORIYA_B64__` placeholder with the real base64 of
`apps/widget/src/fonts/noto-sans-oriya-400-subset.woff2`, so Odia conjuncts
render on judge laptops that don't have Noto Sans Oriya installed
(common on Windows — "Kalinga" renders Oriya conjuncts poorly).

Run manually:

    python scripts/build_widget.py

Or as part of the full bundle rebuild via `scripts/build_bundle.py`.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "apps" / "widget" / "src" / "widget.js"
DIST = REPO / "apps" / "widget" / "dist" / "widget.js"
FONT = REPO / "apps" / "widget" / "src" / "fonts" / "noto-sans-oriya-400-subset.woff2"
MARKER = "__AAAS_NOTO_ORIYA_B64__"


def main() -> int:
    if not SRC.is_file():
        print(f"[build_widget] missing source: {SRC}", file=sys.stderr)
        return 1
    if not FONT.is_file():
        print(f"[build_widget] missing font: {FONT}", file=sys.stderr)
        return 1

    src = SRC.read_text(encoding="utf-8")
    if MARKER not in src:
        print(
            f"[build_widget] marker {MARKER!r} not found in {SRC} — "
            "has widget.js been edited to remove it?",
            file=sys.stderr,
        )
        return 2

    font_b64 = base64.b64encode(FONT.read_bytes()).decode("ascii")
    out = src.replace(MARKER, font_b64)

    DIST.parent.mkdir(parents=True, exist_ok=True)
    DIST.write_text(out, encoding="utf-8")

    print(
        f"[build_widget] wrote {DIST} "
        f"({DIST.stat().st_size:,} bytes, font {len(font_b64):,} b64 chars)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
