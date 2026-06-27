"""Generate small image assets for the pitch deck (rendered to PNG via Chrome).

Outputs SVG + transparent HTML wrappers under pitch/assets/. A separate Chrome
headless pass rasterises them. Native diagram shapes are built in the deck
itself; here we only need the chakra logo and the Odia title phrase (which needs
the embedded Noto Sans Oriya font so it renders anywhere)."""
import base64, pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "pitch" / "assets"
A.mkdir(parents=True, exist_ok=True)
FONT = REPO / "apps" / "widget" / "src" / "fonts" / "noto-sans-oriya-400-subset.woff2"
B64 = base64.b64encode(FONT.read_bytes()).decode("ascii")

CHAKRA = '''<g fill="none" stroke="{c}">
  <circle cx="100" cy="100" r="94" stroke-width="4"/>
  <circle cx="100" cy="100" r="84" stroke-width="9" stroke-dasharray="2.5 9.2" stroke-linecap="round"/>
  <circle cx="100" cy="100" r="70" stroke-width="3"/>
  <g stroke-width="4">
    <line x1="100" y1="100" x2="170" y2="100"/><line x1="100" y1="100" x2="160.6" y2="135"/>
    <line x1="100" y1="100" x2="135" y2="160.6"/><line x1="100" y1="100" x2="100" y2="170"/>
    <line x1="100" y1="100" x2="65" y2="160.6"/><line x1="100" y1="100" x2="39.4" y2="135"/>
    <line x1="100" y1="100" x2="30" y2="100"/><line x1="100" y1="100" x2="39.4" y2="65"/>
    <line x1="100" y1="100" x2="65" y2="39.4"/><line x1="100" y1="100" x2="100" y2="30"/>
    <line x1="100" y1="100" x2="135" y2="39.4"/><line x1="100" y1="100" x2="160.6" y2="65"/>
  </g>
  <circle cx="100" cy="100" r="20" fill="{c}" stroke="none"/>
  <circle cx="100" cy="100" r="10" fill="{hub}" stroke="none"/>
</g>'''

def wrap(name, w, h, body, vb=None):
    vb = vb or f"0 0 {w} {h}"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}">'
           f'<defs><style>@font-face{{font-family:OdiaE;src:url(data:font/woff2;base64,{B64}) format("woff2");}}'
           f'.od{{font-family:OdiaE,sans-serif;}}</style></defs>{body}</svg>')
    (A / f"{name}.svg").write_text(svg, encoding="utf-8")
    html = ('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:transparent;}'
            'svg{display:block;}</style>' + svg)
    (A / f"{name}.html").write_text(html, encoding="utf-8")

# 1) Gold chakra logo (transparent)
wrap("chakra_gold", 220, 220,
     f'<g transform="translate(10,10)">{CHAKRA.format(c="#e6b93f", hub="#7c1428")}</g>')

# 2) Maroon chakra (for light backgrounds)
wrap("chakra_maroon", 220, 220,
     f'<g transform="translate(10,10)">{CHAKRA.format(c="#a8213b", hub="#e6b93f")}</g>')

# 3) Odia title phrase, gold (sits on maroon band)
wrap("odia_sub", 1500, 150,
     '<text x="0" y="112" class="od" font-size="104" font-weight="700" fill="#ffe6bf">'
     'ସମସ୍ତଙ୍କ ପାଇଁ ସୁଗମ ସେବା</text>')

print("wrote assets:", *(p.name for p in sorted(A.glob("*.svg"))))
