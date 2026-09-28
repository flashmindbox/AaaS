"""Render the anticipated judge Q&A to a print-ready A4 PDF.

    python pitch/build_qna.py        # writes pitch/AaaS-Judge-QnA.html + .pdf

Content mirrors hackathon/JUDGE_QA.md (the longer speaking notes). Keep every
claim here true of the shipped system — see "Never say" at the bottom.
"""
import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
CHROME = pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

SECTIONS = [
    ("Why this, why Odisha", [
        ("Why Odisha first? Hindi has more speakers.",
         "Three reasons. Odia is badly served by global tools, so that is where the real gap is. Odisha has an "
         "active digital-service mandate in 5T and Mo Sarkar. And this is our state, so this is where we can "
         "credibly land a pilot. <strong>Odia-first is the hard problem; the engines already cover 22 Indian "
         "languages for what comes next.</strong>"),
        ("Doesn't Bhashini already do this?",
         "Bhashini is the language-engine layer: translation and speech as APIs. AaaS is the accessibility "
         "product on top of it: guided voice form-filling, name transliteration, scanned notices read side by side, "
         "voice navigation without dead ends. <strong>Bhashini gives India voices; AaaS gives Odisha's citizens "
         "hands, eyes and ears. We could plug Bhashini in as an engine tomorrow.</strong> "
         "<em>If they ask “so you're just a UI?”:</em> so is UPI: the rails existed, the product made a billion "
         "people use them."),
        ("Why not Chrome's read-aloud, Google Translate and a screen reader?",
         "An elderly Odia-speaking citizen will not combine three tools. None of them speak Odia numbers, read "
         "scanned circulars into Odia, or fill a form by voice, and most send data to the cloud. <strong>We put "
         "those pieces together as one button, in Odia, running offline.</strong>"),
        ("Isn't this just an accessibility “overlay” like accessiBe?",
         "Overlays claim a script makes a site “compliant” and are rightly criticised for it. <strong>We claim "
         "nothing about the host site. We give the citizen a working way through it, and we are open source, "
         "self-hosted and auditable.</strong>"),
    ]),
    ("What we built", [
        ("Did you build this yourself?",
         "<em>Answer truthfully, in your own words:</em> what you designed and decided, what you wrote, and "
         "who helped (guide teacher, open-source models, any AI coding tools). Judges reward honesty. "
         "<strong>Show ownership by knowing the architecture and the hard problems below cold. That proves "
         "understanding better than any claim.</strong>"),
        ("Which AI models do you run?",
         "Four open-source engines, all on this laptop: <b>IndicWav2Vec</b> (AI4Bharat) for Odia speech-to-text, "
         "<b>IndicTrans2</b> (AI4Bharat) for translation, <b>MMS-TTS</b> (Meta) for Odia, Hindi and English "
         "voices, and <b>Tesseract</b> for OCR. Easy Read is our own rule engine. <strong>No cloud APIs, no "
         "chatbot.</strong>"),
        ("Isn't it just a wrapper around existing models? What's hard?",
         "The models are commodities; the product is everything between the citizen and the model. The Odia voice "
         "model is <b>silent on digits</b>, so we turn numbers into Odia words. The speech model writes English words "
         "<b>phonetically in Odia script</b>, so we match links by sound. Word-for-word translation turns the name "
         "Purnnachandra into <b>“full moon”</b>, so we transliterate names. The translator also <b>changed dates</b> "
         "on long notices (2026 came back as 2021), so we hide numbers from it and put them back afterwards. "
         "<strong>None of that ships in any model.</strong>"),
        ("Why rules for Easy Read, not an AI chatbot?",
         "A government notice with an invented deadline is worse than no notice. Rules are predictable, "
         "auditable line by line, and run offline on an ordinary laptop. <strong>They cannot make up facts.</strong>"),
        ("How accurate are the voice, translation and OCR?",
         "Good on clear speech and printed notices; weaker on noisy rooms and poor scans. Handwriting does not "
         "work. That is why voice commands offer choices instead of guessing, forms ask again, and documents are "
         "shown <b>next to the original</b>. <strong>An imperfect Odia reading beats an English page the citizen "
         "cannot use at all, and the original is always on screen.</strong>"),
    ]),
    ("Deployment, privacy and cost", [
        ("What does a website have to change?",
         "One line of code (a script tag). The widget is about 0.5 MB, has no dependencies, and is isolated so it "
         "cannot break the page. For sites that haven't adopted it, our Chrome extension adds the same button. "
         "<strong>We ran it on the real jajpur.odisha.gov.in and ssepd.odisha.gov.in.</strong>"),
        ("Where does citizen data go? (DPDP Act 2023)",
         "To the institution's own server, for example at OCAC, and nowhere else. Audio is processed in memory "
         "and discarded, and we keep no accounts and log no content: only usage counts per feature. "
         "<strong>Data stays in Odisha.</strong>"),
        ("Does adding this make a website WCAG-compliant?",
         "<strong>No, and we deliberately do not claim that.</strong> Real compliance means fixing the site. "
         "AaaS gives citizens a way through today while that work happens."),
        ("Will it scale? How fast is it?",
         "Four stateless services behind one gateway, so scaling is standard server work. Repeated pages and "
         "sentences come from cache, including a translation cache that survives restarts. "
         "<strong>Don't quote numbers: show it. First use takes seconds; repeats are instant.</strong>"),
        ("What if a model fails, or there is no internet?",
         "Everything runs offline on the laptop. Each service has a backup mode, and the widget shows which "
         "engine answered. <strong>It degrades honestly instead of dying.</strong>"),
        ("Who pays? How is it sustained?",
         "The state, once, for every department: one deployment at OCAC serves every portal. It is open source "
         "(Apache-2.0), so there is no lock-in, any IT firm can run it, and other states adopt it free. "
         "<strong>Like UPI: shared rails, adoption first; support and hosting sustain it.</strong>"),
    ]),
    ("Honest scope", [
        ("Does it do sign language?",
         "Not yet, and we say so. A three.js concept exists in the repo, but a half-good avatar would hurt deaf "
         "users more than help. <strong>We chose to perfect voice, reading and forms first.</strong>"),
        ("Which languages? What does adding one cost?",
         "Odia, Hindi and English today. The engines support most scheduled Indian languages, so a new language "
         "is configuration plus native-speaker testing. <strong>A new language, not a new product.</strong>"),
        ("What's next after the hackathon?",
         "A pilot on one district portal (Jajpur) and one board site (BSE Odisha); a native-speaker review of the "
         "Odia wording; and Bhashini as an alternative engine. <strong>Our ask: give us one site.</strong>"),
    ]),
]

NEVER = [
    "Models we don't run: Whisper, IndicConformer, Piper, NLLB, or any LLM / chatbot",
    "An exam module (cut) or a working sign-language avatar (concept only)",
    "That a site becomes “WCAG-compliant”",
    "Latency or accuracy numbers from memory: demonstrate instead",
    "“21 lakh disabled people in Odisha” (unverified). Use Census 2011: 2.68 crore disabled people in India",
]

qa_html, n = "", 0
for sec, items in SECTIONS:
    qa_html += f'<h2>{sec}</h2>\n'
    for q, a in items:
        n += 1
        qa_html += f'<div class="qa"><p class="q"><span class="num">Q{n}</span>{q}</p><p class="a">{a}</p></div>\n'
never_html = "".join(f"<li>{x}</li>" for x in NEVER)

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>AaaS Judge Q&amp;A</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;0,800;1,400&family=Noto+Sans+Oriya:wght@600;700&display=swap" rel="stylesheet">
<style>
@page {{ size:A4; margin:14mm 15mm 15mm;
  @bottom-left {{ content:"Team SUBARNAREKHA · AaaS · Judge Q&A"; font:7.5pt 'Noto Sans',sans-serif; color:#6b7280; }}
  @bottom-right {{ content:counter(page) " / " counter(pages); font:7.5pt 'Noto Sans',sans-serif; color:#6b7280; }} }}
:root {{ --ink:#16202e; --muted:#4b5566; --line:#d5dbe5; --brand:#1d3a8a; --soft:#e8edf8; --amber:#b45309; --amber-soft:#fdf3e2; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; background:#fff; }}
body {{ font-family:'Noto Sans','Nirmala UI',sans-serif; color:var(--ink); font-size:9.3pt; line-height:1.42;
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
.head {{ background:var(--brand); color:#fff; border-radius:3px; padding:4.5mm 6mm; display:flex; align-items:center; gap:5mm; margin-bottom:3mm; }}
.logo {{ width:14mm; height:14mm; border-radius:50%; background:#fff; color:var(--brand); display:grid; place-items:center;
  font-family:'Noto Sans Oriya','Nirmala UI',sans-serif; font-size:22pt; font-weight:700; flex:none; }}
.head h1 {{ margin:0; font-size:17pt; line-height:1.15; }}
.head .sub {{ font-size:8.6pt; color:#dbe4f7; margin-top:1mm; }}
.intro {{ font-size:8.8pt; color:var(--muted); margin:0 0 1mm; }}
h2 {{ font-size:10.5pt; color:var(--brand); text-transform:uppercase; letter-spacing:.07em; margin:3.6mm 0 1.4mm;
  padding-bottom:1mm; border-bottom:1.2pt solid var(--brand); break-after:avoid; }}
.qa {{ break-inside:avoid; margin:0 0 2.1mm; }}
.q {{ margin:0 0 .6mm; font-weight:700; font-size:9.8pt; display:flex; gap:2mm; }}
.num {{ color:#fff; background:var(--amber); border-radius:2px; font-size:7.8pt; padding:.3mm 1.3mm; height:fit-content; margin-top:.5mm; flex:none; }}
.a {{ margin:0 0 0 9mm; }}
.a strong {{ color:var(--brand); }}
.a em {{ color:var(--amber); font-style:normal; font-weight:600; }}
.never {{ margin-top:4mm; background:var(--amber-soft); border-left:2.5pt solid var(--amber); border-radius:2px; padding:3mm 4.5mm; break-inside:avoid; }}
.never b {{ color:var(--amber); }}
.never ul {{ margin:1mm 0 0; padding-left:5mm; }}
.never li {{ margin-bottom:.6mm; }}
</style></head><body>
<div class="head"><div class="logo">ଅ</div><div>
  <h1>Judge Q&amp;A: prepared answers</h1>
  <div class="sub">AaaS · Accessibility as a Service &nbsp;·&nbsp; Team SUBARNAREKHA &nbsp;·&nbsp; Pratikshya Padhi, OAV Jamdhar &nbsp;·&nbsp; Odiapreneur 3.0</div>
</div></div>
<p class="intro">Presenter prep. Keep answers to 15–30 seconds; the <strong style="color:#1d3a8a">bold line</strong> is the point to land. If you don't know, say so: “I don't know yet; here is how we'd find out.”</p>
{qa_html}
<div class="never"><b>Never say</b><ul>{never_html}</ul></div>
</body></html>"""

out = REPO / "pitch" / "AaaS-Judge-QnA.html"
out.write_text(HTML, encoding="utf-8")
pdf = out.with_suffix(".pdf")
subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", out.as_uri()],
               check=True, capture_output=True)
print("wrote", pdf, f"({n} questions)")
