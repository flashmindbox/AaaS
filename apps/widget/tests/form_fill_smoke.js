// Unit-tests the guided form-fill value normalizer by regex extraction
// from src/widget.js (same approach as the other smoke tests).
//
// Run:  node apps/widget/tests/form_fill_smoke.js

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

function extractConst(name) {
  const re = new RegExp("const " + name + " = \\{[\\s\\S]*?\\};", "m");
  const m = src.match(re);
  if (!m) throw new Error("could not extract " + name);
  return m[0];
}

const code =
  extractFn("toWesternDigits") +
  "\n" +
  extractConst("ODIA_VOWELS") +
  extractConst("ODIA_CONSONANTS") +
  extractConst("ODIA_MATRAS") +
  extractConst("ODIA_SIGNS") +
  extractFn("romanizeOdia") +
  "\n" +
  extractFn("normalizeSpokenValue") +
  "\n" +
  "module.exports = { normalizeSpokenValue, romanizeOdia };";

const mod = { exports: {} };
new Function("module", code)(mod);
const { normalizeSpokenValue, romanizeOdia } = mod.exports;

const results = [];
function check(name, ok) {
  results.push({ name, ok });
  console.log((ok ? "  PASS " : "  FAIL ") + name);
}

// --- tel / number: digits only ---
check("phone keeps only digits", normalizeSpokenValue("tel", "98 76-54 32 10") === "9876543210");
check("Odia digits westernised", normalizeSpokenValue("tel", "୯୮୭୬୫୪୩୨୧୦") === "9876543210");
check("number field strips words", normalizeSpokenValue("number", "45 ବର୍ଷ") === "45");
check("no digits at all passes through", normalizeSpokenValue("tel", "ରାମ") === "ରାମ");

// --- email: spoken at/dot forms ---
check("spoken email assembled", normalizeSpokenValue("email", "ram kumar at gmail dot com") === "ramkumar@gmail.com");
check("email lowercased and de-spaced", normalizeSpokenValue("email", "Ram AT Gmail DOT Com") === "ram@gmail.com");

// --- text: trailing danda/period dropped ---
check("trailing danda removed", normalizeSpokenValue("text", "ରାମ ପ୍ରସାଦ ମହାନ୍ତି।") === "ରାମ ପ୍ରସାଦ ମହାନ୍ତି");
check("trailing period removed", normalizeSpokenValue("text", "Ram Prasad Mohanty.") === "Ram Prasad Mohanty");
check("textarea keeps inner punctuation", normalizeSpokenValue("textarea", "Pipe broken, road flooded. Since May.") === "Pipe broken, road flooded. Since May");
check("empty stays empty", normalizeSpokenValue("text", "  ") === "");

// --- romanizeOdia: names/places become the SAME word in Latin ---
check("simple name", romanizeOdia("ରାମ") === "Rama");
check("name with conjunct", romanizeOdia("ମହାନ୍ତି") === "Mahanti");
check("place name Badachana", romanizeOdia("ବଡ଼ଚଣା") === "Badachana");
check("Purnnachandra keeps its sounds", /purnnachandra/i.test(romanizeOdia("ପୂର୍ଣ୍ଣଚନ୍ଦ୍ର")));
check("Banapur is NOT firework", /banapura/i.test(romanizeOdia("ବଣପୁର")));
check("multi-word title case", romanizeOdia("ରାମ ପ୍ରସାଦ") === "Rama Prasada");
check("odia digits romanize", romanizeOdia("ପ୍ଲଟ ୪୫") === "Plata 45");
check("danda becomes period", romanizeOdia("ଭାଙ୍ଗିଯାଇଛି।").endsWith("."));
check("latin passes through", romanizeOdia("Jajpur Road") === "Jajpur Road");

const fails = results.filter((r) => !r.ok);
console.log("");
console.log(fails.length === 0 ? "OK — all " + results.length + " checks passed" : "FAIL — " + fails.length + " of " + results.length + " failed");
process.exit(fails.length === 0 ? 0 : 1);
