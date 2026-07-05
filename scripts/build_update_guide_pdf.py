"""Generate UPDATE-GUIDE.pdf for the friend — the step-by-step
how-to-update-from-previous-version doc. Ships inside the patch zip.

Run from repo root:
    python scripts/build_update_guide_pdf.py

Output:
    UPDATE-GUIDE.pdf (project root)
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "UPDATE-GUIDE.pdf"

# --- Palette ----------------------------------------------------------
INK = colors.HexColor("#0f1419")
MUTED = colors.HexColor("#5e6778")
ACCENT = colors.HexColor("#1a66cc")
GOOD = colors.HexColor("#2c7a52")
WARN = colors.HexColor("#c7444c")
SOFT_BG = colors.HexColor("#f3f6fa")
CODE_BG = colors.HexColor("#1b2530")
CODE_INK = colors.HexColor("#d8e0ea")

# --- Styles -----------------------------------------------------------
base = getSampleStyleSheet()
S = {
    "title": ParagraphStyle(
        "Title", parent=base["Title"],
        fontName="Helvetica-Bold", fontSize=22, leading=26,
        textColor=INK, spaceAfter=2,
    ),
    "subtitle": ParagraphStyle(
        "Subtitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=11, leading=14,
        textColor=MUTED, spaceAfter=16,
    ),
    "h1": ParagraphStyle(
        "H1", parent=base["Heading1"],
        fontName="Helvetica-Bold", fontSize=15, leading=19,
        textColor=ACCENT, spaceBefore=16, spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "H2", parent=base["Heading2"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=INK, spaceBefore=10, spaceAfter=4,
    ),
    "body": ParagraphStyle(
        "Body", parent=base["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14.5,
        textColor=INK, spaceAfter=6,
    ),
    "muted": ParagraphStyle(
        "Muted", parent=base["Normal"],
        fontName="Helvetica", fontSize=9.5, leading=13,
        textColor=MUTED, spaceAfter=6,
    ),
    "step_num": ParagraphStyle(
        "StepNum", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=colors.white, alignment=1,
    ),
    "step_title": ParagraphStyle(
        "StepTitle", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=11.5, leading=15,
        textColor=INK, spaceAfter=3,
    ),
    "step_body": ParagraphStyle(
        "StepBody", parent=base["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14.5,
        textColor=INK, spaceAfter=0,
    ),
    "code": ParagraphStyle(
        "Code", parent=base["Code"],
        fontName="Courier", fontSize=9.5, leading=13,
        textColor=CODE_INK, backColor=CODE_BG,
        leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=4,
        borderPadding=6,
    ),
}


def step(num: str, title: str, *body_paras) -> Table:
    """Two-column step row: coloured number box + body text block."""
    num_cell = Table(
        [[Paragraph(num, S["step_num"])]],
        colWidths=[12 * mm], rowHeights=[12 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, ACCENT),
        ]),
    )
    body_cell_contents = [Paragraph(title, S["step_title"]), *body_paras]
    tbl = Table(
        [[num_cell, body_cell_contents]],
        colWidths=[14 * mm, 146 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (0, 0), "TOP"),
            ("VALIGN", (1, 0), (1, 0), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
        ]),
    )
    return KeepTogether(tbl)


def code_block(text: str) -> Paragraph:
    """Monospaced code block with dark background."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Preserve line breaks inside the single Paragraph.
    safe = safe.replace("\n", "<br/>")
    return Paragraph(f"<font face='Courier'>{safe}</font>", S["code"])


def callout(tag: str, text: str, color) -> Table:
    tbl = Table(
        [[Paragraph(f"<b>{tag}</b> &nbsp; {text}", S["body"])]],
        colWidths=[160 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ]),
    )
    return tbl


def p(text: str) -> Paragraph:
    return Paragraph(text, S["body"])


def m(text: str) -> Paragraph:
    return Paragraph(text, S["muted"])


def bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(it, S["body"]), leftIndent=10) for it in items],
        bulletType="bullet", start="circle", leftIndent=14, bulletFontSize=7,
    )


def build():
    story = []

    # --- Header ---------------------------------------------------
    story.append(Paragraph("AaaS Update Guide", S["title"]))
    story.append(Paragraph(
        "How to apply the 2026-04-24 patch to your existing AaaS Portable install",
        S["subtitle"],
    ))

    story.append(callout(
        "WHY THIS GUIDE",
        "You already have a working AaaS Portable install. This update is a tiny "
        "patch (~260 KB) that refreshes the widget and adds a new auto-heal system "
        "for AI models. No re-install needed — just 5 quick steps below.",
        ACCENT,
    ))
    story.append(Spacer(1, 12))

    # --- What's new -----------------------------------------------
    story.append(Paragraph("What's new in this update", S["h1"]))
    story.append(bullets([
        "<b>Odia streaming</b> — long paragraphs start speaking in ~1 second instead of ~5.",
        "<b>Mic &rarr; English</b> — speak Odia or Hindi; the form field gets English. Digits convert automatically (୨୦୨୫ &rarr; 2025).",
        "<b>Translation safety net</b> — if translate can't produce real English, the form stays empty with a red error (no more silent Odia-in-English-form).",
        "<b>Smart hover-to-speak</b> — speaks the button's <i>visible</i> text, not its hidden accessibility annotation. Icon buttons still fall back to the annotation correctly.",
        "<b>Auto-heal models</b> — NEW. A one-click script checks every AI model and downloads anything missing. If a gated model is unavailable, it configures a clean fallback.",
        "<b>DevTools diagnostics</b> — hover logs <font face='Courier' size='9'>[AaaS/hover]</font> every element so any remaining issues are easy to report.",
    ]))

    # --- Update in 6 steps ----------------------------------------
    story.append(Paragraph("Update in 6 steps", S["h1"]))

    story.append(step(
        "1", "Close the running demo",
        p("If you have the four AaaS service terminal windows open, close each "
          "of them by clicking the <b>X</b>. Leaving them open is fine too &mdash; "
          "widget files are only read when pages load."),
    ))

    story.append(step(
        "2", "Unzip this update",
        p("Extract the update zip into the <b>same parent folder</b> that contains "
          "your existing <font face='Courier' size='9.5'>AaaS-Portable\\</font> folder."),
        p("<b>Example:</b> if your install is at <font face='Courier' size='9.5'>C:\\AaaS\\AaaS-Portable\\</font>, "
          "extract into <font face='Courier' size='9.5'>C:\\AaaS\\</font>. When Windows asks, "
          "click <b>Yes to All</b> to overwrite existing files."),
    ))

    story.append(step(
        "3", "Run the auto-heal (NEW)",
        p("Double-click <b>ENSURE-READY.bat</b> inside your <font face='Courier' size='9.5'>AaaS-Portable\\</font> folder."),
        p("It verifies every AI model is present and healthy. If anything's "
          "missing, it downloads it automatically. Fast (~5 seconds) when everything's "
          "intact; up to a few minutes on first run if models need fetching."),
        p("Expected output for a healthy install:"),
        code_block(
            "[OK]   MMS-TTS Odia\n"
            "[OK]   MMS-TTS Hindi\n"
            "[OK]   MMS-TTS English\n"
            "[OK]   IndicTrans2 en->indic (200M)\n"
            "[OK]   IndicTrans2 indic->en (200M)\n"
            "[OK]   IndicWav2Vec Odia\n"
            "READY — safe to run RUN-DEMO.bat."
        ),
    ))

    story.append(step(
        "4", "Reload the browser extension",
        p("Chrome caches content scripts, so a refresh alone isn't enough."),
        bullets([
            "Open <font face='Courier' size='9.5'>chrome://extensions</font> in Chrome or Edge.",
            "Find <b>AaaS Accessibility Companion (Odisha)</b>.",
            "Click the circular <b>Reload</b> icon on the extension's tile.",
        ]),
    ))

    story.append(step(
        "5", "Refresh demo tabs",
        p("Press <b>F5</b> (or <b>Ctrl</b>+<b>R</b>) on any open AaaS demo page. "
          "The updated widget.js only takes effect after a full reload."),
    ))

    story.append(step(
        "6", "Start the demo",
        p("Double-click <b>RUN-DEMO.bat</b>. Four terminal windows open, one per service. "
          "After ~15 seconds the demo landing page opens in your browser at "
          "<font face='Courier' size='9.5'>http://127.0.0.1:8000/demo/</font>."),
    ))

    # --- Verify ---------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Verify the update worked", S["h1"]))

    story.append(Paragraph("Three quick smoke tests &mdash; should take under a minute total.", S["muted"]))

    story.append(Paragraph("Test 1 — Odia streaming (1 minute)", S["h2"]))
    story.append(p(
        "Open a demo page. In the widget panel (bottom-right blue button), set "
        "language to <b>Odia</b>. Click <b>Read this page</b>. You should hear the "
        "first sentence within about one second. Before this update, long paragraphs "
        "waited ~5 seconds before anything played."
    ))

    story.append(Paragraph("Test 2 — Mic fills English (30 seconds)", S["h2"]))
    story.append(p(
        "Open the Utkal University demo. Click into the <b>Name</b> text field. "
        "Click the mic button in the widget. Say <i>my name is Priya</i> in Odia "
        "(e.g., <b>ମୋର ନାମ ପ୍ରିୟା</b>). Click the mic again to stop."
    ))
    story.append(p(
        "Expected: the widget's transcript strip shows your Odia speech. The form "
        "field receives the English translation. The status line reads "
        "<font face='Courier' size='9.5'>Filled field (or &rarr; en)</font>."
    ))

    story.append(Paragraph("Test 3 — Smart hover (30 seconds)", S["h2"]))
    story.append(p(
        "In the widget panel, toggle <b>Hover to speak</b> on. Hover any button "
        "or link on the demo page. The widget should speak exactly the visible "
        "text you're pointing at &mdash; not an aria-label or hidden annotation."
    ))

    # --- Troubleshooting ------------------------------------------
    story.append(Paragraph("If something goes wrong", S["h1"]))

    story.append(Paragraph("\"ENSURE-READY.bat: .venv-portable not found\"", S["h2"]))
    story.append(p(
        "You've never run the full SETUP-FRIEND.bat. Do that first (5–10 minutes on a "
        "fresh laptop), then come back to step 3 above."
    ))

    story.append(Paragraph("Auto-heal fails to download a model", S["h2"]))
    story.append(bullets([
        "Check your internet connection and re-run <b>ENSURE-READY.bat</b>.",
        "For the gated AI4Bharat Odia STT model, see the next section.",
        "If you're on a corporate firewall, try a personal hotspot.",
    ]))

    story.append(Paragraph("Widget still behaves like the old version", S["h2"]))
    story.append(p(
        "Chrome aggressively caches content scripts. If step 4 didn't work, try:"
    ))
    story.append(bullets([
        "Close the demo tab completely (right-click &rarr; Close tab), then reopen.",
        "In <font face='Courier' size='9.5'>chrome://extensions</font>, toggle the AaaS Companion off and on.",
        "As a last resort: remove the extension, then re-add it via <b>Load unpacked</b> pointing at <font face='Courier' size='9.5'>AaaS-Portable\\apps\\extension\\</font>.",
    ]))

    story.append(Paragraph("Mic records but no audio plays after", S["h2"]))
    story.append(p(
        "Chrome blocks audio until you interact with the page. Click anywhere on "
        "the page first, then try the mic."
    ))

    story.append(Paragraph("Status shows \"Transcribed (or) — translation unavailable\"", S["h2"]))
    story.append(p(
        "This is expected if the translate service is offline or hit a phrase it "
        "can't translate cleanly. The form is deliberately left empty instead of "
        "filled with Odia. Close the Translate terminal window, re-run RUN-DEMO.bat."
    ))

    # --- Optional: real Odia STT ----------------------------------
    story.append(Paragraph("Optional: enable real Odia speech recognition", S["h1"]))
    story.append(p(
        "Without this setup, the mic uses a mock engine that returns canned phrases "
        "regardless of what you say. To get real Odia transcription:"
    ))
    story.append(step(
        "A", "Create a HuggingFace account",
        p("Go to <font face='Courier' size='9.5'>https://huggingface.co</font> and sign up. Free."),
    ))
    story.append(step(
        "B", "Request model access",
        p("Visit <font face='Courier' size='9.5'>huggingface.co/ai4bharat/indicwav2vec-odia</font>. "
          "Click <b>Agree and access repository</b>. Access is auto-approved immediately."),
    ))
    story.append(step(
        "C", "Create a token",
        p("At <font face='Courier' size='9.5'>huggingface.co/settings/tokens</font>, click "
          "<b>Create new token</b>. Name it anything, type <b>Read</b>. Copy the "
          "<font face='Courier' size='9.5'>hf_...</font> string &mdash; you only see the full value once."),
    ))
    story.append(step(
        "D", "Set the token + re-run auto-heal",
        p("Open a Command Prompt, paste:"),
        code_block("set HF_TOKEN=hf_your_token_here\nENSURE-READY.bat"),
        p("The script downloads the Odia STT model (~870 MB) and flips the STT "
          "service from mock to real. Run RUN-DEMO.bat and the mic now transcribes "
          "what you actually said."),
    ))

    # --- Footer ---------------------------------------------------
    story.append(Spacer(1, 12))
    story.append(callout(
        "NEED MORE HELP",
        "See <font face='Courier' size='9.5'>README-FOR-FRIEND.md</font> in the AaaS-Portable folder for "
        "full install and usage docs. Browser DevTools (F12 &rarr; Console tab) "
        "show diagnostic lines starting with <font face='Courier' size='9.5'>[AaaS/hover]</font> that make "
        "debugging easy to report back.",
        GOOD,
    ))

    # --- Build ----------------------------------------------------
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="AaaS Update Guide", author="Team SUBARNAREKHA",
    )
    doc.build(story)
    print(f"Wrote {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
