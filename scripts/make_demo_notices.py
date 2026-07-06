"""Generate scanned-looking notice fixtures for the OCR demo.

Renders bureaucratic English notices (wording chosen to exercise the
simplify glossary: "hereby", "furnish", "requisite", "w.e.f." ...)
onto an off-white canvas with noise, a slight skew and a stamp box, so
they read as photocopied government paper. Outputs:

- apps/demo-sites/jajpur-collectorate/assets/notice-scan.png
- apps/demo-sites/bse-odisha/assets/circular-scan.pdf  (image-only PDF,
  2 pages — genuinely no text layer, i.e. a true scan simulation)
- apps/demo-sites/ssepd-odisha/assets/pension-notice-scan.png  (MBPY
  pension revision — rupee amounts + dates exercise the TTS number
  verbalization when read aloud in Odia)
- apps/demo-sites/ssepd-odisha/assets/udid-camp-circular.pdf  (2-page
  UDID camp schedule)

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


SSEPD_DIR = REPO / "apps" / "demo-sites" / "ssepd-odisha" / "assets"
JAJPUR_DIR = REPO / "apps" / "demo-sites" / "jajpur-collectorate" / "assets"
UTKAL_DIR = REPO / "apps" / "demo-sites" / "utkal-university" / "assets"

CIRCULAR_TENDER_P1 = {
    "header": ["OFFICE OF THE DISTRICT COLLECTOR, JAJPUR", "TENDER SECTION"],
    "ref": "No. 88 /Tender     Date: 20.04.2026",
    "title": "T E N D E R   C A L L   N O T I C E",
    "body": [
        "It is hereby notified that sealed tenders are invited from "
        "registered contractors for the supply of assistive devices to "
        "block offices, at an estimated cost of Rs. 4800000, on or before "
        "05.05.2026. Tenders received subsequent to the said date shall "
        "be liable to rejection.",
    ],
    "footer": "Executive Officer",
}

CIRCULAR_TENDER_P2 = {
    "header": ["OFFICE OF THE DISTRICT COLLECTOR, JAJPUR"],
    "ref": "Page 2 of 2",
    "title": "",
    "body": [
        "Bidders shall furnish the requisite earnest money deposit of "
        "Rs. 96000 by demand draft and shall peruse the eligibility "
        "criteria appended hereto, in accordance with the stipulated "
        "guidelines. The competent authority reserves the right to reject "
        "any or all tenders without assigning any reason thereof.",
    ],
    "footer": "",
}

AIIMS_DIR = REPO / "apps" / "demo-sites" / "aiims-bhubaneswar" / "assets"

NOTICE_AIIMS = {
    "header": ["AIIMS BHUBANESWAR", "OFFICE OF THE MEDICAL SUPERINTENDENT"],
    "ref": "No. 512 /OPD     Date: 15.06.2026",
    "title": "O P D   N O T I C E",
    "body": [
        "It is hereby notified that OPD registration counters shall "
        "function w.e.f. 8:00 AM to 11:00 AM on all working days. The "
        "registration fee of Rs. 10 shall be remitted at the counter; "
        "patients aged 65 years and above and persons with disabilities "
        "are exempted from payment of the said fee and shall be attended "
        "on priority.",
        "Patients shall furnish the requisite referral slip, if any, at "
        "the time of registration. Teleconsultation slots may be availed "
        "through the Swasthya portal.",
    ],
    "footer": "Medical Superintendent",
}

CIRCULAR_AIIMS_P1 = {
    "header": ["AIIMS BHUBANESWAR", "PATIENT SERVICES"],
    "ref": "No. 534 /Guide     Date: 18.06.2026",
    "title": "P A T I E N T   G U I D E",
    "body": [
        "It is hereby notified that appointments for speciality OPDs, "
        "viz. Cardiology, Nephrology, Neurology and Orthopaedics, shall "
        "be booked prior to the date of visit. Walk-in patients shall be "
        "accommodated subject to availability of slots.",
    ],
    "footer": "Deputy Director (Admin)",
}

CIRCULAR_AIIMS_P2 = {
    "header": ["AIIMS BHUBANESWAR"],
    "ref": "Page 2 of 2",
    "title": "",
    "body": [
        "Attendants of admitted patients shall furnish the requisite "
        "gate pass at the entrance. Wheelchair assistance and sign-guided "
        "navigation shall be provisioned at Gate No. 2 for persons with "
        "disabilities, in accordance with the stipulated guidelines.",
    ],
    "footer": "",
}

NSP_DIR = REPO / "apps" / "demo-sites" / "national-scholarship" / "assets"

NOTICE_NSP = {
    "header": ["GOVERNMENT OF INDIA", "MINISTRY OF SOCIAL JUSTICE & EMPOWERMENT"],
    "ref": "No. F-1145 /NSP     Date: 01.07.2026",
    "title": "N O T I F I C A T I O N",
    "body": [
        "It is hereby notified that online applications for the "
        "Post-Matric Scholarship for Students with Disabilities shall be "
        "received on the National Scholarship Portal w.e.f. 15.07.2026. "
        "The last date for submission of applications is 31.10.2026.",
        "The scholarship shall comprise a maintenance allowance of "
        "Rs. 1200 per month for hostellers and Rs. 550 per month for day "
        "scholars, in addition to reimbursement of the compulsory "
        "non-refundable fees. Applicants shall furnish the requisite "
        "disability certificate issued by the competent authority.",
    ],
    "footer": "Under Secretary to the Government of India",
}

CIRCULAR_NSP_P1 = {
    "header": ["NATIONAL SCHOLARSHIP PORTAL", "APPLICANT GUIDELINES"],
    "ref": "No. F-1152 /NSP     Date: 05.07.2026",
    "title": "G U I D E L I N E S",
    "body": [
        "It is hereby notified that applicants shall register on the "
        "portal with a valid mobile number and shall furnish the Aadhaar "
        "number or the enrolment ID thereof. Applications lacking the "
        "requisite institution verification shall be summarily rejected.",
    ],
    "footer": "Mission Director, NSP",
}

CIRCULAR_NSP_P2 = {
    "header": ["NATIONAL SCHOLARSHIP PORTAL"],
    "ref": "Page 2 of 2",
    "title": "",
    "body": [
        "Institutions shall verify the applications expeditiously and in "
        "any case prior to 15.11.2026, failing which the applications "
        "shall lapse. State nodal officers are required to intimate the "
        "verification status to the Ministry, in accordance with the "
        "stipulated guidelines.",
    ],
    "footer": "",
}

NOTICE_UTKAL = {
    "header": ["UTKAL UNIVERSITY, BHUBANESWAR", "OFFICE OF THE REGISTRAR"],
    "ref": "No. 3172 /Acad.     Date: 22.04.2026",
    "title": "A D M I S S I O N   N O T I C E",
    "body": [
        "It is hereby notified that online applications for admission to "
        "postgraduate programmes for the session 2026-27 shall be received "
        "w.e.f. 01.05.2026. The last date for submission of applications "
        "is 20.05.2026 and the application fee of Rs. 500 shall be "
        "remitted online; candidates belonging to PwD category are "
        "exempted from payment of the said fee.",
        "Candidates shall furnish the requisite certificates at the time "
        "of counselling, failing which the provisional selection shall "
        "stand cancelled.",
    ],
    "footer": "Registrar",
}

NOTICE_SSEPD = {
    "header": ["GOVERNMENT OF ODISHA", "SSEPD DEPARTMENT, BHUBANESWAR"],
    "ref": "No. 2214 /SSEPD     Date: 12.05.2026",
    "title": "N O T I F I C A T I O N",
    "body": [
        "It is hereby notified that the monthly pension payable under the "
        "Madhu Babu Pension Yojana shall be enhanced from Rs. 500 to "
        "Rs. 1000 per month w.e.f. 01.06.2026 in respect of beneficiaries "
        "aged 60 to 79 years, and to Rs. 1200 per month in respect of "
        "beneficiaries aged 80 years and above.",
        "Beneficiaries shall furnish the requisite life certificate at the "
        "block office prior to 25.05.2026, failing which disbursement "
        "shall be kept in abeyance until verification is completed.",
    ],
    "footer": "By order of the Commissioner-cum-Secretary",
}

CIRCULAR_UDID_P1 = {
    "header": ["SSEPD DEPARTMENT, GOVERNMENT OF ODISHA"],
    "ref": "No. 2290 /UDID     Date: 18.05.2026",
    "title": "U D I D   C A M P   C I R C U L A R",
    "body": [
        "It is hereby notified that Unique Disability ID (UDID) enrolment "
        "camps shall be conducted w.e.f. 02.06.2026 at all block "
        "headquarters. Applicants shall furnish one passport photograph, "
        "the disability certificate and the Aadhaar card at the camp.",
    ],
    "footer": "Director, SSEPD",
}

CIRCULAR_UDID_P2 = {
    "header": ["SSEPD DEPARTMENT, GOVERNMENT OF ODISHA"],
    "ref": "Page 2 of 2",
    "title": "",
    "body": [
        "Block Social Security Officers are required to intimate the camp "
        "schedule to all gram panchayats and shall be liable to furnish "
        "compliance reports expeditiously, in accordance with the "
        "stipulated guidelines. Assistance desks for persons with visual "
        "impairment shall be provisioned at each venue.",
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

    SSEPD_DIR.mkdir(parents=True, exist_ok=True)
    pension_png = SSEPD_DIR / "pension-notice-scan.png"
    render_page(NOTICE_SSEPD).save(pension_png, "PNG")
    print(f"[notices] wrote {pension_png} ({pension_png.stat().st_size:,} bytes)")

    udid_pdf = SSEPD_DIR / "udid-camp-circular.pdf"
    u1 = render_page(CIRCULAR_UDID_P1)
    u2 = render_page(CIRCULAR_UDID_P2)
    u1.save(udid_pdf, "PDF", resolution=120, save_all=True, append_images=[u2])
    print(f"[notices] wrote {udid_pdf} ({udid_pdf.stat().st_size:,} bytes, 2 pages)")

    tender_pdf = JAJPUR_DIR / "tender-circular.pdf"
    t1 = render_page(CIRCULAR_TENDER_P1)
    t2 = render_page(CIRCULAR_TENDER_P2)
    t1.save(tender_pdf, "PDF", resolution=120, save_all=True, append_images=[t2])
    print(f"[notices] wrote {tender_pdf} ({tender_pdf.stat().st_size:,} bytes, 2 pages)")

    UTKAL_DIR.mkdir(parents=True, exist_ok=True)
    utkal_png = UTKAL_DIR / "admission-notice-scan.png"
    render_page(NOTICE_UTKAL).save(utkal_png, "PNG")
    print(f"[notices] wrote {utkal_png} ({utkal_png.stat().st_size:,} bytes)")

    NSP_DIR.mkdir(parents=True, exist_ok=True)
    nsp_png = NSP_DIR / "scholarship-notice-scan.png"
    render_page(NOTICE_NSP).save(nsp_png, "PNG")
    print(f"[notices] wrote {nsp_png} ({nsp_png.stat().st_size:,} bytes)")

    nsp_pdf = NSP_DIR / "guidelines-circular.pdf"
    n1 = render_page(CIRCULAR_NSP_P1)
    n2 = render_page(CIRCULAR_NSP_P2)
    n1.save(nsp_pdf, "PDF", resolution=120, save_all=True, append_images=[n2])
    print(f"[notices] wrote {nsp_pdf} ({nsp_pdf.stat().st_size:,} bytes, 2 pages)")

    AIIMS_DIR.mkdir(parents=True, exist_ok=True)
    opd_png = AIIMS_DIR / "opd-notice-scan.png"
    render_page(NOTICE_AIIMS).save(opd_png, "PNG")
    print(f"[notices] wrote {opd_png} ({opd_png.stat().st_size:,} bytes)")

    guide_pdf = AIIMS_DIR / "patient-guide-circular.pdf"
    g1 = render_page(CIRCULAR_AIIMS_P1)
    g2 = render_page(CIRCULAR_AIIMS_P2)
    g1.save(guide_pdf, "PDF", resolution=120, save_all=True, append_images=[g2])
    print(f"[notices] wrote {guide_pdf} ({guide_pdf.stat().st_size:,} bytes, 2 pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
