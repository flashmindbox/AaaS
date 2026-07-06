// Unit-tests the pure voice-navigation matcher functions by regex
// extraction from src/widget.js (same approach as dyslexia_smoke.js).
// No DOM shim needed — everything under test is pure.
//
// Run:  node apps/widget/tests/voice_match_smoke.js

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
  const re = new RegExp("const " + name + " = [\\s\\S]*?;\\n", "m");
  const m = src.match(re);
  if (!m) throw new Error("could not extract " + name);
  return m[0];
}

const code =
  extractConst("VOICE_STRIP_LEADING") +
  extractConst("VOICE_STRIP_TRAILING") +
  extractConst("VOICE_COMMANDS") +
  extractConst("VOICE_OR_EN_GLOSSARY") +
  extractConst("VOICE_ACT_THRESHOLD") +
  extractConst("VOICE_SURE_THRESHOLD") +
  extractConst("VOICE_AMBIGUITY_GAP") +
  extractFn("toWesternDigits") +
  "\n" +
  extractFn("editDistance") +
  "\n" +
  extractFn("phoneticSquash") +
  "\n" +
  extractFn("consonantSkeleton") +
  "\n" +
  extractFn("_tokenSim") +
  "\n" +
  extractFn("normalizeCommandText") +
  "\n" +
  extractFn("matchGlobalCommand") +
  "\n" +
  extractFn("odiaSkeleton") +
  "\n" +
  extractFn("glossaryTranslateOdia") +
  "\n" +
  extractFn("scoreVoiceTarget") +
  "\n" +
  extractFn("rankVoiceTargets") +
  "\n" +
  extractFn("sameVoiceName") +
  "\n" +
  extractFn("sameVoiceTarget") +
  "\n" +
  extractFn("shouldActOnVoiceMatch") +
  "\n" +
  "module.exports = { editDistance, normalizeCommandText, matchGlobalCommand, glossaryTranslateOdia, scoreVoiceTarget, rankVoiceTargets, shouldActOnVoiceMatch, sameVoiceName };";

const mod = { exports: {} };
new Function("module", code)(mod);
const {
  editDistance,
  normalizeCommandText,
  matchGlobalCommand,
  glossaryTranslateOdia,
  scoreVoiceTarget,
  rankVoiceTargets,
  shouldActOnVoiceMatch,
  sameVoiceName,
} = mod.exports;

const results = [];
function check(name, ok) {
  results.push({ name, ok });
  console.log((ok ? "  PASS " : "  FAIL ") + name);
}

// --- editDistance ---
check("editDistance identical", editDistance("abc", "abc") === 0);
check("editDistance one edit", editDistance("kitten", "sitten") === 1);
check("editDistance empty", editDistance("", "abc") === 3);

// --- normalizeCommandText ---
check(
  "strips punctuation + leading filler",
  normalizeCommandText("Click on Citizen Services!") === "citizen services",
);
check(
  "strips longest leading filler first",
  normalizeCommandText("click on tenders") === "tenders",
);
check(
  "strips trailing Odia verb",
  normalizeCommandText("ନାଗରିକ ସେବା ଖୋଲ") === "ନାଗରିକ ସେବା",
);
check("westernizes Odia digits", normalizeCommandText("ଫଳାଫଳ ୨୦୨୬") === "ଫଳାଫଳ 2026");
check("empty input", normalizeCommandText("") === "");

// --- matchGlobalCommand ---
check("Odia translate command", matchGlobalCommand("ଅନୁବାଦ କର", "or") === "translate");
check("English read command", matchGlobalCommand("read this page", "en") === "read");
check("cross-language lookup (en phrase, or hint)", matchGlobalCommand("stop", "or") === "stop");
check("fuzzy tolerates a slip", matchGlobalCommand("translat page", "en") === "translate");
check("garbage is not a command", matchGlobalCommand("purple monkey dishwasher", "en") === null);

// --- glossaryTranslateOdia ---
check(
  "glossary maps common nav phrase",
  glossaryTranslateOdia("ନାଗରିକ ସେବା") === "citizen services",
);
check(
  "glossary fuzzy-recovers an STT slip",
  (glossaryTranslateOdia("ଛାତ୍ର ବ୍ୃତି") || "").includes("scholarship"),
);
check("glossary returns null for unmapped Odia", glossaryTranslateOdia("ଭିଲଡ଼ର") === null);
check(
  "glossary-driven ranking finds the target",
  (() => {
    const g = glossaryTranslateOdia("ଭିନ୍ନକ୍ଷମ ପିଲାଙ୍କ ପାଇଁ ଛାତ୍ର ବୃତ୍ତି");
    const r = rankVoiceTargets(g, [
      { name: "Post-matric scholarship for students with disabilities — last date 30 April", element: null },
      { name: "Contact", element: null },
    ]);
    return r.length > 0 && r[0].name.includes("scholarship") && shouldActOnVoiceMatch(r);
  })(),
);

// --- scoreVoiceTarget ---
check("exact name scores 1", scoreVoiceTarget("citizen services", "Citizen Services") === 1);
const containScore = scoreVoiceTarget("services", "Citizen Services");
check("contained name scores 0.75-0.95", containScore >= 0.75 && containScore <= 0.95);
check(
  "fuzzy transcript clears act threshold",
  scoreVoiceTarget("citzen services", "Citizen Services") >= 0.65,
);
check("unrelated pair scores low", scoreVoiceTarget("weather report", "Citizen Services") < 0.4);

// --- phonetic matching: Odia-STT-heard English finds English names ---
const kantakta = scoreVoiceTarget("Kantakta", "Contact");
check("phonetic 'Kantakta' finds Contact", kantakta >= 0.65);
const notif = scoreVoiceTarget("Notiphikesana", "Notifications");
check("phonetic 'Notiphikesana' finds Notifications", notif >= 0.65);
check("phonetic still rejects unrelated", scoreVoiceTarget("Kantakta", "Tenders") < 0.5);
check(
  "one-letter site buttons (A-, A+) never match by containment",
  scoreVoiceTarget("likara sapa notisa", "A-") < 0.3 && scoreVoiceTarget("tenders", "A") < 0.3,
);
check(
  "skeleton coincidences stay below the choices floor",
  scoreVoiceTarget("Skalarasipa", "Scroll") < 0.55 && scoreVoiceTarget("Skalarasipa", "Close") < 0.55,
);
check(
  "real fuzzy matches stay above the choices floor",
  scoreVoiceTarget("Kantakta", "Contact") >= 0.55 &&
    scoreVoiceTarget("pepara", "Sample Papers") >= 0.55 &&
    scoreVoiceTarget("ପେନସନ", "ମଧୁବାବୁ ପେନ୍ସନ୍ ଯୋଜନା (MBPY) ଉପରେ ନିର୍ଦ୍ଦେଶାବଳୀ") >= 0.55,
);
check(
  "Odia virama slip still matches (ପେନସନ vs ପେନ୍ସନ୍)",
  scoreVoiceTarget("ପେନସନ", "ପେନ୍ସନ୍") >= 0.9,
);
check(
  "Odia word found inside a long Odia link name",
  scoreVoiceTarget("ପେନସନ", "ମଧୁବାବୁ ପେନ୍ସନ୍ ଯୋଜନା (MBPY) ଉପରେ ନିର୍ଦ୍ଦେଶାବଳୀ") >= 0.6,
);
check("phonetic global command: 'rid pej' -> read", matchGlobalCommand("rid pej", "en") === "read");

// --- rankVoiceTargets + decision rule ---
const TARGETS = [
  { name: "Citizen Services", element: null },
  { name: "Contact Us", element: null },
  { name: "Tenders", element: null },
];

const good = rankVoiceTargets("citizen services", TARGETS);
check("good transcript ranks the right target first", good[0] && good[0].name === "Citizen Services");
check("good transcript acts", shouldActOnVoiceMatch(good) === true);

const ambiguous = rankVoiceTargets("services contact", TARGETS);
check("ambiguous transcript does not act", shouldActOnVoiceMatch(ambiguous) === false);

check("empty ranking does not act", shouldActOnVoiceMatch([]) === false);

// --- real-site cases: duplicate names + hidden targets ---
check(
  "same-name tie (header+footer copies) still acts",
  shouldActOnVoiceMatch([
    { score: 0.7, name: "Tenders" },
    { score: 0.7, name: "Tenders" },
    { score: 0.4, name: "Contact" },
  ]) === true,
);
check(
  "different-name near-tie stays cautious",
  shouldActOnVoiceMatch([
    { score: 0.7, name: "Tenders" },
    { score: 0.68, name: "Notices" },
  ]) === false,
);
check(
  "visible target outranks identical hidden one",
  (() => {
    const r = rankVoiceTargets("tenders", [
      { name: "Tenders", element: null, hidden: true },
      { name: "Tenders", element: null },
    ]);
    return r.length === 2 && r[0].hidden === false && r[1].hidden === true;
  })(),
);
check(
  "truncated ticker copy counts as the same link",
  sameVoiceName(
    "NOTICE INVITING APPLICATIONS FOR SETTLEMENT OF COUNTRY LIQUOR SHOPS FOR JAJPUR DISTRICT FOR 2026-27",
    "NOTICE INVITING APPLICATIONS FOR SETTLEMENT OF COUNTRY LIQUOR SHOPS FOR…",
  ) === true,
);
check(
  "bulleted copy of a link counts as the same link",
  sameVoiceName("• M.Tech Spot Round Admission 2026-27", "M.Tech Spot Round Admission 2026-27") === true,
);
check(
  "different notices stay distinct",
  sameVoiceName(
    "Public notice on lease cases under Danagadi Tahasil.",
    "Public Notice for allotment of homestead land",
  ) === false,
);
check(
  "same destination worded differently still acts",
  (() => {
    const el = { tagName: "A", href: "http://x/tender.pdf" };
    return shouldActOnVoiceMatch([
      { score: 0.7, name: "Tender call notice No. 88 for supply of devices", element: el },
      { score: 0.68, name: "Tender call notice No. 88 — supply of devices (PDF)", element: { tagName: "A", href: "http://x/tender.pdf" } },
      { score: 0.4, name: "Contact", element: null },
    ]) === true;
  })(),
);
check(
  "hidden carousel notice is now reachable",
  (() => {
    const r = rankVoiceTargets("liquor shop notice", [
      { name: "NOTICE INVITING APPLICATIONS FOR SETTLEMENT OF COUNTRY LIQUOR SHOPS FOR JAJPUR DISTRICT", element: null, hidden: true },
      { name: "Home", element: null },
    ]);
    return r.length > 0 && /LIQUOR/.test(r[0].name);
  })(),
);

const noise = rankVoiceTargets("purple monkey dishwasher", TARGETS);
check("noise matches nothing", noise.length === 0);

const fails = results.filter((r) => !r.ok);
console.log("");
console.log(fails.length === 0 ? "OK — all " + results.length + " checks passed" : "FAIL — " + fails.length + " of " + results.length + " failed");
process.exit(fails.length === 0 ? 0 : 1);
