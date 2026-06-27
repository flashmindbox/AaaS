"""Render the anticipated judge Q&A to a print-ready A4 PDF (Odisha theme).

Builds a self-contained HTML (chakra + Odia font embedded as base64) and lets a
separate Chrome --print-to-pdf pass rasterise it. Content is the prepared Q&A.
"""
import base64, pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
AST = REPO / "pitch" / "assets"
CHAKRA = base64.b64encode((AST / "chakra_gold.png").read_bytes()).decode()
FONTB = base64.b64encode(
    (REPO / "apps" / "widget" / "src" / "fonts" / "noto-sans-oriya-400-subset.woff2").read_bytes()
).decode()

SECTIONS = [
    ("Differentiation", [
        ("Isn't this just another accessibility overlay (accessiBe / UserWay)?",
         "Overlays are site-owner products: English-centric, cloud-based, proprietary, and widely "
         "criticised for falsely claiming a script makes a site “compliant.” We are the "
         "opposite on every count. <strong>AaaS is user-controlled (a browser extension that works "
         "on any site), Indian-language-first, on-device, open-source, and honest — an "
         "assistive layer plus an API toolkit, not a compliance band-aid.</strong>"),
        ("Why not just use Google Translate plus a normal screen reader?",
         "A blind Odia-speaking farmer will not stitch together three separate tools. AaaS is one "
         "button that reads aloud, translates and fills forms by voice — in Odia — on any "
         "page, including the many that mainstream screen readers handle poorly because they are "
         "built English-first. <strong>We package fragmented capabilities into one accessible, "
         "Indian-language experience.</strong>"),
        ("Why not simply use Bhashini, the Government of India's language platform?",
         "Bhashini is an excellent translation / ASR backend — and we are complementary, not "
         "competing. AaaS is the accessibility delivery layer (widget, cross-site extension, "
         "screen-reader, exam mode, dyslexia rendering) on top of it. <strong>Our translation "
         "engine is pluggable — we can run on Bhashini, AI4Bharat IndicTrans2, or fully "
         "on-device — so we ride India's own rails, not against them.</strong>"),
        ("What stops Google or Microsoft from simply building this?",
         "Nothing — but they build horizontal, English-first products, not Odia-first public "
         "infrastructure that a state can audit and self-host. <strong>Our moat is focus, openness "
         "and sovereignty: an open, Indian-language accessibility stack the government owns rather "
         "than rents.</strong>"),
    ]),
    ("Technical", [
        ("How accurate is the Odia voice and the translation, and what about errors?",
         "The voice is Meta's MMS-TTS (a VITS model; Odia is a first-class supported language) and "
         "translation is Indic-tuned (AI4Bharat IndicTrans2). This is assistive output, not legal "
         "text — and the user always retains the original on screen. <strong>A slightly "
         "imperfect Odia reading is incomparably better than an English page the citizen cannot use "
         "at all.</strong>"),
        ("How does it work on sites that don't cooperate, or that block scripts via CSP?",
         "The browser extension injects independently of the website, and the AI runs on-device in "
         "a sandboxed WebAssembly worker, so it is not blocked by the page's Content-Security-"
         "Policy. <strong>We demonstrated it working live on Wikipedia — one of the strictest-"
         "CSP sites on the web.</strong>"),
        ("Is on-device AI fast enough on a low-end laptop?",
         "The first use loads the model (a few seconds, shown as a clear status), after which it is "
         "cached and responsive, and results are cached across page reloads. If a device is too "
         "weak, the very same engines run on the gateway as a fallback. <strong>Same voice — "
         "two places to run it.</strong>"),
        ("The extension injects into every website — isn't that a security and privacy risk?",
         "It requests minimal permissions, renders its UI inside an isolated Shadow DOM that cannot "
         "read the host page's data, and <strong>processes voice and text on-device — nothing "
         "is sent to a server.</strong> Because it is open-source, any security team (including the "
         "government's) can audit exactly what it does."),
    ]),
    ("Trust & Compliance", [
        ("Does installing this make a website WCAG- or legally compliant?",
         "<strong>No — and we deliberately do not claim that</strong> (that false promise is "
         "precisely why overlays face lawsuits). We help institutions meet the RPwD Act 2016, GIGW "
         "3.0 and WCAG 2.1, and we log WCAG results as evidence — but genuine compliance is "
         "built with our API, never faked with a script."),
        ("Where does citizen data go? (DPDP Act 2023)",
         "For the extension, voice and page text stay on the device. For the gateway, processing is "
         "in-country and self-hostable. <strong>No citizen data leaves the country or touches a "
         "foreign cloud — DPDP Act 2023 by design.</strong>"),
    ]),
    ("Adoption & Sustainability", [
        ("It is open-source — how do you sustain it?",
         "An open core (free for institutions to deploy, as a public good), sustained through "
         "deployment and integration support, hosting, custom language and voice packs, and "
         "government / CSR grants. <strong>The goal is public infrastructure, like UPI — "
         "adoption first, sustainability through the services around it.</strong>"),
        ("How would a government actually adopt this?",
         "Begin with a single department or university portal as a pilot — no rebuild needed, "
         "as it works on the existing site. Prove usage and WCAG evidence, then scale state-wide. "
         "<strong>Our ask is exactly that: give us one site.</strong>"),
    ]),
    ("Roadmap & Honesty", [
        ("Is the sign-language avatar working today?",
         "We are upfront: <strong>it is our flagship next milestone, currently in development</strong> "
         "— text → Indian Sign Language gloss → 3D avatar, built on the official "
         "ISLRTC ISL dictionary. We present the vision because no competitor even attempts sign "
         "language."),
        ("What did you actually build, versus use off the shelf?",
         "We stand openly on open models — Meta MMS-TTS, OpenAI Whisper, AI4Bharat IndicTrans2. "
         "<strong>What we built is the platform: the multi-tenant API gateway, the drop-in widget, "
         "the cross-site browser extension, the on-device WebAssembly pipeline, the accessible exam "
         "module, and the admin dashboard</strong> — turning open models into deployable public "
         "accessibility infrastructure."),
    ]),
]

NOTE = (
    "Translation engine: the deck presents AI4Bharat IndicTrans2; the live demo currently runs on "
    "Google Translate for speed and coverage. If asked directly, the honest line is — "
    "“the engine is pluggable; the demo uses Google for reliability, production targets "
    "IndicTrans2 / Bhashini for sovereignty.” Never present the demo as IndicTrans2."
)

qa_html = ""
n = 0
for sec, items in SECTIONS:
    qa_html += f'<div class="sec"><span class="seclabel">{sec}</span></div>\n'
    for q, a in items:
        n += 1
        qa_html += (f'<div class="qa"><p class="q"><span class="num">Q{n}.</span> {q}</p>'
                    f'<p class="a">{a}</p></div>\n')

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'OdiaE'; src:url(data:font/woff2;base64,{FONTB}) format('woff2'); }}
@page {{ size:A4; margin:16mm 15mm 18mm 15mm; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; padding:0; font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif; color:#2a2118; }}
.odia {{ font-family:'OdiaE','Noto Sans Oriya',sans-serif; }}
.header {{ background:linear-gradient(100deg,#7c1428,#a8213b 60%,#ef7d16); border-radius:10px;
  border:2px solid #e6b93f; padding:14px 18px; display:flex; align-items:center; gap:16px; margin-bottom:14px; }}
.header img {{ width:64px; height:64px; }}
.htext h1 {{ margin:0; color:#fff3da; font-size:21px; letter-spacing:.2px; }}
.htext .sub {{ color:#ffe6bf; font-size:11.5px; margin-top:3px; }}
.htext .od {{ color:#ffe6bf; font-size:13px; margin-top:2px; font-weight:600; }}
.intro {{ font-size:11px; color:#7a5a38; margin:0 2px 12px; font-style:italic; }}
.sec {{ margin:14px 0 6px; border-bottom:2px solid #e6b93f; padding-bottom:3px; }}
.seclabel {{ color:#8d1b2f; font-weight:800; font-size:13px; letter-spacing:1.5px; text-transform:uppercase; }}
.qa {{ break-inside:avoid; page-break-inside:avoid; margin:9px 0 11px; }}
.q {{ margin:0 0 4px; color:#7c1428; font-weight:700; font-size:12.6px; line-height:1.3; }}
.num {{ color:#c9952a; }}
.a {{ margin:0; font-size:11.6px; line-height:1.5; color:#33291d; }}
.a strong {{ color:#7c1428; }}
.note {{ margin-top:16px; background:#fdf3dd; border:1.5px solid #c9952a; border-left:6px solid #ef7d16;
  border-radius:8px; padding:10px 14px; font-size:11px; line-height:1.5; color:#33291d; break-inside:avoid; }}
.note b {{ color:#8d1b2f; }}
.foot {{ position:fixed; bottom:6mm; left:15mm; right:15mm; display:flex; justify-content:space-between;
  font-size:9px; color:#a08a63; border-top:1px solid #e0cfa0; padding-top:3px; }}
</style></head><body>
<div class="foot"><span>Team SUBARNAREKHA &nbsp;·&nbsp; Accessibility as a Service (AaaS)</span>
<span>Smart Odisha Hackathon '25 &nbsp;·&nbsp; Jajpur, Odisha</span></div>
<div class="header">
  <img src="data:image/png;base64,{CHAKRA}"/>
  <div class="htext">
    <h1>Anticipated Judge Q&amp;A &mdash; with prepared responses</h1>
    <div class="sub">Accessibility as a Service (AaaS) &nbsp;·&nbsp; Team SUBARNAREKHA &nbsp;·&nbsp; Smart Odisha Hackathon '25, Jajpur</div>
    <div class="od odia">ସମସ୍ତଙ୍କ ପାଇଁ ସୁଗମ ସେବା</div>
  </div>
</div>
<p class="intro">Likely questions from the evaluation panel, with concise, defensible answers. The bold line in each answer is the point to land.</p>
{qa_html}
<div class="note"><b>Internal prep note (not for the slides):</b> {NOTE}</div>
</body></html>"""

out = REPO / "pitch" / "AaaS-Judge-QnA.html"
out.write_text(HTML, encoding="utf-8")
print("wrote", out, f"({len(HTML):,} bytes, {n} questions)")
