"""Combine the guidebook chapters into one printable HTML file.

Extracts each chapter's <section class="sheet"> (and any chapter-specific
<style> block, e.g. ch06's dyslexia demo) and concatenates them, forcing a
page break before each chapter. Output: aaas-guidebook.html — render that to
PDF with headless Chrome.
"""
import re, pathlib, sys

GB = pathlib.Path(__file__).resolve().parent
ORDER = [
    "index.html",
    "01-the-problem.html", "02-architecture.html", "03-the-six-components.html",
    "04-reaching-real-websites.html", "05-how-the-ai-works.html",
    "06-odia-first-design.html", "07-security-privacy-a11y.html",
    "08-running-the-demo.html", "09-pitch-and-judge-qa.html",
]

styles, sheets = [], []
for name in ORDER:
    html = (GB / name).read_text(encoding="utf-8")
    for st in re.findall(r"<style>(.*?)</style>", html, re.S):
        styles.append(st.strip())
    m = re.search(r'(<section class="sheet">.*?</section>)', html, re.S)
    if not m:
        sys.exit(f"[combine] no .sheet found in {name}")
    sheets.append(f"<!-- {name} -->\n" + m.group(1))

combined = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AaaS — Accessibility as a Service · Complete Guidebook</title>
<link rel="stylesheet" href="assets/guide.css">
<style>
  /* each chapter starts on a fresh A4 page */
  .sheet { break-before: page; page-break-before: always; }
  .sheet:first-of-type { break-before: auto; page-break-before: avoid; }
  /* chapter-specific styles collected from the source files */
%s
</style>
</head>
<body>
%s
</body>
</html>
""" % ("\n".join(styles), "\n\n".join(sheets))

out = GB / "aaas-guidebook.html"
out.write_text(combined, encoding="utf-8")
print(f"[combine] wrote {out} ({out.stat().st_size:,} bytes, {len(sheets)} chapters)")
