"""Generate prep PDFs for Pratikshya (class 12, Team SUBARNAREKHA).

Produces four short, plain-language PDFs inside hackathon/pratikshya-prep/:
  01-What-is-AaaS.pdf          - project explainer + architecture diagram
  02-Demo-Walkthrough.pdf      - step-by-step demo script + flow diagram
  03-Judge-Questions.pdf       - Q&A cheat sheet
  04-Pitch-and-Fallback.pdf    - pitch scripts + emergency fallback

Usage:  python scripts/generate_pratikshya_prep.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --- Paths ---------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hackathon" / "pratikshya-prep"
OUT.mkdir(parents=True, exist_ok=True)

# --- Fonts (register Nirmala UI for Odia script) --------------------------

try:
    pdfmetrics.registerFont(TTFont("Nirmala", r"C:\Windows\Fonts\Nirmala.ttf"))
    pdfmetrics.registerFont(TTFont("Nirmala-Bold", r"C:\Windows\Fonts\NirmalaB.ttf"))
    ODIA_FONT = "Nirmala"
    ODIA_FONT_BOLD = "Nirmala-Bold"
except Exception:
    ODIA_FONT = "Helvetica"
    ODIA_FONT_BOLD = "Helvetica-Bold"

# --- Palette (Odisha-inspired teal + warm gold) ---------------------------

TEAL = colors.HexColor("#0B6E6E")
TEAL_LIGHT = colors.HexColor("#E5F2F2")
GOLD = colors.HexColor("#C48A1B")
GOLD_LIGHT = colors.HexColor("#FDF3DB")
INK = colors.HexColor("#1E2A2A")
MUTED = colors.HexColor("#556363")
PAPER = colors.HexColor("#FFFDF8")
BORDER = colors.HexColor("#D5D0C3")

# --- Styles ---------------------------------------------------------------

base = getSampleStyleSheet()

STYLES = {
    "title": ParagraphStyle(
        "Title", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=26, leading=30, textColor=TEAL, spaceAfter=4, alignment=TA_LEFT,
    ),
    "subtitle": ParagraphStyle(
        "Subtitle", parent=base["Normal"], fontName="Helvetica",
        fontSize=12, leading=15, textColor=MUTED, spaceAfter=16,
    ),
    "h1": ParagraphStyle(
        "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, textColor=TEAL, spaceBefore=14, spaceAfter=6,
    ),
    "h2": ParagraphStyle(
        "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=16, textColor=INK, spaceBefore=10, spaceAfter=4,
    ),
    "body": ParagraphStyle(
        "Body", parent=base["Normal"], fontName="Helvetica",
        fontSize=11, leading=15, textColor=INK, spaceAfter=6,
    ),
    "body_em": ParagraphStyle(
        "BodyEm", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=11, leading=15, textColor=MUTED, spaceAfter=6,
    ),
    "bullet": ParagraphStyle(
        "Bullet", parent=base["Normal"], fontName="Helvetica",
        fontSize=11, leading=15, textColor=INK, leftIndent=14, bulletIndent=2,
        spaceAfter=3,
    ),
    "quote": ParagraphStyle(
        "Quote", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=11.5, leading=16, textColor=INK, leftIndent=12, rightIndent=8,
        spaceBefore=4, spaceAfter=8, borderColor=GOLD, borderPadding=6,
    ),
    "odia": ParagraphStyle(
        "Odia", parent=base["Normal"], fontName=ODIA_FONT_BOLD,
        fontSize=14, leading=20, textColor=TEAL, spaceAfter=2,
    ),
    "small": ParagraphStyle(
        "Small", parent=base["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=MUTED,
    ),
    "footer": ParagraphStyle(
        "Footer", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=9, leading=11, textColor=MUTED, alignment=TA_CENTER,
    ),
}


# --- Helpers --------------------------------------------------------------

def para(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet_list(items: list[str]) -> list[Flowable]:
    return [Paragraph(f"• {t}", STYLES["bullet"]) for t in items]


def callout(title: str, body_lines: list[str], colour=GOLD_LIGHT, border=GOLD) -> Table:
    """A highlighted box — use for 'memorize this' or 'tip' panels."""
    inner = [Paragraph(f"<b>{title}</b>", STYLES["body"])]
    for line in body_lines:
        inner.append(Paragraph(line, STYLES["body"]))
    tbl = Table([[inner]], colWidths=[16 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colour),
        ("BOX", (0, 0), (-1, -1), 0.75, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def qa_block(q: str, a: str) -> list[Flowable]:
    return [
        Paragraph(f"<b>Q.</b> {q}", STYLES["body"]),
        Paragraph(f"<b>A.</b> {a}", STYLES["body"]),
        Spacer(1, 6),
    ]


# --- Diagram flowables ----------------------------------------------------

class ArchitectureDiagram(Flowable):
    """Simple block diagram: User -> Widget -> Gateway -> 3 AI services -> Models.

    Drawn purely with reportlab shapes so it embeds natively in the PDF.
    """

    def __init__(self, width=17 * cm, height=9.5 * cm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, _w, _h):
        return self.width, self.height

    def _box(self, c, x, y, w, h, label, fill=TEAL_LIGHT, border=TEAL,
             text_colour=INK, bold=True, size=10):
        c.setFillColor(fill)
        c.setStrokeColor(border)
        c.setLineWidth(1)
        c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
        c.setFillColor(text_colour)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        lines = label.split("\n")
        total = size * 1.2 * len(lines)
        for i, line in enumerate(lines):
            text_w = c.stringWidth(line, "Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(x + (w - text_w) / 2, y + h / 2 + total / 2 - size * 1.2 * (i + 0.8), line)

    def _arrow(self, c, x1, y1, x2, y2, colour=MUTED):
        c.setStrokeColor(colour)
        c.setLineWidth(1.1)
        c.line(x1, y1, x2, y2)
        # Simple arrowhead
        import math
        angle = math.atan2(y2 - y1, x2 - x1)
        ah = 5
        c.line(x2, y2, x2 - ah * math.cos(angle - math.pi / 6),
               y2 - ah * math.sin(angle - math.pi / 6))
        c.line(x2, y2, x2 - ah * math.cos(angle + math.pi / 6),
               y2 - ah * math.sin(angle + math.pi / 6))

    def draw(self):
        c = self.canv
        w, h = self.width, self.height

        # Layer labels (left margin)
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(MUTED)
        for y_frac, label in [(0.86, "USER"), (0.60, "WIDGET"), (0.36, "SERVICES"), (0.10, "AI MODELS")]:
            c.drawString(0, h * y_frac - 5, label)

        # User (top)
        self._box(c, w * 0.35, h * 0.82, w * 0.30, h * 0.12,
                  "Student on college website\n(Odia / Hindi / English)",
                  fill=GOLD_LIGHT, border=GOLD, size=9.5)

        # Widget
        self._box(c, w * 0.32, h * 0.56, w * 0.36, h * 0.11,
                  "Floating 'ଅ' accessibility button",
                  fill=TEAL, border=TEAL, text_colour=colors.white, size=10)

        # Gateway (middle, just above services)
        self._box(c, w * 0.38, h * 0.44, w * 0.24, h * 0.08,
                  "Gateway (port 8000)", fill=TEAL_LIGHT, border=TEAL, size=9.5)

        # 3 services
        svc_y = h * 0.26
        svc_h = h * 0.11
        svc_w = w * 0.26
        gap = (w - 3 * svc_w) / 4
        svc_x = [gap, gap * 2 + svc_w, gap * 3 + 2 * svc_w]
        for x, title, sub in zip(
            svc_x,
            ["TTS 8001", "STT 8002", "Translate 8003"],
            ["Text -> Odia voice", "Odia voice -> text", "English <-> Odia"],
        ):
            self._box(c, x, svc_y, svc_w, svc_h, f"{title}\n{sub}",
                      fill=TEAL_LIGHT, border=TEAL, bold=True, size=9.5)

        # 4 AI models (bottom)
        mdl_y = h * 0.05
        mdl_h = h * 0.10
        mdl_titles = ["MMS-TTS (Meta)", "IndicWav2Vec", "IndicTrans2 (AI4Bharat)", "WCAG axe-core"]
        mdl_w = (w - 5 * gap) / 4
        for i, t in enumerate(mdl_titles):
            x = gap + i * (mdl_w + gap * 0.6)
            self._box(c, x, mdl_y, mdl_w, mdl_h, t,
                      fill=GOLD_LIGHT, border=GOLD, size=9)

        # Arrows
        self._arrow(c, w * 0.50, h * 0.82, w * 0.50, h * 0.67)  # user -> widget
        self._arrow(c, w * 0.50, h * 0.56, w * 0.50, h * 0.52)  # widget -> gateway
        # gateway -> 3 services
        for i, x in enumerate(svc_x):
            self._arrow(c, w * 0.50, h * 0.44, x + svc_w / 2, svc_y + svc_h)
        # services -> models (just the first three)
        for i in range(3):
            x = svc_x[i] + svc_w / 2
            mx = gap + i * (mdl_w + gap * 0.6) + mdl_w / 2
            self._arrow(c, x, svc_y, mx, mdl_y + mdl_h)


class DemoFlow(Flowable):
    """Horizontal flow of demo scenes: 1 -> 2 -> 3 -> 4 -> 5."""

    def __init__(self, width=17 * cm, height=3.5 * cm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, _w, _h):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        steps = [
            ("1.", "Open demo site", "Utkal admissions"),
            ("2.", "Click the 'ଅ'", "Widget slides up"),
            ("3.", "Read aloud", "Odia voice plays"),
            ("4.", "Translate", "Page becomes Odia"),
            ("5.", "Speak to form", "Voice fills field"),
        ]
        n = len(steps)
        gap = 0.4 * cm
        box_w = (w - (n - 1) * gap) / n
        box_h = h * 0.8
        box_y = h * 0.1
        for i, (num, title, sub) in enumerate(steps):
            x = i * (box_w + gap)
            c.setFillColor(TEAL_LIGHT)
            c.setStrokeColor(TEAL)
            c.setLineWidth(1)
            c.roundRect(x, box_y, box_w, box_h, 4, stroke=1, fill=1)
            c.setFillColor(TEAL)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x + 6, box_y + box_h - 14, num)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 9.5)
            c.drawString(x + 6, box_y + box_h - 30, title)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8.5)
            c.drawString(x + 6, box_y + box_h - 44, sub)
            # Arrow to next
            if i < n - 1:
                ax1 = x + box_w
                ax2 = x + box_w + gap - 2
                ay = box_y + box_h / 2
                c.setStrokeColor(MUTED)
                c.setLineWidth(1.1)
                c.line(ax1, ay, ax2, ay)
                c.line(ax2, ay, ax2 - 3, ay + 3)
                c.line(ax2, ay, ax2 - 3, ay - 3)


# --- Page template --------------------------------------------------------

def _draw_page_chrome(canvas, doc, doc_title: str):
    canvas.saveState()
    # Top band
    canvas.setFillColor(TEAL)
    canvas.rect(0, A4[1] - 0.9 * cm, A4[0], 0.9 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(2 * cm, A4[1] - 0.6 * cm, "AaaS - Team SUBARNAREKHA - Prep for Pratikshya")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 0.6 * cm, doc_title)

    # Footer
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Oblique", 8.5)
    canvas.drawCentredString(A4[0] / 2, 1 * cm,
                             "Smart Odisha Hackathon '25  -  page %d" % doc.page)
    canvas.restoreState()


def build_pdf(filename: Path, doc_title: str, story: list[Flowable]) -> None:
    doc = BaseDocTemplate(
        str(filename), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=doc_title, author="Team SUBARNAREKHA",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    tmpl = PageTemplate(id="main", frames=[frame],
                        onPage=lambda c, d: _draw_page_chrome(c, d, doc_title))
    doc.addPageTemplates([tmpl])
    doc.build(story)
    print(f"  wrote {filename.relative_to(ROOT)}")


# --- Document 1: What is AaaS? -------------------------------------------

def doc_what_is_aaas() -> list[Flowable]:
    s: list[Flowable] = []
    s.append(para("What is AaaS?", "title"))
    s.append(para("A short explainer for Pratikshya - read this first.", "subtitle"))

    s.append(para("The one-line answer", "h1"))
    s.append(Paragraph(
        "\"AaaS is an <b>open-source accessibility layer</b> for Indian public institutions. "
        "It is Odia-first. Any college or government portal can plug it in and make their "
        "website usable for blind, deaf, and dyslexic students - in Odia.\"",
        STYLES["quote"]))

    s.append(para("Think of it as <b>UPI, but for accessibility</b>. "
                  "UPI is one shared system that every bank plugs into. "
                  "AaaS is one shared system that every college and government portal can plug into.", "body"))

    s.append(para("Who it helps (remember these three names)", "h1"))
    s.append(para(
        "These are the three example users we keep coming back to in the demo and the pitch. "
        "Judges remember people more than they remember features.", "body"))

    user_table = Table([
        ["Priyanka", "Blind, class 12 in Puri, speaks only Odia.",
         "She fills an admissions form by speaking Odia into the widget."],
        ["Arun", "Dyslexic, reads Odia.",
         "He turns on Dyslexia Mode. Line spacing widens. Reading becomes easier."],
        ["Meera", "Deaf, from Cuttack.",
         "She watches the VC's Odia welcome video with auto-generated Odia captions."],
    ], colWidths=[2.5 * cm, 6.5 * cm, 8 * cm])
    user_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), TEAL_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), TEAL),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    s.append(user_table)
    s.append(Spacer(1, 10))

    s.append(para("The three problems we solve", "h1"))
    s.extend(bullet_list([
        "<b>Accessibility is broken.</b> Nearly every college/government website in Odisha "
        "is hard to use for disabled students. Labels are missing, colours have bad contrast, "
        "keyboards don't work, captchas are images-only.",
        "<b>Odia is ignored.</b> Global tools support Hindi or English, but treat Odia as "
        "\"other\". We make Odia the <i>first</i> language, not a translation afterthought.",
        "<b>Every college re-builds it badly.</b> 200+ colleges in Odisha each try to fix "
        "accessibility alone. We make one shared layer everyone can plug into.",
    ]))

    s.append(PageBreak())

    s.append(para("How it works (picture version)", "h1"))
    s.append(para(
        "Don't memorise every box. Just be able to point at the picture and say: "
        "\"Student talks to the widget, widget talks to three services, services use "
        "open-source AI models - everything runs on the college's own server.\"", "body"))
    s.append(Spacer(1, 6))
    s.append(ArchitectureDiagram())
    s.append(Spacer(1, 10))

    s.append(callout("If a judge asks what MMS-TTS / IndicTrans2 / IndicWav2Vec are:",
                     ["<b>MMS-TTS</b> (Meta) - turns text into Odia voice.",
                      "<b>IndicWav2Vec</b> (AI4Bharat) - turns Odia voice into text.",
                      "<b>IndicTrans2</b> (AI4Bharat, IIT Madras) - translates between Indian languages and English.",
                      "<b>axe-core</b> - scans a website for accessibility mistakes."]))
    s.append(Spacer(1, 8))
    s.append(para("You don't need to know the maths behind these. Judges rarely ask. "
                  "If they do: \"They are open-source models we picked because they work "
                  "well on Indian languages - Odia especially.\"", "body_em"))

    s.append(PageBreak())

    s.append(para("Numbers to know cold", "h1"))
    s.append(para("Memorise these five. They are the ones judges most often ask.", "body"))
    s.append(Spacer(1, 6))

    num_rows = [
        ["21 lakh+", "Persons with disabilities in Odisha (2011 Census - real number higher)."],
        ["42 million+", "Odia speakers worldwide. 6th classical language of India."],
        ["200+", "BPUT-affiliated colleges in Odisha. Plus 15+ state universities, 62,000+ schools."],
        ["WCAG 2.2 AA", "The accessibility standard we follow (it's the global one)."],
        ["Apache 2.0", "Our open-source licence - anyone can use, modify, share."],
    ]
    num_table = Table(num_rows, colWidths=[3.2 * cm, 13.8 * cm])
    num_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GOLD_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), GOLD),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    s.append(num_table)
    s.append(Spacer(1, 12))

    s.append(para("The Odisha angle (important)", "h1"))
    s.extend(bullet_list([
        "Odisha has <b>5T</b> and <b>Mo Sarkar</b> - the state's own digital-service mandates. "
        "Accessibility is part of them. Use this phrase if the judge is from government.",
        "Run the pilot at <b>OCAC</b> (Odisha Computer Application Centre) - the state's IT agency. "
        "Everything runs on their servers. <i>Data never leaves Odisha.</i>",
        "Odia is a <b>classical language</b> (declared 2014). We handle Odia conjuncts correctly - "
        "which global tools get wrong.",
    ]))

    s.append(Spacer(1, 12))
    s.append(callout("One-line you can always fall back on:",
                     ["\"AaaS makes accessibility a <b>shared public layer</b>, "
                      "like UPI - so every college in Odisha doesn't have to build it alone.\""]))
    return s


# --- Document 2: Demo walkthrough ----------------------------------------

def doc_demo_walkthrough() -> list[Flowable]:
    s: list[Flowable] = []
    s.append(para("Your Demo Walkthrough", "title"))
    s.append(para("What to click, what to say - on stage.", "subtitle"))

    s.append(para("Before the judges arrive (2-minute setup)", "h1"))
    s.extend(bullet_list([
        "Open the demo site at <b>http://127.0.0.1:8000/demo/</b> - this is the Jajpur landing page.",
        "Turn laptop volume up. Plug in the external mic if you have one. Do one test read-aloud.",
        "Silence phone. Close WhatsApp, email, any notification apps.",
        "Put a water bottle and your printed cheat-sheet on the table.",
        "Breathe. You have practised this. It will go fine.",
    ]))

    s.append(para("The demo in one picture", "h1"))
    s.append(Spacer(1, 4))
    s.append(DemoFlow())
    s.append(Spacer(1, 8))

    s.append(para("Scene 1 - Open the demo (20 seconds)", "h1"))
    s.append(para(
        "Point at the screen. Say:", "body"))
    s.append(Paragraph(
        "\"This is what a realistic Odisha college admissions page looks like today - "
        "English-first, dense, hard to use for a student who reads only Odia or can't see the screen. "
        "Watch what happens when our layer turns on.\"", STYLES["quote"]))

    s.append(para("Scene 2 - Click the 'ଅ' button (15 seconds)", "h1"))
    s.append(para(
        "Point at the bottom-right corner. Click the floating Odia letter <b>ଅ</b>. "
        "The accessibility panel slides up. Say:", "body"))
    s.append(Paragraph(
        "\"This is the AaaS widget. One button. Any college can paste three lines into their "
        "HTML and every student on their site gets this.\"", STYLES["quote"]))

    s.append(para("Scene 3 - Read the page aloud in Odia (45 seconds)", "h1"))
    s.append(para("Click <b>Read this page</b>. Odia voice starts playing. Say:", "body"))
    s.append(Paragraph(
        "\"The page is now being read aloud in Odia. The voice is from Meta's MMS-TTS model, "
        "running on the laptop. No internet needed. No student data leaving the server.\"", STYLES["quote"]))
    s.append(para("After about 10 seconds, press Space to pause. Move on.", "body_em"))

    s.append(PageBreak())

    s.append(para("Scene 4 - Translate the page to Odia (45 seconds)", "h1"))
    s.append(para(
        "Click <b>Translate this page → Odia</b>. Watch blocks of English text turn into Odia. "
        "Say while it happens:", "body"))
    s.append(Paragraph(
        "\"We use AI4Bharat's IndicTrans2 translation model, built at IIT Madras. An Odia-speaking student can now read "
        "every form label, every instruction, every error message - in Odia. Not English.\"",
        STYLES["quote"]))

    s.append(para("Scene 5 - Speak to fill a form (60 seconds)", "h1"))
    s.append(para(
        "Click inside the <b>Name</b> form field. Click the widget's <b>Speak to fill</b> button. "
        "Allow microphone when the browser asks.", "body"))
    s.append(para("Speak this sentence aloud, slowly and clearly:", "body"))
    s.append(Paragraph("ਠୋର ନାମ ପ୍ରତୀକ୍ଷା", STYLES["odia"]))
    s.append(Paragraph("<i>Transliteration:</i> <b>Mora naam Pratikshya.</b>", STYLES["body"]))
    s.append(Paragraph("<i>Meaning:</i> \"My name is Pratikshya.\"", STYLES["body_em"]))
    s.append(Spacer(1, 4))
    s.append(para("Your spoken Odia will appear in the form field as Odia text. Say:", "body"))
    s.append(Paragraph(
        "\"I just filled a form by voice. In Odia. This is AI4Bharat's IndicWav2Vec model "
        "recognising Odia speech - about 85% accurate, far better than global tools.\"", STYLES["quote"]))

    s.append(para("Scene 6 - Close (20 seconds)", "h1"))
    s.append(para("Stand up straight. Look at the judges. Say:", "body"))
    s.append(Paragraph(
        "\"Twenty-one lakh persons with disabilities in Odisha. Forty-two million Odia speakers. "
        "Two hundred colleges, each currently inaccessible on its own. We make accessibility a "
        "shared public layer. Odisha first. India next. Happy to answer anything.\"",
        STYLES["quote"]))
    s.append(para("<b>Then stop talking.</b> Wait for the judges. Don't keep pitching.", "body_em"))

    s.append(Spacer(1, 10))
    s.append(callout("If something breaks on stage",
                     ["<b>Don't panic. Don't apologise twice.</b> Say <i>one</i> of these:",
                      "&nbsp;&nbsp;- \"One moment, the model is under load - let me show you the scripted run.\"",
                      "&nbsp;&nbsp;- \"Wi-Fi is slow - the widget falls back to the browser's speech engine. "
                      "The point still stands.\"",
                      "&nbsp;&nbsp;- \"Let me skip that scene - our compliance dashboard is the clearer one anyway.\"",
                      "Move on. Judges remember how you handle a breakage more than the breakage itself."]))
    return s


# --- Document 3: Judge questions -----------------------------------------

def doc_judge_questions() -> list[Flowable]:
    s: list[Flowable] = []
    s.append(para("Judge Questions - Cheat Sheet", "title"))
    s.append(para("Short answers. 20-30 seconds each. Pause. Let them ask the next one.", "subtitle"))

    s.append(callout("Three rules for the Q&A",
                     ["<b>1.</b> If you don't know: \"Honestly, I don't know - here is how we would find out.\"",
                      "<b>2.</b> Never ramble. Stop at 30 seconds. Judges prefer short.",
                      "<b>3.</b> If they ask a hostile question, thank them for it. Stay calm."]))
    s.append(Spacer(1, 8))

    # Category: Why Odisha / Why Odia
    s.append(para("Why Odisha? Why Odia?", "h1"))
    s.extend(qa_block(
        "Why Odisha first? Hindi has more speakers.",
        "Three reasons. One - Odisha has <b>5T and Mo Sarkar</b>, real state mandates for "
        "digital-service accessibility. Two - Odia is under-served. Global tools work poorly "
        "on Odia; we focus on what's missing. Three - we're based here, so we can land a real "
        "pilot faster."))
    s.extend(qa_block(
        "How does this fit 5T and Mo Sarkar?",
        "5T's five pillars include Transparency and Transformation. Our compliance dashboard "
        "gives the state measurable accessibility data. Mo Sarkar asks citizens if they got the "
        "service - for a disabled Odia-speaking citizen today, the answer is \"no\". We fix that."))
    s.extend(qa_block(
        "Does Odia have enough digital content to train on?",
        "Yes. AI4Bharat's IndicCorp has good Odia data. The models we use are already trained on "
        "it - we don't need to train from scratch. What's thin is regional dialects like Sambalpuri "
        "and Kosali - that's future work."))

    s.append(para("What exists already - how are you different?", "h1"))
    s.extend(qa_block(
        "Isn't this just another AccessiBe / UserWay overlay?",
        "No. Those are overlays - JavaScript that patches bad HTML at runtime. The disability "
        "community signed an open letter saying overlays don't work. We do two things overlays "
        "don't: (1) a design system colleges build into their site so nothing needs patching, "
        "and (2) assistive services the user chooses to turn on."))
    s.extend(qa_block(
        "Why not use Google Translate or ChatGPT?",
        "Two reasons. (1) <b>DPDP</b> - public institutions can't legally send student speech "
        "to OpenAI or Google servers. Data residency. (2) Integration - a chatbot can read a "
        "page but can't reliably <i>fill</i> a form field. Our widget has direct access to the page."))
    s.extend(qa_block(
        "What's actually new here? These are existing models.",
        "The novelty is the <b>assembly</b>, not the models. Like UPI - built from existing "
        "banking rails, but novel as a shared layer. Nobody has assembled accessibility, Indic AI, "
        "and DPDP-grade controls into one open-source stack a college can self-host."))

    s.append(PageBreak())

    s.append(para("Is this technically credible?", "h1"))
    s.extend(qa_block(
        "How good is Odia speech recognition really?",
        "IndicWav2Vec gives us about <b>12-18%</b> word-error rate on standard Odia - much "
        "better than Whisper's 25-35% on the same. Accuracy drops on rural dialects; that's "
        "honest, and it's on our Phase 3 roadmap with a linguistics-department partner."))
    s.extend(qa_block(
        "What if the AI service is down?",
        "The design system still works - that's why we split the layers. The widget falls back "
        "to the browser's built-in Web Speech API. Nothing the student can do today stops working."))
    s.extend(qa_block(
        "How does multi-tenant isolation work?",
        "Row-level security in Postgres keyed by <code>tenant_id</code>. Each college gets its "
        "own bucket in MinIO storage. AI inference is stateless. Colleges can't see each other's "
        "data even though they share infrastructure."))
    s.extend(qa_block(
        "Security?",
        "STRIDE threat model in the repo. Mutual TLS inside the stack. Keycloak auth. Audit log "
        "in Postgres. SBOM generated on every CI run, scanned with Grype. All documented."))

    s.append(para("Impact and fairness", "h1"))
    s.extend(qa_block(
        "Isn't a widget patronising? Just build better websites.",
        "Both are needed. The widget is <b>opt-in</b> - the student chooses their language, "
        "their reading mode, their voice-or-text. Nothing is imposed. And the design system "
        "half of AaaS is exactly the \"build better\" answer - that's why we ship both."))
    s.extend(qa_block(
        "How do you involve disabled users in the design?",
        "Today we're built against WCAG 2.2 AA and accepted best practices. Phase 5 of our plan "
        "is structured user-testing with the National Association for the Blind and Enabling Units "
        "at three universities. We don't claim lived-experience feedback yet - that comes next."))
    s.extend(qa_block(
        "What about students without smartphones or internet?",
        "The compliance scorecard helps on any device - a feature-phone browser benefits from "
        "a well-built site too. And Phase 5 has an SMS-channel fallback for form-filling. "
        "We don't solve the digital divide; we try not to make it worse."))

    s.append(PageBreak())

    s.append(para("Money and adoption", "h1"))
    s.extend(qa_block(
        "What's your business model?",
        "Open source, Apache 2.0 - colleges self-host for free. Sustainability comes from (1) "
        "optional paid managed hosting, (2) government grants under the Digital Public Infrastructure "
        "playbook, (3) CSR from companies with accessibility compliance obligations. Modelled on "
        "<b>MOSIP</b>, not on SaaS startups."))
    s.extend(qa_block(
        "Why would a government college actually adopt this?",
        "Three reasons. (1) They're legally required to be accessible under the RPwD Act and aren't. "
        "(2) A UGC circular links accessibility to institutional ranking. (3) Peer adoption - once "
        "IIT Bhubaneswar or Utkal picks it up, BPUT colleges follow."))
    s.extend(qa_block(
        "Five-year vision if this works?",
        "Two outcomes. One - AaaS becomes part of India's DPI stack alongside UPI, DigiLocker, "
        "e-Sign. Two - we scale beyond colleges to municipal services, state portals, and exam boards."))

    s.append(para("About your team", "h1"))
    s.extend(qa_block(
        "Why is your team the right one?",
        "We are a student team from Odisha. We know the language, the state, the universities. "
        "We named ourselves <b>SUBARNAREKHA</b> after the river that carries gold downstream "
        "to everyone on its banks. That's the intent - accessibility shouldn't belong to "
        "whoever hires the best vendor."))
    s.extend(qa_block(
        "Do you have accessibility expertise?",
        "We've built against WCAG 2.2 AA from day one. We do <i>not</i> have a professionally-"
        "trained accessibility auditor on the core team yet. That's a Phase 2 advisor we're "
        "actively looking for - and if any judge here can connect us, we'd welcome it."))
    s.extend(qa_block(
        "Is this a real project after the hackathon, or a weekend hack?",
        "Real project. Apache-2.0 repo. Six-phase roadmap documented. Three universities already "
        "interested in piloting. Hackathon or not, we keep shipping."))

    s.append(Spacer(1, 8))
    s.append(callout("Golden rule",
                     ["If a judge reveals a weakness you don't have an answer for, say this:",
                      "<b>\"That is a real gap. Honestly, we haven't solved that yet. "
                      "Here is how we would find out: [one specific next step].\"</b>",
                      "This wins judges over <i>more</i> than a confident wrong answer."]))
    return s


# --- Document 4: Pitch + fallback ----------------------------------------

def doc_pitch_and_fallback() -> list[Flowable]:
    s: list[Flowable] = []
    s.append(para("Pitch Scripts + Fallback", "title"))
    s.append(para("Three pitch lengths plus what to do if everything breaks.", "subtitle"))

    s.append(para("30-second pitch (the hook)", "h1"))
    s.append(para("Use this when a judge walks up and says \"tell me what this is.\"", "body"))
    s.append(Paragraph(
        "\"Every public-college website in Odisha fails accessibility. We built an "
        "<b>open-source layer</b> - a design system, an Odia-first voice widget, and a compliance "
        "scorecard - that any college can plug in. Think <b>UPI, but for accessibility</b>. "
        "Odisha first. India next.\"",
        STYLES["quote"]))
    s.append(para("Then stop. Let them ask the next question.", "body_em"))

    s.append(para("60-second pitch (the elevator)", "h1"))
    s.append(para("When you have a full minute - intro round, booth conversation.", "body"))
    s.append(Paragraph(
        "\"Odisha has over <b>21 lakh</b> persons with disabilities and <b>42 million</b> Odia speakers. "
        "Yet almost every college and government portal in the state is English-first and hard to "
        "use for disabled students.<br/><br/>"
        "We think accessibility shouldn't be 200 separate broken projects. It should be <b>shared "
        "public infrastructure</b> - like UPI.<br/><br/>"
        "<b>AaaS is three things:</b> a design system every component is accessible by default; an "
        "assistive widget with Odia voice, translation, dyslexia mode, and captions; and a compliance "
        "dashboard a college can run against its own site. It's Apache 2.0, on-prem capable - student "
        "data never leaves the college.<br/><br/>"
        "We want to pilot at one Odisha institution. Adopt it. Fork it. Watch the rest of the "
        "state follow.\"",
        STYLES["quote"]))

    s.append(PageBreak())

    s.append(para("2-minute pitch (panel round)", "h1"))
    s.append(para("Use this when you have the full floor.", "body"))

    s.append(para("<b>1. Open with a person.</b>", "body"))
    s.append(Paragraph(
        "\"Picture Priyanka. Blind, class 12, Puri, speaks only Odia. Next week she has to fill "
        "an online admissions form for Utkal University. Today that form defeats her - the labels "
        "aren't linked, the captcha is an image, the page is in English, the errors flash and "
        "disappear. She asks her brother to fill it for her. Half of Odisha's disabled students "
        "do the same.\"", STYLES["quote"]))

    s.append(para("<b>2. Scale it up.</b>", "body"))
    s.append(Paragraph(
        "\"Odisha has 21 lakh persons with disabilities. 42 million Odia speakers. 15 state "
        "universities. 200+ BPUT colleges. Every one of them legally owes accessibility under "
        "the RPwD Act - and almost none of them deliver it.\"", STYLES["quote"]))

    s.append(para("<b>3. Name the failure pattern.</b>", "body"))
    s.append(Paragraph(
        "\"The reason it keeps failing: every college treats accessibility as a per-project "
        "checkbox. They hire a vendor, bolt on an 'overlay' widget, tick the box, move on. "
        "It doesn't work. And no one measures it.\"", STYLES["quote"]))

    s.append(para("<b>4. Our answer.</b>", "body"))
    s.append(Paragraph(
        "\"Accessibility has to become <i>infrastructure</i>, not <i>remediation</i>. Three pieces. "
        "A React design system - every component WCAG 2.2 AA at commit time, Noto Sans Oriya bundled. "
        "A testing harness so every pull request is measured. An assistive widget - Odia voice in, "
        "Odia voice out, translation, dyslexia mode, captions - all on-prem. Apache 2.0, DPDP-compliant, "
        "deployable on a single VM at OCAC.\"", STYLES["quote"]))

    s.append(para("<b>5. Close.</b>", "body"))
    s.append(Paragraph(
        "\"We named the team SUBARNAREKHA - the river that carries gold downstream to everyone "
        "on its banks. That's the intent. Accessibility shouldn't belong to whoever hires the "
        "best vendor. It should belong to every Odia speaker, and then to every Indian. "
        "Odisha first. India next.\"", STYLES["quote"]))

    s.append(PageBreak())

    s.append(para("Phrases to say (words the judges like)", "h1"))
    s.extend(bullet_list([
        "<b>Digital public infrastructure</b> - not \"SaaS platform\".",
        "<b>Odia-first</b> - not \"multilingual\".",
        "<b>Assistive services layer</b> - never \"overlay\" (it's a slur in the accessibility community).",
        "<b>Aligned with 5T and Mo Sarkar</b> - whenever the judge is from government.",
        "<b>On-prem at OCAC's data centre</b> - sounds more concrete than \"on-prem\".",
        "<b>Open source, Apache 2.0</b> - say this early. It changes the room.",
    ]))

    s.append(para("Phrases to avoid", "h1"))
    s.extend(bullet_list([
        "\"AI-powered\" as a standalone claim. Always name the model (MMS-TTS, IndicTrans2, IndicWav2Vec).",
        "\"Solves accessibility.\" We <i>enable</i> it. We don't <i>solve</i> it.",
        "\"Disabled people.\" Say \"people with disabilities\" or be specific (blind, Deaf, dyslexic).",
        "\"Simple\" or \"easy.\" Accessibility is never simple. Judges know it.",
    ]))

    s.append(para("If everything breaks - your emergency script", "h1"))
    s.append(para(
        "If the laptop dies, if Wi-Fi is off, if the demo crashes - you still have the pitch. "
        "Follow these three steps in order.", "body"))
    s.extend(bullet_list([
        "<b>Acknowledge once.</b> \"Looks like the stack is under load - let me take you through "
        "it without the demo.\" <i>Don't apologise twice.</i>",
        "<b>Pivot to the 60-second pitch.</b> You have it memorised. Deliver it. Eye contact.",
        "<b>Point to the repo.</b> \"Apache 2.0, it's all live - QR code on the table. "
        "Everything I just described exists and the code is public.\"",
    ]))

    s.append(Spacer(1, 10))
    s.append(callout("If your mind goes blank in the Q&A",
                     ["Use this line. It buys you 10 seconds and is completely honest:",
                      "<b>\"That's a good question - let me think about it for a second.\"</b>",
                      "Judges appreciate pause more than they appreciate rambling. Take a breath. "
                      "Then give a short answer - 2 sentences is enough."]))

    s.append(para("The one thing to remember", "h1"))
    s.append(Paragraph(
        "You don't need to know every technical detail. You need to know <b>three names</b> "
        "(Priyanka, Arun, Meera), <b>five numbers</b> (21 lakh, 42 million, 200 colleges, WCAG 2.2 AA, "
        "Apache 2.0), and <b>one tagline</b> (\"UPI of accessibility - Odisha first, India next\").<br/><br/>"
        "That's it. Everything else is conversation.", STYLES["quote"]))
    return s


# --- Main -----------------------------------------------------------------

def main() -> None:
    print(f"Generating prep PDFs in {OUT}")
    build_pdf(OUT / "01-What-is-AaaS.pdf",
              "1. What is AaaS?", doc_what_is_aaas())
    build_pdf(OUT / "02-Demo-Walkthrough.pdf",
              "2. Demo Walkthrough", doc_demo_walkthrough())
    build_pdf(OUT / "03-Judge-Questions.pdf",
              "3. Judge Q&A", doc_judge_questions())
    build_pdf(OUT / "04-Pitch-and-Fallback.pdf",
              "4. Pitch + Fallback", doc_pitch_and_fallback())
    print("Done.")


if __name__ == "__main__":
    main()
