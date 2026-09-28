"""Render the presenter Markdown notes to printable A4 PDFs (via headless Chrome).

    python hackathon/md2pdf.py DEMO_SCRIPT.md:2-Demo-Script.pdf ...

Each argument is ``source.md:output.pdf`` relative to this folder.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

CSS = """
@page { size: A4; margin: 16mm 17mm 16mm;
  @bottom-left { content: "Team SUBARNAREKHA · AaaS"; font: 7.5pt 'Noto Sans', sans-serif; color: #6b7280; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt 'Noto Sans', sans-serif; color: #6b7280; }
}
:root { --ink:#16202e; --muted:#4b5566; --line:#d5dbe5; --brand:#1d3a8a; --soft:#e8edf8; --amber:#b45309; --amber-soft:#fdf3e2; }
html, body { background:#fff; margin:0; }
body { font-family:'Noto Sans','Noto Sans Oriya','Nirmala UI',sans-serif; color:var(--ink);
  font-size:10pt; line-height:1.5; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.doc-head { display:flex; align-items:center; gap:4mm; border-bottom:1.4pt solid var(--brand);
  padding-bottom:3mm; margin-bottom:5mm; }
.logo { width:11mm; height:11mm; border-radius:50%; background:var(--brand); color:#fff; display:grid;
  place-items:center; font-family:'Noto Sans Oriya','Nirmala UI',sans-serif; font-size:17pt; font-weight:700; flex:none; }
.doc-head .k { font-size:7.5pt; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--amber); }
.doc-head .t { font-size:9pt; color:var(--muted); }
h1 { font-size:20pt; line-height:1.15; margin:0 0 3mm; color:var(--ink); }
h2 { font-size:13pt; color:var(--brand); margin:6mm 0 2mm; padding-top:1mm; break-after:avoid; }
h3 { font-size:11pt; margin:4.5mm 0 1.5mm; break-after:avoid; }
p { margin:0 0 2.2mm; }
ul, ol { margin:0 0 2.5mm; padding-left:5.5mm; }
li { margin-bottom:.8mm; }
li > p { margin:0; }
hr { border:0; border-top:.6pt solid var(--line); margin:5mm 0; }
blockquote { margin:2mm 0 3mm; padding:2.5mm 4mm; background:var(--amber-soft); border-left:2.5pt solid var(--amber);
  border-radius:2px; break-inside:avoid; }
blockquote p { margin:0 0 1.2mm; } blockquote p:last-child { margin:0; }
code { font-family:Consolas,'Cascadia Mono',monospace; font-size:8.8pt; background:#f1f4f8; padding:.2mm 1mm; border-radius:2px; }
pre { background:#f1f4f8; padding:3mm; border-radius:2px; white-space:pre-wrap; break-inside:avoid; }
pre code { background:none; padding:0; }
table { width:100%; border-collapse:collapse; margin:1mm 0 3.5mm; font-size:9pt; break-inside:avoid; }
th, td { text-align:left; vertical-align:top; padding:1.5mm 2mm; border-bottom:.6pt solid var(--line); }
th { font-size:7.8pt; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); border-bottom:1pt solid var(--ink); }
em { color:#334155; }
li.task { list-style:none; margin-left:-5mm; padding-left:6mm; position:relative; }
li.task::before { content:""; position:absolute; left:0; top:1.1mm; width:3mm; height:3mm; border:.9pt solid var(--ink); border-radius:1px; }
"""


_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s")


def _blank_before_lists(text: str) -> str:
    """Python-Markdown needs a blank line before a list; GitHub doesn't."""
    out: list[str] = []
    for line in text.splitlines():
        prev = out[-1] if out else ""
        if _LIST_ITEM.match(line) and prev.strip() and not _LIST_ITEM.match(prev) \
                and not prev.startswith((" ", "\t")):
            out.append("")
        out.append(line)
    return "\n".join(out)


def render(src: Path, out: Path) -> None:
    text = _blank_before_lists(src.read_text(encoding="utf-8"))
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    # "- [ ] item" -> empty tick box for printing.
    body = re.sub(r"<li>\[ \]\s*", '<li class="task">', body)
    body = re.sub(r"<li>\s*<p>\[ \]\s*", '<li class="task"><p>', body)
    title = re.search(r"<h1>(.*?)</h1>", body)
    name = re.sub(r"<[^>]+>", "", title.group(1)) if title else src.stem
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;0,800;1,400&family=Noto+Sans+Oriya:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="doc-head"><div class="logo">ଅ</div><div><div class="k">AaaS · Accessibility as a Service</div>
<div class="t">Team SUBARNAREKHA · Pratikshya Padhi · OAV Jamdhar · Odiapreneur 3.0</div></div></div>
{body}</body></html>"""
    tmp = out.with_suffix(".html")
    tmp.write_text(page, encoding="utf-8")
    subprocess.run(
        [str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=15000", f"--print-to-pdf={out}", tmp.as_uri()],
        check=True, capture_output=True,
    )
    tmp.unlink()
    print(f"{src.name} -> {out}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        s, o = arg.split(":", 1) if arg.count(":") == 1 else arg.rsplit(":", 1)
        render(HERE / s, Path(o) if Path(o).is_absolute() else HERE / o)
