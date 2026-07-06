// Unit-tests the pure OCR pick-mode helpers by regex extraction from
// src/widget.js (same approach as the other smoke tests). A tiny DOM
// shim provides just enough Element behaviour for describeOcrTarget.
//
// Run:  node apps/widget/tests/ocr_pick_smoke.js

const fs = require("fs");
const path = require("path");

const WIDGET = path.resolve(__dirname, "..", "src", "widget.js");
const src = fs.readFileSync(WIDGET, "utf-8");

function extractFn(name) {
  const re = new RegExp("function\\s+" + name + "[\\s\\S]*?^  \\}", "m");
  const m = src.match(re);
  if (!m) throw new Error("could not extract " + name);
  return m[0];
}

// Fake elements: describeOcrTarget touches tagName, currentSrc/src,
// closest("a[href]"), href — and calls isVisible (stubbed here).
class FakeEl {
  constructor(tag, props = {}) {
    this.tagName = tag;
    this.attrs = props.attrs || {};
    Object.assign(this, props);
  }
  getAttribute(k) {
    return this.attrs[k] !== undefined ? this.attrs[k] : null;
  }
  closest(sel) {
    let node = this;
    while (node) {
      if (sel === "a[href]" && node.tagName === "A" && node.href) return node;
      if (sel === "figure" && node.tagName === "FIGURE") return node;
      node = node.parent || null;
    }
    return null;
  }
  querySelector(sel) {
    if (sel === "figcaption" && this.caption) return this.caption;
    return null;
  }
}

global.document = { baseURI: "http://127.0.0.1:8000/demo/jajpur-collectorate/" };
global.URL = URL;

const code =
  "function isVisible(el) { return !el.hidden; }\n" +
  extractFn("describeOcrTarget") +
  "\n" +
  extractFn("ocrLangHint") +
  "\n" +
  extractFn("ocrCandidateName") +
  "\n" +
  "module.exports = { describeOcrTarget, ocrLangHint, ocrCandidateName };";

const mod = { exports: {} };
new Function("module", code)(mod);
const { describeOcrTarget, ocrLangHint, ocrCandidateName } = mod.exports;

const results = [];
function check(name, ok) {
  results.push({ name, ok });
  console.log((ok ? "  PASS " : "  FAIL ") + name);
}

// --- describeOcrTarget: images ---
const img = new FakeEl("IMG", { src: "assets/notice-scan.png", currentSrc: "http://x/assets/notice-scan.png" });
const gotImg = describeOcrTarget(img);
check("visible image is a target", gotImg && gotImg.kind === "image");
check("image url prefers currentSrc", gotImg && gotImg.url === "http://x/assets/notice-scan.png");

const hiddenImg = new FakeEl("IMG", { src: "x.png", hidden: true });
check("hidden image is not a target", describeOcrTarget(hiddenImg) === null);

const noSrcImg = new FakeEl("IMG", { src: "", currentSrc: "" });
check("image without src is not a target", describeOcrTarget(noSrcImg) === null);

// --- describeOcrTarget: PDF links ---
const pdfLink = new FakeEl("A", { href: "http://x/docs/Circular-Scan.PDF?dl=1" });
const gotPdf = describeOcrTarget(pdfLink);
check("PDF link is a target (case + query ignored)", gotPdf && gotPdf.kind === "pdf");
check("PDF url kept intact", gotPdf && gotPdf.url === "http://x/docs/Circular-Scan.PDF?dl=1");

const spanInLink = new FakeEl("SPAN", {});
spanInLink.parent = new FakeEl("A", { href: "http://x/notice.pdf" });
check("click on child of a PDF link resolves to the link", (describeOcrTarget(spanInLink) || {}).kind === "pdf");

const htmlLink = new FakeEl("A", { href: "http://x/page.html" });
check("normal link is not a target", describeOcrTarget(htmlLink) === null);

const relativePdf = new FakeEl("A", { href: "assets/scan.pdf" });
check("relative PDF href resolves against baseURI", (describeOcrTarget(relativePdf) || {}).kind === "pdf");

check("null input is safe", describeOcrTarget(null) === null);

// --- ocrLangHint ---
check("Hindi page hints hin", ocrLangHint("hi") === "hi");
check("English page hints auto (ori+eng covers mixes)", ocrLangHint("en") === "auto");
check("Odia page hints auto", ocrLangHint("or") === "auto");

// --- ocrCandidateName ---
const altImg = new FakeEl("IMG", { attrs: { alt: "Scanned notification No. 1247" } });
check("image name from alt text", ocrCandidateName(altImg, "image") === "Scanned notification No. 1247");

const figImg = new FakeEl("IMG", { attrs: {} });
figImg.parent = new FakeEl("FIGURE", {});
figImg.parent.caption = { textContent: "  Notification (scanned copy)  " };
check("image name falls back to figcaption", ocrCandidateName(figImg, "image") === "Notification (scanned copy)");

const bareImg = new FakeEl("IMG", { attrs: {} });
check("image name has a safe default", ocrCandidateName(bareImg, "image") === "Image on this page");

const namedLink = new FakeEl("A", { href: "http://x/a.pdf", textContent: "Examination circular  No. 886" });
check("pdf name from link text", ocrCandidateName(namedLink, "pdf") === "Examination circular No. 886");

const bareLink = new FakeEl("A", { href: "http://x/files/Sale%20Notice-1.pdf", textContent: "" });
check("pdf name falls back to decoded filename", ocrCandidateName(bareLink, "pdf") === "Sale Notice-1.pdf");

const fails = results.filter((r) => !r.ok);
console.log("");
console.log(fails.length === 0 ? "OK — all " + results.length + " checks passed" : "FAIL — " + fails.length + " of " + results.length + " failed");
process.exit(fails.length === 0 ? 0 : 1);
