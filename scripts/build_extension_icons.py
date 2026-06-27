"""Generate 16/32/48/128 PNG icons for the AaaS Companion browser extension.

Stdlib-only (struct + zlib), so the bundle build runs on any Python 3.12+.
If Pillow is importable and the Odia subset font is on disk, it renders a
white "ଅ" character on a blue square for a proper branded icon. Otherwise
it falls back to a simple blue square with a lighter-blue inner circle —
recognisable in a toolbar, good enough for a demo.

Run manually:

    python scripts/build_extension_icons.py

Or as part of the full bundle rebuild via scripts/build_bundle.py.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "apps" / "extension" / "icons"
FONT_PATH = REPO / "apps" / "widget" / "src" / "fonts" / "noto-sans-oriya-400-subset.woff2"
SIZES = (16, 32, 48, 128)

BG = (0x1A, 0x66, 0xCC)     # primary blue (#1a66cc, matches widget FAB)
INNER = (0x2D, 0x7A, 0xD9)  # lighter blue hover colour
FG = (0xFF, 0xFF, 0xFF)     # white


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_png(path: Path, width: int, height: int, rgba_rows: list[bytes]) -> None:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rgba_rows)
    idat = zlib.compress(raw, 9)
    path.write_bytes(
        sig
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _stdlib_icon(size: int) -> tuple[int, int, list[bytes]]:
    # Rounded square with a lighter inner circle. Alpha channel so the
    # corners are transparent instead of a bright-blue box.
    corner_r = max(2, size // 6)
    inner_r = size * 0.32
    cx = cy = (size - 1) / 2.0
    rows: list[bytes] = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            # Round-corner mask: each corner is a quarter-circle of radius
            # corner_r. If the pixel is in the corner square and outside
            # the circle, make it transparent.
            in_corner = False
            for (cxr, cyr) in (
                (corner_r, corner_r),
                (size - 1 - corner_r, corner_r),
                (corner_r, size - 1 - corner_r),
                (size - 1 - corner_r, size - 1 - corner_r),
            ):
                if (
                    (x < corner_r and y < corner_r and cxr == corner_r and cyr == corner_r)
                    or (x > size - 1 - corner_r and y < corner_r and cxr != corner_r and cyr == corner_r)
                    or (x < corner_r and y > size - 1 - corner_r and cxr == corner_r and cyr != corner_r)
                    or (x > size - 1 - corner_r and y > size - 1 - corner_r and cxr != corner_r and cyr != corner_r)
                ):
                    dx = x - cxr
                    dy = y - cyr
                    if dx * dx + dy * dy > corner_r * corner_r:
                        in_corner = True
                        break
            if in_corner:
                row += bytes((0, 0, 0, 0))
                continue

            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= inner_r:
                row += bytes(FG + (0xFF,))
            elif dist <= inner_r + 1:
                # 1-pixel antialias ring between fg and bg
                t = max(0.0, min(1.0, (inner_r + 1 - dist)))
                r = int(BG[0] * (1 - t) + FG[0] * t)
                g = int(BG[1] * (1 - t) + FG[1] * t)
                b = int(BG[2] * (1 - t) + FG[2] * t)
                row += bytes((r, g, b, 0xFF))
            else:
                row += bytes(BG + (0xFF,))
        rows.append(bytes(row))
    return size, size, rows


def _pillow_icon(size: int) -> tuple[int, int, list[bytes]] | None:
    """Render a white 'ଅ' over a blue rounded square. Returns None if Pillow
    or the font are unavailable so the caller can fall back."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        return None
    if not FONT_PATH.is_file():
        return None
    # Pillow reads woff2 via FreeType only if it was built with woff2 support.
    # If that import fails we fall back to the stdlib icon.
    try:
        font = ImageFont.truetype(str(FONT_PATH), int(size * 0.74))
    except Exception:
        return None
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = max(2, size // 6)
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=radius, fill=BG + (0xFF,)
    )
    text = "ଅ"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
    except Exception:
        return None
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
        text,
        fill=FG + (0xFF,),
        font=font,
    )
    rows = []
    for y in range(size):
        rows.append(bytes(img.crop((0, y, size, y + 1)).tobytes()))
    return size, size, rows


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    used = "stdlib"
    for size in SIZES:
        data = _pillow_icon(size) or _stdlib_icon(size)
        if data is None:
            data = _stdlib_icon(size)
        if data is _pillow_icon:  # never true — kept to hint at intent
            used = "pillow"
        w, h, rows = data
        out = OUT_DIR / f"icon-{size}.png"
        _write_png(out, w, h, rows)
        print(f"[build_extension_icons] wrote {out} ({out.stat().st_size} bytes)")
    # Detect Pillow path after the fact for the summary line.
    if _pillow_icon(16) is not None:
        used = "pillow"
    print(f"[build_extension_icons] renderer: {used}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
