"""Generate scanned-looking notice fixtures for the OCR demo.

Renders bureaucratic English notices (wording chosen to exercise the
simplify glossary: "hereby", "furnish", "requisite", "w.e.f." ...)
onto an off-white canvas with noise, a slight skew and a stamp box, so
they read as photocopied government paper. Outputs:

- apps/demo-sites/jajpur-collectorate/assets/notice-scan.png
- apps/demo-sites/bse-odisha/assets/circular-scan.pdf  (image-only PDF,
  2 pages — genuinely no text layer, i.e. a true scan simulation)

English on purpose: the demo beat is scan -> plain Odia speech, and
PIL cannot shape Odia conjuncts without libraqm. Real Odia scans work
through the ori traineddata at runtime.

Run (needs Pillow — the translate venv has it via the [ocr] extra):

    services/translate/.venv/Scripts/python scripts/make_demo_notices.py
"""

from __future__ import annotations

import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
JAJPUR_OUT = REPO / "apps" / "demo-sites" / "jajpur-collectorate" / "assets" / "notice-scan.png"
BSE_OUT = REPO / "apps" / "demo-sites" / "bse-odisha" / "assets" / "circular-scan.pdf"

PAPER = (245, 242, 234)
INK = (28, 30, 38)

W, H = 1240, 940

NOTICE_JAJPUR = {
    "header": ["GOVERNMENT OF ODISHA", "OFFICE OF THE DISTRICT COLLECTOR, JAJPUR"],
    "ref": "No. 1247 /Estt.     Date: 02.04.2026",
    "title": "N O T I F I C A T I O N",
    "body": [
        "It is hereby notified that all applicants under the Post-Matric "
        "Scholarship Scheme shall furnish the requisite documents on or "
        "before the stipulated date w.e.f. 15.04.2026; applications "
        "received subsequent to the said date shall be liable to rejection.",
        "Applicants are required to peruse the guidelines and intimate any "
        "grievance to the competent authority at the earliest. Verification "
        "of domicile certificates shall commence forthwith at the block "
        "offices.",
    ],
    "footer": "By order of the Collector",
}

CIRCULAR_BSE_P1 = {
    "header": ["BOARD OF SECONDARY EDUCATION, ODISHA", "CUTTACK"],
    "ref": "No. EX-II/886     Date: 05.04.2026",
    "title": "E X A M I N A T I O N   C I R C U L A R",
    "body": [
        "It is hereby notified that the Annual High School Certificate "
        "Examination shall commence w.e.f. 21.04.2026. Candidates shall "
        "furnish the requisite admit cards prior to entering the "
        "examination hall.",
    ],
    "footer": "Controller of Examinations",
}

CIRCULAR_BSE_P2 = {
    "header": ["BOARD OF SECONDARY EDUCATION, ODISHA"],
    "ref": "Page 2 of 2",
    "title": "",
    "body": [
        "Centre superintendents are required to intimate the aforesaid "
        "arrangements to all invigilators and shall be liable to furnish "
        "compliance reports expeditiously, in accordance with the "
        "stipulated guidelines.",
    ],
    "footer": "",
}


def _font(size: int, serif: bool = True) -> ImageFont.FreeTypeFont:
    candidates = ["times.ttf", "georgia.ttf", "arial.ttf"] if serif else ["arial.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def render_page(spec: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    h1 = _font(40)
    h2 = _font(30)
    body_font = _font(28)
    small = _font(24)

    y = 70
    for line in spec["header"]:
        w = draw.textlength(line, font=h1 if line is spec["header"][0] else h2)
        draw.text(((W - w) / 2, y), line, font=h1 if line is spec["header"][0] else h2, fill=INK)
        y += 52
    draw.line([(120, y + 8), (W - 120, y + 8)], fill=INK, width=2)
    y += 36
    draw.text((120, y), spec["ref"], font=small, fill=INK)
    y += 56
    if spec["title"]:
        w = draw.textlength(spec["title"], font=h2)
        draw.text(((W - w) / 2, y), spec["title"], font=h2, fill=INK)
        y += 66

    for para in spec["body"]:
        for line in textwrap.wrap(para, width=68):
            draw.text((120, y), line, font=body_font, fill=INK)
            y += 42
        y += 24

    if spec["footer"]:
        y = max(y + 30, H - 160)
        draw.text((W - 480, y), spec["footer"], font=body_font, fill=INK)
        # A stamp-ish box for scanned-paper flavour.
        draw.rectangle([(120, y - 10), (360, y + 70)], outline=(90, 90, 120), width=3)
        draw.text((140, y + 12), "RECEIVED", font=small, fill=(90, 90, 120))

    # Scan artefacts: speckle noise + slight skew on off-white.
    random.seed(42)
    px = img.load()
    for _ in range(4000):
        x = random.randrange(W)
        yy = random.randrange(H)
        g = random.randrange(140, 220)
        px[x, yy] = (g, g, g)
    img = img.rotate(-0.6, expand=False, fillcolor=PAPER, resample=Image.BICUBIC)
    return img


def main() -> int:
    JAJPUR_OUT.parent.mkdir(parents=True, exist_ok=True)
    BSE_OUT.parent.mkdir(parents=True, exist_ok=True)

    render_page(NOTICE_JAJPUR).save(JAJPUR_OUT, "PNG")
    print(f"[notices] wrote {JAJPUR_OUT} ({JAJPUR_OUT.stat().st_size:,} bytes)")

    p1 = render_page(CIRCULAR_BSE_P1)
    p2 = render_page(CIRCULAR_BSE_P2)
    p1.save(BSE_OUT, "PDF", resolution=120, save_all=True, append_images=[p2])
    print(f"[notices] wrote {BSE_OUT} ({BSE_OUT.stat().st_size:,} bytes, 2 pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
