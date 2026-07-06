/**
 * AaaS accessibility widget — v2 (Phase v2).
 *
 * A single `<script>` tag paints a floating button onto the page. Click
 * it to open a panel with:
 *
 *   - "Read this page" → server TTS (translates first if the picked
 *     language isn't the page's own). Meta MMS-TTS is the only engine;
 *     there is no browser-Web-Speech fallback — if the gateway is down,
 *     the status pill surfaces the error and nothing speaks.
 *   - Language picker → Odia / Hindi / English / Auto (auto reads the
 *     page's own language attribute).
 *   - Microphone → records up to 10 s, sends to /stt/transcribe,
 *     displays the transcript, and dispatches an `aaas-transcript`
 *     CustomEvent so the host page (demo-site forms)
 *     can listen and auto-fill form fields.
 *
 * The panel lives in a Shadow DOM so the host page's CSS can't leak
 * in and the widget's CSS can't leak out.
 *
 * Usage:
 *
 *   <script
 *     src="/widget.js"
 *     data-gateway="http://127.0.0.1:8000"
 *     data-key="aaas_live_00000000000000000000000000000000"
 *     defer
 *   ></script>
 *
 *   // Optional: let the host page receive STT transcripts.
 *   document.addEventListener("aaas-transcript", (ev) => {
 *     const { text, language } = ev.detail;
 *     document.activeElement.value = text;
 *   });
 */
(function () {
  "use strict";

  if (window.__AAAS_WIDGET_LOADED__) return;
  window.__AAAS_WIDGET_LOADED__ = true;

  // Noto Sans Oriya regular (Odia + ZWNJ/ZWJ subset from Google Fonts v35,
  // ~99 KB woff2). Inlined so Odia conjuncts render correctly on judge
  // laptops that ship without the font — Windows 10/11 has "Kalinga"
  // but its conjunct rendering is poor; macOS ships nothing for Oriya.
  //
  // The literal is replaced at dist-build time by scripts/build_widget.py.
  // In src/ it stays as the placeholder string so the file stays readable.
  const NOTO_ORIYA_WOFF2_BASE64 = "__AAAS_NOTO_ORIYA_B64__";
  const ORIYA_UNICODE_RANGE =
    "U+0951-0952, U+0964-0965, U+0B01-0B77, U+1CDA, U+1CF2, U+200C-200D, U+20B9, U+25CC";

  // Atkinson Hyperlegible (Braille Institute, OFL) for dyslexia mode.
  // Latin-only subset; the unicode-range keeps it away from Indic text
  // so Odia keeps rendering with Noto Sans Oriya.
  const ATKINSON_WOFF2_BASE64 = "__AAAS_ATKINSON_B64__";
  const LATIN_UNICODE_RANGE =
    "U+0000-00FF, U+0131, U+0152-0153, U+2013-2014, U+2018-201D, U+2026";

  // localStorage keys. Namespaced so embedders don't clash with us.
  const LS_DYSLEXIA = "aaas.dyslexia.v1";
  const LS_HOVER_SPEAK = "aaas.hover-speak.v1";
  const LS_RULER = "aaas.ruler.v1";

  const CURRENT_SCRIPT = document.currentScript;
  // If the script is served from a http(s) origin (cloud or local
  // gateway), default the gateway URL to that same origin so embedders
  // don't need to repeat it in data-gateway=. Falls through to the
  // old 127.0.0.1:8000 default for file:// or weird embeds.
  const SCRIPT_ORIGIN = (() => {
    try {
      const src = CURRENT_SCRIPT && CURRENT_SCRIPT.src;
      if (!src) return "";
      const o = new URL(src, location.href).origin;
      return o && o.startsWith("http") ? o : "";
    } catch {
      return "";
    }
  })();
  // When loaded by the browser extension there is no <script> tag and no
  // window globals shared across the isolated/main world boundary. The
  // extension's isolated-world shim writes config onto the <html> element's
  // dataset (DOM is shared across worlds); read it here as a fallback.
  const HTML_DATASET =
    (document.documentElement && document.documentElement.dataset) || {};
  const CONFIG = {
    gateway:
      CURRENT_SCRIPT?.dataset.gateway ||
      window.AAAS_GATEWAY_URL ||
      HTML_DATASET.aaasGateway ||
      SCRIPT_ORIGIN ||
      "http://127.0.0.1:8000",
    apiKey:
      CURRENT_SCRIPT?.dataset.key ||
      window.AAAS_API_KEY ||
      HTML_DATASET.aaasKey ||
      "aaas_live_00000000000000000000000000000000",
    // Default read-aloud language. The extension's config bridge writes
    // data-aaas-lang from the popup's "Default language" setting; a plain
    // embed can use <script data-lang> or window.AAAS_DEFAULT_LANG. Falls
    // back to Odia — this platform is Odisha-first, and the flagship demo
    // moment (translate + read an English page in Odia) must work without
    // touching the picker. "auto" (read the page's own language) is still
    // available in the picker and as an explicit config value. Normalised
    // to a known value so a bad config can't wedge the picker on an
    // option that doesn't exist.
    defaultLang: (() => {
      const v = (
        CURRENT_SCRIPT?.dataset.lang ||
        window.AAAS_DEFAULT_LANG ||
        HTML_DATASET.aaasLang ||
        "or"
      ).toLowerCase();
      return ["auto", "or", "hi", "en"].includes(v) ? v : "or";
    })(),
    // Client-side chunk size. Kept well below the TTS service's
    // MAX_INPUT_CHARS (600) so we never hit a 413, but also small
    // enough that the first chunk synthesises fast — time-to-first-
    // audio is the single biggest demo UX lever. Sentence-based
    // chunking fills up to this cap and flushes on the next boundary.
    maxChars: 220,
    // Max recording length before we auto-stop. Keeps STT latency bounded
    // and avoids leaving the mic on if the user forgets to click stop.
    maxRecordSeconds: 10,
  };

  // When the browser extension has "On-device mode" enabled, the isolated-
  // world config bridge writes these onto <html> so the main-world widget
  // can dynamic-import ondevice.js from the extension origin. Empty/0 on
  // every non-extension embed, which is how the gateway-path stays the
  // default without any code-branch check.
  const ON_DEVICE = HTML_DATASET.aaasOnDevice === "1";
  const EXT_ROOT = HTML_DATASET.aaasExtRoot || "";

  // Set by the extension's isolated-world bridge (inject-config.js). When
  // present, translation is routed through Google Translate via the background
  // service worker (which bypasses page CSP + CORS) instead of being fetched
  // directly. On a plain <script> embed this is empty and we fetch Google
  // ourselves, falling back to the AaaS gateway if that's blocked/offline.
  const EXT_BRIDGE = HTML_DATASET.aaasExt === "1";

  // Lazy-loaded once per page. null = not tried yet, pending promise while
  // importing, resolved {speak,transcribe} once ready. Failures resolve to
  // null so subsequent calls fall through to the gateway path quickly
  // instead of retrying a doomed dynamic import on every utterance.
  let _onDeviceBackendPromise = null;
  async function getOnDeviceBackend() {
    if (!ON_DEVICE || !EXT_ROOT) return null;
    if (_onDeviceBackendPromise) return _onDeviceBackendPromise;
    _onDeviceBackendPromise = (async () => {
      try {
        const mod = await import(EXT_ROOT + "ondevice.js");
        return await mod.createOnDeviceBackend({ extRoot: EXT_ROOT });
      } catch (err) {
        console.warn("[AaaS] on-device backend unavailable:", err);
        return null;
      }
    })();
    return _onDeviceBackendPromise;
  }

  /* ---------- primitives: LRU cache, StreamQueue, typed errors ---------- */

  // Size-bounded cache for translate responses (strings) and phrase TTS
  // blobs. Using a plain Map + oldest-key eviction — the set is small
  // enough (few hundred entries) that a real LRU order-of-access
  // data structure would be overkill.
  class LruCache {
    constructor(max) {
      this.max = max;
      this.map = new Map();
    }
    has(key) { return this.map.has(key); }
    get(key) {
      if (!this.map.has(key)) return undefined;
      const v = this.map.get(key);
      this.map.delete(key);
      this.map.set(key, v);
      return v;
    }
    set(key, value) {
      if (this.map.has(key)) this.map.delete(key);
      this.map.set(key, value);
      while (this.map.size > this.max) {
        const oldest = this.map.keys().next().value;
        this.map.delete(oldest);
      }
    }
  }

  const translateCache = new LruCache(200);
  const phraseCache = new LruCache(300);

  const translateKey = (src, tgt, text) => `${src}→${tgt}:${text}`;
  const phraseKey = (lang, text) => `${lang}:${text}`;

  // Persistent, cross-reload cache (IndexedDB, scoped to the page's origin).
  // The in-memory LruCaches above die with the page; this layer means
  // re-reading the same page after a reload — or revisiting it later — replays
  // stored audio + translations instead of regenerating them. That's the
  // single biggest cost saver on the on-device path, where a miss means a
  // multi-second model run. Keyed identically to the memory caches. Every
  // operation is best-effort: any IndexedDB failure (private mode, quota,
  // blocked upgrade) degrades silently to "no cache" rather than breaking TTS.
  const persistentCache = (() => {
    const DB_NAME = "aaas-cache";
    const DB_VERSION = 1;
    const STORES = ["tts", "translate"];
    // Soft caps so the cache can't grow without bound; oldest writes evicted.
    const MAX_ENTRIES = { tts: 600, translate: 2000 };
    let dbPromise = null;

    function openDb() {
      if (dbPromise) return dbPromise;
      dbPromise = new Promise((resolve) => {
        let req;
        try {
          req = indexedDB.open(DB_NAME, DB_VERSION);
        } catch {
          resolve(null);
          return;
        }
        req.onupgradeneeded = () => {
          const db = req.result;
          for (const s of STORES) {
            if (!db.objectStoreNames.contains(s)) {
              db.createObjectStore(s).createIndex("t", "t");
            }
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
        req.onblocked = () => resolve(null);
      });
      return dbPromise;
    }

    async function get(store, key) {
      const db = await openDb();
      if (!db) return undefined;
      return new Promise((resolve) => {
        try {
          const r = db.transaction(store, "readonly").objectStore(store).get(key);
          r.onsuccess = () => resolve(r.result ? r.result.v : undefined);
          r.onerror = () => resolve(undefined);
        } catch {
          resolve(undefined);
        }
      });
    }

    async function put(store, key, value) {
      const db = await openDb();
      if (!db) return;
      try {
        const os = db.transaction(store, "readwrite").objectStore(store);
        os.put({ v: value, t: Date.now() }, key);
        // Opportunistic eviction: once over cap, drop the oldest writes.
        const countReq = os.count();
        countReq.onsuccess = () => {
          const over = countReq.result - (MAX_ENTRIES[store] || 1000);
          if (over <= 0) return;
          let removed = 0;
          const curReq = os.index("t").openCursor();
          curReq.onsuccess = () => {
            const cur = curReq.result;
            if (!cur || removed >= over) return;
            cur.delete();
            removed++;
            cur.continue();
          };
        };
      } catch {}
    }

    return { get, put };
  })();

  // Async push/pop channel that lets the three-stage pipeline
  // (translate → TTS → play) run concurrently. Producer calls push()
  // / close(); consumer awaits next() which resolves when something is
  // available or when the queue has closed.
  class StreamQueue {
    constructor() {
      this.items = [];
      this.waiters = [];
      this.closed = false;
    }
    push(item) {
      if (this.closed) return;
      if (this.waiters.length) {
        this.waiters.shift()(item);
      } else {
        this.items.push(item);
      }
    }
    close() {
      this.closed = true;
      while (this.waiters.length) this.waiters.shift()(null);
    }
    async next() {
      if (this.items.length) return this.items.shift();
      if (this.closed) return null;
      return new Promise((resolve) => this.waiters.push(resolve));
    }
  }

  // Typed errors so callers can tell "translate went wrong" from
  // "TTS went wrong" and fall back to the right next step without
  // re-parsing error strings.
  class TranslateError extends Error {
    constructor(text, lang, cause) {
      super(`translate failed: ${cause?.message || cause}`);
      this.name = "TranslateError";
      this.text = text;
      this.lang = lang;
      this.cause = cause;
    }
  }
  class TtsError extends Error {
    constructor(text, lang, cause) {
      super(`tts failed: ${cause?.message || cause}`);
      this.name = "TtsError";
      this.text = text;
      this.lang = lang;
      this.cause = cause;
    }
  }

  // Shared fetch timeout. Wraps AbortController so we don't hang
  // forever on a wedged upstream — 6 s is long enough for a cold
  // MMS-TTS call but short enough that a real outage surfaces as an
  // error instead of a hung request.
  function withTimeout(ms, external) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), ms);
    if (external) external.addEventListener("abort", () => ctl.abort());
    return {
      signal: ctl.signal,
      clear: () => clearTimeout(timer),
    };
  }

  /* ---------- language helpers ---------- */

  // Classify a string by dominant script: Odia, Devanagari (Hindi) or
  // Latin (English). Returns null when there are no letters to judge.
  function dominantScript(text) {
    let or = 0, hi = 0, en = 0;
    for (const ch of text || "") {
      if (/[଀-୿]/.test(ch)) or++;
      else if (/[ऀ-ॿ]/.test(ch)) hi++;
      else if (/[A-Za-z]/.test(ch)) en++;
    }
    if (!or && !hi && !en) return null;
    if (or >= hi && or >= en) return "or";
    if (hi >= or && hi >= en) return "hi";
    return "en";
  }

  // Decide what "Auto" resolves to and what we treat as the translation
  // source. Prefer an explicit <html lang="…">; otherwise sniff the page's
  // own text. The open web is mostly English and many pages omit lang, so an
  // unknown page falls back to English (not Odia) — feeding English text to
  // the Odia voice produces near-silence, and mis-tagging a page as its own
  // target language skips translation entirely.
  function detectPageLang() {
    const raw = (document.documentElement.getAttribute("lang") || "")
      .toLowerCase()
      .split("-")[0];
    if (["or", "hi", "en"].includes(raw)) return raw;
    try {
      const sample = (document.body && document.body.textContent) || "";
      const guessed = dominantScript(sample.slice(0, 5000));
      if (guessed) return guessed;
    } catch {}
    return "en";
  }

  // True iff the letters in `text` are predominantly in `lang`'s script.
  // Used to detect translate output that silently passed through in the
  // source script (mock off-script fallback, or a real engine that gave
  // up) — feeding Latin text to the Odia MMS checkpoint drops almost
  // every token, so "Link, Home" at lang=or comes out as ~0.4s of near-
  // silence. Callers reroute such atoms to source-language speech.
  const _SCRIPT_RE = {
    or: /[଀-୿]/,
    hi: /[ऀ-ॿ]/,
    en: /[A-Za-z]/,
  };
  function looksLikeTargetScript(text, lang) {
    const re = _SCRIPT_RE[lang];
    if (!re || !text) return true;
    let target = 0;
    let other = 0;
    for (const ch of text) {
      if (re.test(ch)) target++;
      else if (/[A-Za-zऀ-ॿ଀-୿]/.test(ch)) other++;
    }
    if (!target && !other) return true;
    return target >= other;
  }

  // The mock translate engine returns "[src->tgt] original" for phrases
  // outside its curated corpus. Feeding that literal prefix to the TTS
  // tokeniser produces a few frames of noise before the real audio;
  // strip it so the announcer only speaks the atom text itself.
  const _PASSTHROUGH_RE = /^\[[a-z]{2}->[a-z]{2}\]\s*/i;
  function stripPassthroughAnnotation(text) {
    return (text || "").replace(_PASSTHROUGH_RE, "");
  }

  // Translate models pass Odia/Devanagari digits through unchanged, but
  // web forms (ages, years, phone numbers) expect ASCII — so numerals
  // are normalised after translation, not before.
  function toWesternDigits(text) {
    if (!text) return text;
    return text
      .replace(/[୦-୯]/g, (ch) => String(ch.charCodeAt(0) - 0x0b66))
      .replace(/[०-९]/g, (ch) => String(ch.charCodeAt(0) - 0x0966));
  }

  // The TTS service splits long inputs into chunks internally but then
  // concatenates every chunk's waveform into one WAV before responding,
  // so paragraph-length atoms don't play until the entire paragraph is
  // rendered (~5 s on a 500-char CPU synth). Pre-splitting here at
  // sentence boundaries lets the translate→synth→play pipeline stream
  // — first audio arrives ~one sentence after we start, not one
  // paragraph. Terminator set mirrors the server's regex.
  const _SENTENCE_SPLIT_RE = /[^.!?।॥]+[.!?।॥]+\s*|[^.!?।॥]+$/g;
  function splitIntoSentences(text, maxChars) {
    const trimmed = (text || "").trim();
    if (!trimmed) return [];
    const cap = maxChars || 180;
    if (trimmed.length <= cap) return [trimmed];
    const pieces = Array.from(trimmed.matchAll(_SENTENCE_SPLIT_RE))
      .map((m) => m[0].trim())
      .filter(Boolean);
    if (!pieces.length) return [trimmed];
    const out = [];
    let buf = "";
    for (const piece of pieces) {
      if (piece.length > cap) {
        if (buf) { out.push(buf); buf = ""; }
        const words = piece.split(/\s+/);
        let w = "";
        for (const word of words) {
          if (!w) w = word;
          else if (w.length + 1 + word.length <= cap) w = w + " " + word;
          else { out.push(w); w = word; }
        }
        if (w) out.push(w);
        continue;
      }
      if (!buf) buf = piece;
      else if (buf.length + 1 + piece.length <= cap) buf = buf + " " + piece;
      else { out.push(buf); buf = piece; }
    }
    if (buf) out.push(buf);
    return out.length ? out : [trimmed];
  }

  /* ---------- voice navigation ----------
   * Matches an STT transcript against (a) a small table of global
   * widget commands per language, then (b) the accessible names of the
   * page's links and buttons. Dependency-free scoring: exact match,
   * containment, then token-level fuzzy overlap via edit distance.
   * Everything here is top-level and pure (rankVoiceTargets works on
   * plain {name} objects) so voice_match_smoke.js can extract and unit
   * test it without a DOM.
   */

  // Two-row iterative Levenshtein distance.
  function editDistance(a, b) {
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    let prev = new Array(b.length + 1);
    let curr = new Array(b.length + 1);
    for (let j = 0; j <= b.length; j++) prev[j] = j;
    for (let i = 1; i <= a.length; i++) {
      curr[0] = i;
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        curr[j] = Math.min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
      }
      const tmp = prev;
      prev = curr;
      curr = tmp;
    }
    return prev[b.length];
  }

  // Filler a spoken command may carry around the target name: "click
  // on Citizen Services", "ନାଗରିକ ସେବା ଖୋଲ". Longest-first so "click
  // on" wins over "click".
  const VOICE_STRIP_LEADING = [
    "click on", "click", "open", "go to", "goto", "select", "press",
    "क्लिक करो", "खोलो", "जाओ",
  ];
  const VOICE_STRIP_TRAILING = [
    "ଖୋଲନ୍ତୁ", "ଖୋଲ", "କରନ୍ତୁ", "କର", "ଯାଆନ୍ତୁ", "ଯାଅ", "ଦବାନ୍ତୁ",
    "करो", "खोलो", "जाओ",
  ];

  function normalizeCommandText(text) {
    let t = toWesternDigits(text || "")
      .toLowerCase()
      .replace(/[.,!?;:()"'«»।॥/\-–—]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    for (const lead of VOICE_STRIP_LEADING) {
      if (t.startsWith(lead + " ")) {
        t = t.slice(lead.length + 1);
        break;
      }
    }
    for (const tail of VOICE_STRIP_TRAILING) {
      if (t.endsWith(" " + tail)) {
        t = t.slice(0, -(tail.length + 1));
        break;
      }
    }
    return t.trim();
  }

  // Global widget actions. Phrases are compared in normalized form, so
  // trailing verbs the normalizer strips ("କର") are safe to include.
  const VOICE_COMMANDS = [
    { action: "read", en: ["read page", "read this page", "read aloud", "read"], or: ["ପୃଷ୍ଠା ପଢ଼", "ପଢ଼ନ୍ତୁ", "ପଢ଼"], hi: ["पेज पढ़ो", "पढ़ो"] },
    { action: "stop", en: ["stop", "stop reading", "quiet"], or: ["ବନ୍ଦ କର", "ରୁହ"], hi: ["रुको", "बंद करो"] },
    { action: "translate", en: ["translate", "translate page", "translate this page"], or: ["ଅନୁବାଦ କର", "ଅନୁବାଦ"], hi: ["अनुवाद करो", "अनुवाद"] },
    { action: "easyread", en: ["easy read", "simplify", "simple words"], or: ["ସହଜ ପଢ଼ା", "ସରଳ କର"], hi: ["आसान पढ़ो", "सरल करो"] },
    { action: "top", en: ["go to top", "top of page", "scroll up"], or: ["ଉପରକୁ ଯାଅ", "ଉପର"], hi: ["ऊपर जाओ"] },
    { action: "search", en: ["search", "find"], or: ["ଖୋଜ"], hi: ["खोजो", "ढूंढो"] },
  ];

  function matchGlobalCommand(text, lang) {
    const norm = normalizeCommandText(text);
    if (!norm) return null;
    const langs = ["en", "or", "hi"].filter((l) => l !== lang);
    langs.unshift(lang);
    // Exact first (hint language, then the rest — STT hints can be
    // wrong), then edit-distance-tolerant on phrases long enough that
    // a one-letter slip can't jump between commands.
    for (const l of langs) {
      for (const cmd of VOICE_COMMANDS) {
        for (const phrase of cmd[l] || []) {
          if (normalizeCommandText(phrase) === norm) return cmd.action;
        }
      }
    }
    for (const l of langs) {
      for (const cmd of VOICE_COMMANDS) {
        for (const phrase of cmd[l] || []) {
          const p = normalizeCommandText(phrase);
          if (p.length < 4 || norm.length < 4) continue;
          const sim = 1 - editDistance(norm, p) / Math.max(norm.length, p.length);
          if (sim >= 0.85) return cmd.action;
        }
      }
    }
    return null;
  }

  // Odia -> English token map for common government-site navigation
  // vocabulary. MT of short nav phrases drifts into synonyms the string
  // matcher can't recover ("ନାଗରିକ ସେବା" -> "the Civil Service",
  // "ଅଭିଯୋଗ" -> "Complaint" where the link says "Grievance"), so the
  // frequent terms are pinned to the wording the sites actually use.
  // Values may be multi-word. Extend freely during rehearsal.
  const VOICE_OR_EN_GLOSSARY = {
    "ନାଗରିକ": "citizen",
    "ସେବା": "services",
    "ଯୋଗାଯୋଗ": "contact",
    "ଅଭିଯୋଗ": "grievance",
    "ବିଜ୍ଞପ୍ତି": "notifications",
    "ସୂଚନା": "notice",
    "ଫଳାଫଳ": "results",
    "ପ୍ରମାଣପତ୍ର": "certificate",
    "ଆୟ": "income",
    "ଜାତି": "caste",
    "ବାସିନ୍ଦା": "residence",
    "ଛାତ୍ର": "student",
    "ଛାତ୍ରଛାତ୍ରୀ": "students",
    "ବୃତ୍ତି": "scholarship",
    "ପିଲା": "students",
    "ପିଲାଙ୍କ": "students",
    "ପାଇଁ": "for",
    "ଭିନ୍ନକ୍ଷମ": "disabilities",
    "ଆବେଦନ": "apply",
    "ଡାଉନଲୋଡ୍": "download",
    "ଟେଣ୍ଡର": "tender",
    "ନିଯୁକ୍ତି": "recruitment",
    "ସ୍ୱାସ୍ଥ୍ୟ": "health",
    "ଶିକ୍ଷା": "education",
    "ରାସନ": "ration",
    "କାର୍ଡ": "card",
    "ପେନସନ": "pension",
    "ଯୋଜନା": "scheme",
    "ବିଷୟରେ": "about",
    "ଘର": "home",
    "ଖବର": "news",
  };

  // STT slips in Odia mostly scramble matras and viramas, not the base
  // consonants (ବ୍ୃତି for ବୃତ୍ତି). Stripping the combining marks gives
  // a consonant skeleton that survives those slips, so fuzzy glossary
  // lookup compares skeletons when the full forms don't match.
  function odiaSkeleton(tok) {
    return tok.replace(/[଼-୍୕-ୗୢ-ୣ]/g, "");
  }

  // Map an Odia transcript to English via the nav glossary, token by
  // token. Fuzzy key lookup absorbs small STT slips. Odia tokens with
  // no glossary hit are dropped rather than passed through — a partial
  // English phrase matches links, mixed-script noise doesn't. Returns
  // null when nothing mapped.
  function glossaryTranslateOdia(normText) {
    const keys = Object.keys(VOICE_OR_EN_GLOSSARY);
    const out = [];
    let mapped = 0;
    for (const tok of normText.split(" ")) {
      if (!tok) continue;
      if (!/[଀-୿]/.test(tok)) {
        out.push(tok);
        continue;
      }
      let hit = VOICE_OR_EN_GLOSSARY[tok];
      if (!hit) {
        const tokSkel = odiaSkeleton(tok);
        let bestSim = 0;
        let bestKey = null;
        for (const k of keys) {
          const full = 1 - editDistance(tok, k) / Math.max(tok.length, k.length);
          const kSkel = odiaSkeleton(k);
          const skel = kSkel && tokSkel
            ? 1 - editDistance(tokSkel, kSkel) / Math.max(tokSkel.length, kSkel.length)
            : 0;
          const sim = Math.max(full, skel);
          if (sim > bestSim) {
            bestSim = sim;
            bestKey = k;
          }
        }
        if (bestSim >= 0.65) hit = VOICE_OR_EN_GLOSSARY[bestKey];
      }
      if (hit) {
        out.push(hit);
        mapped++;
      }
    }
    return mapped ? out.join(" ") : null;
  }

  // Score a transcript against one accessible name. 1.0 exact;
  // 0.75–0.95 containment (scaled by length ratio); otherwise a
  // token-overlap blend: coverage = how much of the transcript matched,
  // precision = how much of the name it accounts for.
  function scoreVoiceTarget(transcript, name) {
    const t = normalizeCommandText(transcript);
    const n = normalizeCommandText(name);
    if (!t || !n) return 0;
    if (t === n) return 1;
    if (n.includes(t) || t.includes(n)) {
      const ratio = Math.min(t.length, n.length) / Math.max(t.length, n.length);
      return 0.75 + 0.2 * ratio;
    }
    const tTokens = t.split(" ");
    const nTokens = n.split(" ");
    let sum = 0;
    for (const tok of tTokens) {
      let best = 0;
      for (const cand of nTokens) {
        let s = 0;
        if (tok === cand) s = 1;
        else if (tok.length >= 4 && cand.length >= 4) {
          s = 1 - editDistance(tok, cand) / Math.max(tok.length, cand.length);
        }
        if (s > best) best = s;
      }
      if (best >= 0.75) sum += best;
    }
    const coverage = Math.min(1, sum / tTokens.length);
    const precision = Math.min(1, sum / nTokens.length);
    return 0.7 * coverage + 0.3 * precision;
  }

  const VOICE_ACT_THRESHOLD = 0.65;
  const VOICE_SURE_THRESHOLD = 0.85;
  const VOICE_AMBIGUITY_GAP = 0.1;

  function rankVoiceTargets(transcript, targets) {
    const ranked = [];
    for (const target of targets) {
      const score = scoreVoiceTarget(transcript, target.name || "");
      if (score > 0.25) {
        ranked.push({ score, name: target.name, element: target.element || null });
      }
    }
    ranked.sort((a, b) => b.score - a.score);
    return ranked;
  }

  // Act on a clearly-best candidate, never on an ambiguous one: a sure
  // hit clicks, a plausible hit clicks only with daylight to the
  // runner-up, everything else just reports candidates.
  function shouldActOnVoiceMatch(ranked) {
    if (!ranked.length) return false;
    const top = ranked[0].score;
    if (top >= VOICE_SURE_THRESHOLD) return true;
    if (top < VOICE_ACT_THRESHOLD) return false;
    return ranked.length < 2 || top - ranked[1].score >= VOICE_AMBIGUITY_GAP;
  }

  const VOICE_TARGET_SELECTOR =
    'a[href], button, [role="button"], [role="link"], input[type="submit"], input[type="button"], summary';

  function collectVoiceTargets() {
    const seen = new Set();
    const out = [];
    document.querySelectorAll(VOICE_TARGET_SELECTOR).forEach((el) => {
      if (!isVisible(el)) return;
      if (el.closest("[data-aaas-widget]")) return;
      // getAccessibleName skips <input> value; submit buttons name
      // themselves through it ("<input type=submit value=Search>").
      const name = getAccessibleName(el) || (el.tagName === "INPUT" ? (el.value || "").trim() : "");
      if (!name) return;
      const key = name + "§" + (el.getAttribute("href") || el.tagName);
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ name, element: el });
    });
    return out;
  }

  /* ---------- scanned-notice OCR ----------
   * Government portals publish notices as scans (images / image-only
   * PDFs) that every text-based feature is blind to. The user picks a
   * scan, the gateway's /translate/ocr endpoint (Tesseract) extracts
   * the text, and the result runs through the same simplify→translate
   * →TTS pipeline as everything else.
   */

  // Classify an element as an OCR-able target: a visible image, or a
  // link whose URL path ends in .pdf (query string ignored). Returns
  // { kind: "image"|"pdf", url } or null.
  function describeOcrTarget(el) {
    if (!el || !el.tagName) return null;
    if (el.tagName === "IMG") {
      if (!isVisible(el)) return null;
      const url = el.currentSrc || el.src || "";
      return url ? { kind: "image", url } : null;
    }
    const link = el.closest ? el.closest("a[href]") : null;
    if (link) {
      let path = "";
      try {
        path = new URL(link.href, document.baseURI).pathname;
      } catch {
        return null;
      }
      if (/\.pdf$/i.test(path)) return { kind: "pdf", url: link.href };
    }
    return null;
  }

  // Which OCR language hint to send. "auto" maps to ori+eng on the
  // server, which covers the common Odia/English notice mix — only a
  // Hindi page needs the explicit hint (hin isn't in the auto set).
  function ocrLangHint(pageLangNow) {
    return pageLangNow === "hi" ? "hi" : "auto";
  }

  async function probeGateway() {
    try {
      const r = await fetch(`${CONFIG.gateway}/healthz`, {
        cache: "no-store",
      });
      return r.ok;
    } catch {
      return false;
    }
  }

  /* ---------- styles (scoped to Shadow DOM) ---------- */
  const FONT_FACE_CSS = `
    @font-face {
      font-family: 'Noto Sans Oriya';
      font-style: normal;
      font-weight: 400;
      font-display: swap;
      src: url(data:font/woff2;base64,${NOTO_ORIYA_WOFF2_BASE64}) format('woff2');
      unicode-range: ${ORIYA_UNICODE_RANGE};
    }
  `;
  const STYLE = `
    ${FONT_FACE_CSS}
    :host { all: initial; }
    * { box-sizing: border-box; font-family: 'Noto Sans Oriya', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
    .fab {
      position: fixed;
      right: 1.25rem;
      bottom: 1.25rem;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: #1a66cc;
      color: white;
      border: 0;
      box-shadow: 0 6px 18px rgba(0,0,0,0.25);
      font-size: 1.6rem;
      cursor: pointer;
      z-index: 2147483647;
    }
    .fab:hover { background: #2d7ad9; }
    .fab:focus-visible { outline: 3px solid #ffcf33; outline-offset: 2px; }

    .panel {
      position: fixed;
      right: 1.25rem;
      bottom: 5.5rem;
      width: min(360px, calc(100vw - 2.5rem));
      background: #0f1419;
      color: #e8edf2;
      border-radius: 14px;
      border: 1px solid #253040;
      box-shadow: 0 18px 40px rgba(0,0,0,0.35);
      padding: 1rem 1rem 0.9rem;
      z-index: 2147483647;
      display: none;
    }
    .panel[data-open="true"] { display: block; }

    .title { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.2rem; }
    .sub { color: #8b96a5; font-size: 0.85rem; margin: 0 0 0.9rem; }

    .row { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.65rem; }
    .row label { font-size: 0.82rem; color: #8b96a5; }

    select.lang {
      flex: 1;
      background: #1b2530;
      color: #e8edf2;
      border: 1px solid #2c3a4c;
      border-radius: 8px;
      padding: 0.4rem 0.55rem;
      font-size: 0.9rem;
    }
    select.lang:focus-visible { outline: 2px solid #ffcf33; outline-offset: 1px; }

    button.action {
      width: 100%;
      background: #1a66cc;
      color: white;
      border: 0;
      border-radius: 10px;
      padding: 0.7rem 1rem;
      font-size: 0.98rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      justify-content: center;
      margin-bottom: 0.55rem;
    }
    button.action:hover:not(:disabled) { background: #2d7ad9; }
    button.action:disabled { opacity: 0.55; cursor: not-allowed; }
    button.action.stop { background: #c7444c; }
    button.action.stop:hover { background: #d85860; }
    button.action.mic { background: #2c7a52; }
    button.action.mic:hover { background: #349062; }
    button.action.mic.recording,
    button.action.voice.recording { background: #c7444c; animation: pulse 1.2s infinite; }
    @keyframes pulse { 50% { box-shadow: 0 0 0 6px rgba(199,68,76,0.35); } }

    .transcript {
      margin-top: 0.3rem;
      padding: 0.55rem 0.7rem;
      background: #1b2530;
      border-radius: 8px;
      border: 1px solid #2c3a4c;
      font-size: 0.9rem;
      color: #d0dce8;
      min-height: 1.2em;
      word-break: break-word;
    }
    .transcript:empty { display: none; }

    .status {
      margin-top: 0.55rem;
      min-height: 1.3rem;
      color: #8b96a5;
      font-size: 0.85rem;
    }
    .status.error { color: #ff9898; }
    .status.ok    { color: #8fdba0; }
    /* Attention-grabbing informational notice ("page is already in
       Odia") — an amber pill rather than a colour change, so a user
       who just clicked a button can't miss the answer. */
    .status.notice {
      color: #ffd25e;
      background: rgba(255, 207, 51, 0.12);
      border: 1px solid rgba(255, 207, 51, 0.5);
      border-radius: 8px;
      padding: 0.4rem 0.6rem;
      font-weight: 600;
      animation: aaas-notice-pop 0.35s ease;
    }
    @keyframes aaas-notice-pop {
      0%   { transform: scale(0.94); opacity: 0.3; }
      55%  { transform: scale(1.03); }
      100% { transform: scale(1); opacity: 1; }
    }

    .meta {
      margin-top: 0.35rem;
      font-size: 0.75rem;
      color: #5e6778;
    }

    label.toggle {
      display: grid;
      grid-template-columns: auto 1fr;
      grid-template-rows: auto auto;
      column-gap: 0.6rem;
      align-items: center;
      padding: 0.55rem 0.7rem;
      background: #1b2530;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      margin-bottom: 0.55rem;
      cursor: pointer;
      user-select: none;
    }
    label.toggle:hover { border-color: #3a4c63; }
    label.toggle input[type="checkbox"] {
      grid-row: 1 / span 2;
      width: 18px;
      height: 18px;
      accent-color: #1a66cc;
      cursor: pointer;
    }
    label.toggle .toggle-text {
      font-size: 0.92rem;
      color: #e8edf2;
      font-weight: 500;
    }
    label.toggle .toggle-hint {
      font-size: 0.76rem;
      color: #8b96a5;
    }

    .read-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 0.4rem;
      margin-bottom: 0.55rem;
    }
    .read-row button.action { margin-bottom: 0; }
    button.pause {
      width: 44px;
      padding: 0.7rem 0;
      background: #1b2530;
      border: 1px solid #2c3a4c;
      color: #e8edf2;
      border-radius: 10px;
      font-size: 1rem;
      cursor: pointer;
      display: none;
    }
    button.pause:hover:not(:disabled) { background: #24303e; }
    .read-row[data-playing="true"] button.pause { display: block; }

    .shortcuts-link {
      display: inline-block;
      margin-top: 0.25rem;
      margin-bottom: 0.3rem;
      background: none;
      border: 0;
      padding: 0;
      color: #6e95cc;
      font-size: 0.8rem;
      cursor: pointer;
      text-decoration: underline dotted;
    }
    .shortcuts-link:hover { color: #8fb0e0; }

    .shortcuts-overlay {
      position: absolute;
      right: 1rem;
      bottom: 1rem;
      left: 1rem;
      background: #1b2530;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      padding: 0.8rem 0.9rem;
      font-size: 0.82rem;
      color: #d0dce8;
      display: none;
      z-index: 10;
    }
    .shortcuts-overlay[data-open="true"] { display: block; }
    .shortcuts-overlay h4 {
      margin: 0 0 0.5rem;
      font-size: 0.88rem;
      color: #e8edf2;
    }
    .shortcuts-overlay dl {
      margin: 0;
      display: grid;
      grid-template-columns: auto 1fr;
      row-gap: 0.28rem;
      column-gap: 0.8rem;
    }
    .shortcuts-overlay dt {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      color: #ffcf33;
    }
    .shortcuts-overlay dd { margin: 0; }
    .shortcuts-overlay .close-overlay {
      position: absolute;
      top: 0.3rem;
      right: 0.5rem;
      background: none;
      border: 0;
      color: #8b96a5;
      cursor: pointer;
      font-size: 1rem;
    }

    .ocr-overlay {
      position: absolute;
      right: 1rem;
      bottom: 1rem;
      left: 1rem;
      background: #1b2530;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      padding: 0.8rem 0.9rem;
      font-size: 0.85rem;
      color: #d0dce8;
      display: none;
      z-index: 11;
    }
    .ocr-overlay[data-open="true"] { display: block; }
    .ocr-overlay h4 {
      margin: 0 0 0.5rem;
      font-size: 0.88rem;
      color: #e8edf2;
    }
    .ocr-overlay .ocr-text {
      max-height: 11rem;
      overflow-y: auto;
      user-select: text;
      -webkit-user-select: text;
      line-height: 1.6;
      white-space: pre-wrap;
      background: #141c26;
      border: 1px solid #2c3a4c;
      border-radius: 8px;
      padding: 0.5rem 0.6rem;
    }
    .ocr-overlay .ocr-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.6rem;
    }
    .ocr-overlay .ocr-actions button {
      flex: 1;
      background: #2563b0;
      border: 0;
      border-radius: 8px;
      color: #fff;
      padding: 0.45rem 0.5rem;
      font-size: 0.82rem;
      cursor: pointer;
    }
    .ocr-overlay .ocr-actions button:hover { background: #2f74c8; }
    .ocr-overlay .close-ocr {
      position: absolute;
      top: 0.3rem;
      right: 0.5rem;
      background: none;
      border: 0;
      color: #8b96a5;
      cursor: pointer;
      font-size: 1rem;
    }
  `;

  /* ---------- structure-aware DOM walker ----------
   * Emits "atoms" in reading order: headings, links, buttons, form
   * fields, images-with-alt, and prose runs between them. Each atom
   * carries a role-prefix ("Heading level 2, ") so the TTS output
   * resembles what a real screen reader would say — the thing that
   * separates accessibility from "read text aloud". The structure
   * prefixes are pre-warmed into phraseCache on panel open, so their
   * playback is effectively free.
   */

  const INTERACTIVE_SELECTOR =
    'a[href], button, input:not([type="hidden"]), select, textarea, summary, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="menuitem"], [role="tab"], [role="switch"], [tabindex]:not([tabindex="-1"])';

  const WALKER_SKIP_TAGS = new Set([
    "SCRIPT", "STYLE", "NOSCRIPT", "NAV", "FOOTER",
    "IFRAME", "SVG", "CANVAS", "AUDIO", "VIDEO", "TEMPLATE",
  ]);

  function isVisible(el) {
    if (!el || !(el instanceof Element)) return false;
    if (el.getAttribute("aria-hidden") === "true") return false;
    // offsetParent is null for display:none; fast path, skips a
    // getComputedStyle call on the common case.
    if (el.offsetParent === null && el.tagName !== "BODY") {
      const s = getComputedStyle(el);
      if (s.display === "none" || s.visibility === "hidden") return false;
    }
    return true;
  }

  function dereferenceLabelledBy(el) {
    const ids = (el.getAttribute("aria-labelledby") || "")
      .split(/\s+/).filter(Boolean);
    if (!ids.length) return null;
    const parts = ids
      .map((id) => document.getElementById(id)?.textContent?.trim())
      .filter(Boolean);
    return parts.length ? parts.join(" ") : null;
  }

  function getAccessibleName(el) {
    if (!el) return null;

    // aria-labelledby points at another element's visible text, so it
    // still wins — the pointed-at label IS what the user sees.
    const byId = dereferenceLabelledBy(el);
    if (byId) return byId;

    const tag = el.tagName;

    // <img> has no textContent; alt is the intended caption.
    if (tag === "IMG") return (el.getAttribute("alt") || "").trim() || null;

    // Form controls don't have textContent of their own; fall back to
    // the linked <label>, then aria-label, then placeholder.
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
      if (el.id) {
        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (lbl) return lbl.textContent.trim();
      }
      const anc = el.closest("label");
      if (anc) {
        const clone = anc.cloneNode(true);
        clone.querySelectorAll("input, select, textarea").forEach((n) => n.remove());
        const t = clone.textContent.trim();
        if (t) return t;
      }
      const aria = el.getAttribute("aria-label");
      if (aria && aria.trim()) return aria.trim();
      const ph = el.getAttribute("placeholder");
      if (ph && ph.trim()) return ph.trim();
      return null;
    }

    // For links / buttons / everything else: speak what the user sees.
    // Visible text wins over aria-label so the spoken text matches the
    // rendered text. aria-label is only consulted when there's no
    // visible text (icon buttons: `<button aria-label="Menu">☰</button>`
    // — one glyph, no letters, so we use "Menu").
    const visible = (el.textContent || "").replace(/\s+/g, " ").trim();
    const visibleLetters = (visible.match(/\p{L}/gu) || []).length;
    if (visible && visibleLetters >= 2) return visible;
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim();
    if (visible) return visible;
    const title = el.getAttribute("title");
    if (title && title.trim()) return title.trim();
    return null;
  }

  function describeField(el) {
    const name = getAccessibleName(el) || "unlabelled";
    const tag = el.tagName;
    let type;
    if (tag === "INPUT") type = (el.getAttribute("type") || "text").toLowerCase();
    else if (tag === "SELECT") type = "dropdown";
    else if (tag === "TEXTAREA") type = "text area";
    else type = tag.toLowerCase();
    const parts = [name, type];
    if (el.required) parts.push("required");
    if (el.disabled) parts.push("disabled");
    // Value / state. Booleans report checked/unchecked; anything else
    // reports its current value or "empty".
    if (type === "checkbox" || type === "radio") {
      parts.push(el.checked ? "checked" : "unchecked");
    } else if (tag === "SELECT") {
      const opt = el.options[el.selectedIndex];
      parts.push(opt && opt.text ? `${opt.text} selected` : "nothing selected");
    } else {
      const v = (el.value || "").trim();
      parts.push(v ? `value: ${v.slice(0, 80)}` : "empty");
    }
    return parts.join(", ");
  }

  // Role-prefix strings the Announcer reads before the element's
  // accessible name ("Button: Submit"). Keyed by target language so
  // an Odia reader hears an Odia role announcement instead of the
  // Latin characters silently vanishing through the Odia tokeniser.
  // ``null`` for any missing lang falls back to the English table.
  const PREFIX_STRINGS = {
    en: {
      heading: (lvl) => `Heading level ${lvl}, `,
      link: "Link, ",
      button: "Button, ",
      checkbox: "Checkbox, ",
      radio: "Radio button, ",
      switch: "Switch, ",
      field: "Form field, ",
      image: "Image, ",
    },
    or: {
      heading: (lvl) => `ଶୀର୍ଷକ ସ୍ତର ${lvl}, `,
      link: "ଲିଙ୍କ, ",
      button: "ବଟନ, ",
      checkbox: "ଚେକ୍ ବକ୍ସ, ",
      radio: "ରେଡିଓ ବଟନ, ",
      switch: "ସ୍ୱିଚ, ",
      field: "ଫର୍ମ କ୍ଷେତ୍ର, ",
      image: "ଛବି, ",
    },
    hi: {
      heading: (lvl) => `शीर्षक स्तर ${lvl}, `,
      link: "लिंक, ",
      button: "बटन, ",
      checkbox: "चेकबॉक्स, ",
      radio: "रेडियो बटन, ",
      switch: "स्विच, ",
      field: "फ़ॉर्म फ़ील्ड, ",
      image: "चित्र, ",
    },
  };

  // Look up the localised role announcement for an atom. Falls back to
  // English if the target language doesn't have an entry (keeps the
  // widget usable for languages we haven't translated yet).
  function prefixFor(atom, tgt) {
    if (!atom || !atom.role) return "";
    const table = PREFIX_STRINGS[tgt] || PREFIX_STRINGS.en;
    const fallback = PREFIX_STRINGS.en;
    const entry = table[atom.role] ?? fallback[atom.role];
    if (!entry) return "";
    if (typeof entry === "function") return entry(atom.level ?? 1);
    return entry;
  }

  function describeAtom(el) {
    const tag = el.tagName;
    const role = el.getAttribute("role");
    if (/^H[1-6]$/.test(tag)) {
      const name = getAccessibleName(el);
      if (!name) return null;
      return { text: name, role: "heading", level: Number(tag[1]), element: el };
    }
    if (tag === "A" || role === "link") {
      const name = getAccessibleName(el) || (el.getAttribute("href") || "").split("/").filter(Boolean).pop() || "link";
      return { text: name, role: "link", element: el };
    }
    if (tag === "BUTTON" || role === "button" || tag === "SUMMARY") {
      const name = getAccessibleName(el) || "unnamed button";
      return { text: name, role: "button", element: el };
    }
    if (tag === "INPUT") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "hidden") return null;
      if (type === "checkbox" || type === "radio") {
        const name = getAccessibleName(el) || "unlabelled";
        const state = el.checked ? "checked" : "unchecked";
        return { text: `${name}, ${state}`, role: type, element: el };
      }
      return { text: describeField(el), role: "field", element: el };
    }
    if (tag === "TEXTAREA" || tag === "SELECT") {
      return { text: describeField(el), role: "field", element: el };
    }
    if (tag === "IMG") {
      const alt = (el.getAttribute("alt") || "").trim();
      if (!alt) return null;
      return { text: alt, role: "image", element: el };
    }
    if (role === "checkbox" || role === "radio" || role === "switch") {
      const name = getAccessibleName(el) || "unlabelled";
      const state = el.getAttribute("aria-checked") === "true" ? "checked" : "unchecked";
      return { text: `${name}, ${state}`, role, element: el };
    }
    return null;
  }

  function isAtomicTag(tag) {
    return (
      /^H[1-6]$/.test(tag) ||
      tag === "A" || tag === "BUTTON" || tag === "SUMMARY" ||
      tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" ||
      tag === "IMG"
    );
  }

  function splitLongProse(text, maxChars) {
    const out = [];
    const sentences = text
      .split(/(?<=[।?!])\s+|(?<=[.])\s+(?=[A-Z])/g)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!sentences.length) return [text.slice(0, maxChars)];
    let buf = "";
    for (const s of sentences) {
      if ((buf + " " + s).length > maxChars && buf) {
        out.push(buf);
        buf = s;
      } else {
        buf = buf ? buf + " " + s : s;
      }
    }
    if (buf) out.push(buf);
    return out;
  }

  // Returns an ordered array of atoms. Prose runs between interactive
  // elements are collected as {role:"prose"} atoms — that way the TTS
  // pipeline can chunk them for translate latency without breaking
  // mid-sentence and without announcing "paragraph" for every block.
  function collectAtoms(root) {
    const out = [];
    let proseBuf = [];
    const flushProse = () => {
      if (!proseBuf.length) return;
      const joined = proseBuf.join(" ").replace(/\s+/g, " ").trim();
      proseBuf = [];
      if (!joined) return;
      for (const piece of splitLongProse(joined, CONFIG.maxChars)) {
        out.push({ text: piece, prefix: "", role: "prose", element: null });
      }
    };
    const widgetHost = document.querySelector("[data-aaas-widget]");
    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          if (node.nodeType === Node.TEXT_NODE) {
            const p = node.parentElement;
            if (!p) return NodeFilter.FILTER_REJECT;
            if (WALKER_SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT;
            if (widgetHost && widgetHost.contains(p)) return NodeFilter.FILTER_REJECT;
            if (p.getAttribute("aria-hidden") === "true") return NodeFilter.FILTER_REJECT;
            if (!isVisible(p)) return NodeFilter.FILTER_REJECT;
            // Text inside an atomic element is consumed by the atom
            // itself via getAccessibleName — skip here so we don't
            // double-speak the button's label.
            let cur = p;
            while (cur && cur !== root) {
              if (isAtomicTag(cur.tagName)) return NodeFilter.FILTER_REJECT;
              cur = cur.parentElement;
            }
            return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
          }
          // Element node.
          const el = node;
          if (WALKER_SKIP_TAGS.has(el.tagName)) return NodeFilter.FILTER_REJECT;
          if (widgetHost && widgetHost.contains(el)) return NodeFilter.FILTER_REJECT;
          if (el.getAttribute("aria-hidden") === "true") return NodeFilter.FILTER_REJECT;
          if (!isVisible(el)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        },
      }
    );
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) {
        const t = node.nodeValue.trim();
        if (t) proseBuf.push(t);
        continue;
      }
      const el = node;
      if (isAtomicTag(el.tagName) || el.hasAttribute("role")) {
        const atom = describeAtom(el);
        if (atom) {
          flushProse();
          out.push(atom);
        }
      }
    }
    flushProse();
    return out;
  }

  /* ---------- API clients ---------- */

  // Text the TTS service can't voice — whitespace or punctuation only, which
  // normalises to empty and 400s — has no speakable letter or digit in any
  // script. Detect it locally so a separator unit like "·" never costs a
  // request or logs a browser console error; callers already skip on throw.
  const SPEAKABLE_RE = /[\p{L}\p{N}]/u;
  function isSpeakable(text) {
    return typeof text === "string" && SPEAKABLE_RE.test(text);
  }

  // Phrase- and chunk-level TTS. Cache-first: identical {lang, text}
  // requests hit the in-memory blob map and return in microseconds,
  // which is the single biggest lever for the hover/focus reader
  // path where structure prefixes ("Heading level 2, ") repeat
  // hundreds of times per session.
  async function synthesise(chunk, lang, { signal } = {}) {
    if (!isSpeakable(chunk)) {
      throw new TtsError(chunk, lang, new Error("nothing speakable"));
    }
    const k = phraseKey(lang || "", chunk);
    const hit = phraseCache.get(k);
    if (hit) return hit;
    // Persistent (cross-reload) hit: replay the stored clip instead of
    // regenerating — skips the on-device model run / a gateway round-trip.
    const storedAudio = await persistentCache.get("tts", k);
    if (storedAudio) {
      phraseCache.set(k, storedAudio);
      return storedAudio;
    }
    if (ON_DEVICE) {
      const od = await getOnDeviceBackend();
      if (od) {
        try {
          const blob = await od.speak(chunk, lang);
          phraseCache.set(k, blob);
          persistentCache.put("tts", k, blob);
          return blob;
        } catch (err) {
          // Fall through to the gateway. Both paths use Meta MMS-TTS, so
          // the user still gets the same voice — just from the server
          // instead of WebAssembly when on-device inference hiccups.
          console.warn("[AaaS] on-device speak failed, using gateway:", err);
        }
      }
    }
    // TTS synthesis can take well over 6 s on a cold model load or when the
    // CPU is briefly busy — server-side rtf spikes to 2-3x under load (see
    // .run-logs/tts.log, where short inputs occasionally took 7-22 s). The
    // gateway's own read timeout is 30 s, so the client must wait at least
    // as long; a 6 s abort here was surfacing spurious "TTS unavailable"
    // errors mid-read even though the server went on to answer fine.
    const t = withTimeout(30000, signal);
    try {
      const body = { text: chunk };
      if (lang) body.lang = lang;
      const response = await fetch(`${CONFIG.gateway}/tts/synthesise`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": CONFIG.apiKey,
        },
        body: JSON.stringify(body),
        signal: t.signal,
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const j = await response.json();
          if (j.detail) detail = j.detail;
        } catch {}
        throw new TtsError(chunk, lang, new Error(detail));
      }
      const blob = await response.blob();
      phraseCache.set(k, blob);
      persistentCache.put("tts", k, blob);
      return blob;
    } catch (err) {
      if (err instanceof TtsError) throw err;
      throw new TtsError(chunk, lang, err);
    } finally {
      t.clear();
    }
  }

  // Map our codes to Google's (identical for or/hi/en); anything else →
  // "auto" so Google detects the source itself.
  function googleCode(code) {
    return ["or", "hi", "en"].includes(code) ? code : "auto";
  }

  // Translate via the extension's background worker (Google Translate). The
  // worker bypasses page CSP + CORS, so this works on any site. Communicates
  // over window.postMessage because the widget runs in the page's MAIN world
  // and can't touch chrome.runtime directly.
  let _bridgeSeq = 0;
  function googleTranslateViaBridge(text, src, tgt, timeoutMs) {
    return new Promise((resolve, reject) => {
      const id = "tr-" + ++_bridgeSeq;
      const onMsg = (ev) => {
        if (ev.source !== window) return;
        const d = ev.data;
        if (!d || d.source !== "aaas-bridge" || d.kind !== "translate-res" || d.id !== id) {
          return;
        }
        window.removeEventListener("message", onMsg);
        clearTimeout(timer);
        if (d.ok && typeof d.text === "string") resolve(d.text);
        else reject(new Error(d.error || "translate bridge failed"));
      };
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMsg);
        reject(new Error("translate bridge timed out"));
      }, Math.max(timeoutMs || 0, 8000));
      window.addEventListener("message", onMsg);
      window.postMessage(
        { source: "aaas-widget", kind: "translate-req", id, text, src: googleCode(src), tgt: googleCode(tgt) },
        "*",
      );
    });
  }

  // Direct Google Translate fetch — used by plain <script> embeds (no
  // extension bridge). Subject to the page's CSP/CORS, so it can be blocked
  // on strict sites; callers fall back to the gateway when it throws. Bounded
  // by a timeout so a hung connection (captive portal, flaky network) doesn't
  // stall the fallback.
  async function googleTranslateDirect(text, src, tgt, signal, timeoutMs) {
    const url =
      "https://translate.googleapis.com/translate_a/single" +
      `?client=gtx&sl=${encodeURIComponent(googleCode(src))}&tl=${encodeURIComponent(googleCode(tgt))}` +
      `&dt=t&q=${encodeURIComponent(text)}`;
    const t = withTimeout(Math.max(timeoutMs || 0, 8000), signal);
    try {
      const r = await fetch(url, { signal: t.signal, cache: "no-store" });
      if (!r.ok) throw new Error("google HTTP " + r.status);
      const data = await r.json();
      if (!Array.isArray(data) || !Array.isArray(data[0])) {
        throw new Error("google: unexpected response shape");
      }
      return data[0].map((seg) => (seg && seg[0]) || "").join("");
    } finally {
      t.clear();
    }
  }

  // Gateway translate (IndicTrans2) — the preferred path when the gateway
  // is reachable, and the reason the portable demo bundle keeps working
  // with no internet.
  async function gatewayTranslate(text, srcLang, tgtLang, { signal, timeoutMs }) {
    const t = withTimeout(timeoutMs, signal);
    try {
      const response = await fetch(`${CONFIG.gateway}/translate/translate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": CONFIG.apiKey,
        },
        body: JSON.stringify({ text, src_lang: srcLang, tgt_lang: tgtLang }),
        signal: t.signal,
      });
      if (!response.ok) {
        throw new TranslateError(text, tgtLang, new Error(`HTTP ${response.status}`));
      }
      const json = await response.json();
      return json.text;
    } finally {
      t.clear();
    }
  }

  // Translate one chunk. Strategy: prefer the AaaS gateway (IndicTrans2 — the
  // clearest, most formal Odia) whenever it's reachable, and fall back to
  // Google Translate so a plain standalone embed still works on any site with
  // no local services. Reachability is cached so a no-services embed pays at
  // most one failed gateway probe, then goes straight to Google.
  // Cache-first at both the in-memory and cross-reload (IndexedDB) layers.
  //
  // null = gateway not yet probed; true/false = last known reachability.
  let _gatewayTranslateReachable = null;
  async function translateChunk(text, srcLang, tgtLang, { signal, timeoutMs = 6000 } = {}) {
    if (srcLang === tgtLang) return text;
    const k = translateKey(srcLang, tgtLang, text);
    const hit = translateCache.get(k);
    if (hit !== undefined) return hit;
    const storedTr = await persistentCache.get("translate", k);
    if (storedTr !== undefined) {
      translateCache.set(k, storedTr);
      return storedTr;
    }

    const store = (out) => {
      translateCache.set(k, out);
      persistentCache.put("translate", k, out);
      return out;
    };

    const googleStep = async () => {
      const out = EXT_BRIDGE
        ? await googleTranslateViaBridge(text, srcLang, tgtLang, timeoutMs)
        : await googleTranslateDirect(text, srcLang, tgtLang, signal, timeoutMs);
      if (typeof out === "string" && out.trim()) return store(out);
      throw new Error("empty translation");
    };

    // Primary: AaaS gateway (IndicTrans2), whenever it's reachable.
    if (_gatewayTranslateReachable !== false) {
      try {
        const out = store(
          await gatewayTranslate(text, srcLang, tgtLang, { signal, timeoutMs }),
        );
        _gatewayTranslateReachable = true;
        return out;
      } catch (err) {
        if (signal && signal.aborted) throw new TranslateError(text, tgtLang, err);
        // Gateway down/unreachable — remember it so we don't retry on every
        // chunk, and fall through to Google for this and subsequent calls.
        _gatewayTranslateReachable = false;
        console.warn(
          "[AaaS] gateway translate unavailable, using Google:",
          err?.message || err,
        );
      }
    }

    // Fallback: Google Translate (also the primary once the gateway is known
    // unreachable — e.g. a standalone extension with no services running).
    try {
      return await googleStep();
    } catch (err) {
      if (err instanceof TranslateError) throw err;
      throw new TranslateError(text, tgtLang, err);
    }
  }

  // Easy Read: rule-based simplification via the translate service's
  // /simplify route (reached through the gateway's /translate catch-all).
  // Cache-first like translateChunk, reusing the "translate" IndexedDB
  // store under a distinct key prefix so no schema bump is needed.
  // Unlike translate there is no Google fallback — a failed fetch
  // throws and the caller decides what to show.
  async function simplifyChunk(text, lang, { signal, timeoutMs = 20000 } = {}) {
    const k = "simplify§" + lang + ":" + text;
    const hit = translateCache.get(k);
    if (hit !== undefined) return hit;
    const stored = await persistentCache.get("translate", k);
    if (stored !== undefined) {
      translateCache.set(k, stored);
      return stored;
    }
    const t = withTimeout(timeoutMs, signal);
    try {
      const response = await fetch(`${CONFIG.gateway}/translate/simplify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": CONFIG.apiKey,
        },
        body: JSON.stringify({ text, lang }),
        signal: t.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json = await response.json();
      const out = typeof json.text === "string" && json.text ? json.text : text;
      translateCache.set(k, out);
      persistentCache.put("translate", k, out);
      return out;
    } finally {
      t.clear();
    }
  }

  // Fetch a scanned document (image or PDF) and run it through the
  // gateway's OCR endpoint. No cache — scans are picked explicitly
  // and rarely twice in a session. Throws with a readable message on
  // any failure; the caller shows it in the status pill.
  async function ocrFetchAndRecognize(url, lang, { timeoutMs = 60000 } = {}) {
    const t = withTimeout(timeoutMs);
    try {
      const srcResp = await fetch(url, { signal: t.signal });
      if (!srcResp.ok) {
        throw new Error(`could not fetch the document (HTTP ${srcResp.status})`);
      }
      const blob = await srcResp.blob();
      if (blob.size > 15000000) {
        throw new Error("document too large (15 MB max)");
      }
      const fd = new FormData();
      fd.append("file", blob, /\.pdf($|\?)/i.test(url) ? "scan.pdf" : "scan.png");
      fd.append("lang", lang || "auto");
      const response = await fetch(`${CONFIG.gateway}/translate/ocr`, {
        method: "POST",
        headers: { "X-API-Key": CONFIG.apiKey },
        body: fd,
        signal: t.signal,
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          detail = (await response.json()).detail || detail;
        } catch {}
        throw new Error(detail);
      }
      return await response.json();
    } finally {
      t.clear();
    }
  }

  async function transcribe(blob, languageHint) {
    if (ON_DEVICE) {
      const od = await getOnDeviceBackend();
      if (od) {
        try {
          return await od.transcribe(blob, languageHint);
        } catch (err) {
          console.warn("[AaaS] on-device transcribe failed, using gateway:", err);
        }
      }
    }
    const fd = new FormData();
    fd.append("audio", blob, "speech.webm");
    if (languageHint) fd.append("language", languageHint);
    const response = await fetch(`${CONFIG.gateway}/stt/transcribe`, {
      method: "POST",
      headers: { "X-API-Key": CONFIG.apiKey },
      body: fd,
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const j = await response.json();
        if (j.detail) detail = j.detail;
      } catch {}
      throw new Error(detail);
    }
    return response.json();
  }

  /* ---------- playback ---------- */

  // Streaming player: caller reset()s, enqueue()s blobs as they
  // arrive, calls finish() once no more blobs will be produced, and
  // awaits drain() to hear the whole thing. The drain loop blocks on
  // a promise when the queue is empty so we don't busy-poll while
  // synthesis catches up.
  class Player {
    constructor() {
      this.audio = new Audio();
      this.queue = [];
      this.playing = false;
      this.stopped = false;
      this.feedDone = false;
      this._resume = null;
      // Ring buffer of recently-played blobs for ← (replay previous).
      this.history = [];
      this.historyMax = 3;
      // onAdvance fires when drain() moves to the next blob. UI uses
      // this to update the "playing N/M" progress chip.
      this.onAdvance = null;
      // Cached last blob URL so we can revoke it on skip without
      // waiting for the next drain iteration.
      this._currentUrl = null;
    }
    reset() {
      this.queue = [];
      this.stopped = false;
      this.feedDone = false;
      this._resume = null;
      this.history = [];
      this._skipRequested = false;
    }
    _wake() {
      if (this._resume) {
        const r = this._resume;
        this._resume = null;
        r();
      }
    }
    stop() {
      this.stopped = true;
      this.feedDone = true;
      this.queue = [];
      try {
        this.audio.pause();
        this.audio.src = "";
      } catch {}
      if (this._currentUrl) {
        try { URL.revokeObjectURL(this._currentUrl); } catch {}
        this._currentUrl = null;
      }
      this.playing = false;
      this._wake();
    }
    pause() {
      if (!this.playing) return false;
      try { this.audio.pause(); } catch {}
      return true;
    }
    resume() {
      if (!this.audio.src) return false;
      try { this.audio.play(); } catch {}
      return true;
    }
    isPaused() {
      return this.playing && this.audio.paused;
    }
    // Stop the current blob mid-play and advance to the next enqueued
    // blob. Does NOT empty the queue — used for → shortcut.
    skipCurrent() {
      if (!this.playing) return false;
      this._skipRequested = true;
      try { this.audio.pause(); } catch {}
      // The onended/onerror-style promise resolves via the audio's
      // "pause" event fallback below.
      if (this._onAdvance) this._onAdvance();
      return true;
    }
    // Push the last-played blob back onto the front of the queue.
    replayPrevious() {
      if (!this.history.length) return false;
      const prev = this.history[this.history.length - 1];
      this.queue.unshift(prev);
      this._skipRequested = true;
      try { this.audio.pause(); } catch {}
      if (this._onAdvance) this._onAdvance();
      return true;
    }
    enqueue(blob) {
      if (this.stopped || this.feedDone) return;
      this.queue.push(blob);
      this._wake();
    }
    finish() {
      this.feedDone = true;
      this._wake();
    }
    async drain() {
      if (this.playing) return;
      this.playing = true;
      try {
        while (!this.stopped && (!this.feedDone || this.queue.length)) {
          if (!this.queue.length) {
            await new Promise((resolve) => {
              this._resume = resolve;
            });
            continue;
          }
          const blob = this.queue.shift();
          const url = URL.createObjectURL(blob);
          this._currentUrl = url;
          this.audio.src = url;
          this._skipRequested = false;
          if (this.onAdvance) {
            try { this.onAdvance(); } catch {}
          }
          try {
            await this.audio.play();
            await new Promise((resolve) => {
              const done = () => resolve();
              this._onAdvance = done;
              this.audio.onended = done;
              this.audio.onerror = done;
            });
          } finally {
            this._onAdvance = null;
            URL.revokeObjectURL(url);
            if (this._currentUrl === url) this._currentUrl = null;
            // Push to history unless we're unwinding a stop.
            if (!this.stopped) {
              this.history.push(blob);
              while (this.history.length > this.historyMax) this.history.shift();
            }
          }
        }
      } finally {
        this.playing = false;
      }
    }
    // Back-compat shim: fire-and-forget a full blob list. Used by
    // callers that have already batched their synthesis and just want
    // ordered playback. New streaming callers should use reset +
    // enqueue + finish + drain directly.
    async play(blobs) {
      this.reset();
      for (const b of blobs) this.queue.push(b);
      this.finish();
      await this.drain();
    }
  }

  /* ---------- announcer (focus / hover / selection) ----------
   * Lightweight, single-utterance pipeline separate from the main
   * Read-this-page Player. When the user tabs / hovers / selects,
   * the previous utterance is cancelled (both in-flight fetches and
   * the audio itself) and only the newest announcement plays. Caches
   * (translateCache, phraseCache) make repeat announcements — tab
   * back to the same field — effectively instantaneous.
   */
  class Announcer {
    constructor({ getTargetLang, getSourceLang }) {
      this.getTargetLang = getTargetLang;
      this.getSourceLang = getSourceLang;
      this.audio = new Audio();
      this._abort = null;
    }
    cancel() {
      if (this._abort) {
        try { this._abort.abort(); } catch {}
      }
      this._abort = null;
      try { this.audio.pause(); this.audio.src = ""; } catch {}
    }
    async announce(atom) {
      this.cancel();
      const ac = new AbortController();
      this._abort = ac;
      const tgt = this.getTargetLang();
      const src = this.getSourceLang();
      const tgtPrefix = prefixFor(atom, tgt);
      if (!(atom.text || "").trim() && !tgtPrefix.trim()) return;
      // Route every neural request through the target-language MMS
      // checkpoint so a user who picked Odia only ever hears the Odia
      // voice. The alternative — swapping in source-language MMS when
      // translate returns off-script — leaked the English voice on
      // demo-site links that aren't in the mock corpus (bug: both
      // English and Odia voices speaking after a hover).
      let spoken = tgtPrefix + (atom.text || "");
      const lang = tgt;
      try {
        if (src && src !== tgt && atom.text) {
          const translated = await translateChunk(atom.text, src, tgt, {
            signal: ac.signal,
          });
          if (looksLikeTargetScript(translated, tgt)) {
            spoken = tgtPrefix + translated;
          } else {
            // Translate returned source-script text (mock passthrough
            // or a real engine giving up). The Indic MMS tokeniser
            // drops Latin tokens, so the body goes silent — but the
            // target-script prefix still speaks, which at minimum
            // announces the role. Strip the "[src->tgt] " annotation
            // first so it doesn't leak into the audio pipeline.
            const cleaned = stripPassthroughAnnotation(translated);
            spoken = tgtPrefix + cleaned;
          }
        }
      } catch (err) {
        // Translate failed — speak the source text after the target
        // prefix. Off-script body will be swallowed by the Indic
        // tokeniser, but the prefix still conveys the role and we
        // never switch away from the target voice.
        spoken = tgtPrefix + (atom.text || "");
      }
      if (ac.signal.aborted) return;
      console.debug("[AaaS/hover]", {
        visible: atom.text,
        role: atom.role,
        src,
        tgt,
        spoken,
        lang,
      });
      try {
        const blob = await synthesise(spoken, lang, { signal: ac.signal });
        if (ac.signal.aborted) return;
        const url = URL.createObjectURL(blob);
        this.audio.src = url;
        this.audio.onended = () => URL.revokeObjectURL(url);
        this.audio.onerror = () => URL.revokeObjectURL(url);
        await this.audio.play().catch((e) => {
          console.warn(
            "[AaaS/hover] audio.play blocked — click anywhere on the page once to unlock autoplay.",
            e?.name || e?.message || "unknown",
          );
        });
      } catch (err) {
        // TTS failed — stay silent. No browser-voice fallback:
        // MMS is the only engine.
      }
    }
  }

  function debounce(fn, ms) {
    let timer = null;
    const wrapped = (...args) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => { timer = null; fn(...args); }, ms);
    };
    wrapped.cancel = () => { if (timer) clearTimeout(timer); timer = null; };
    return wrapped;
  }

  /* ---------- mic recorder ---------- */

  class Recorder {
    constructor() {
      this.stream = null;
      this.recorder = null;
      this.chunks = [];
      this.timer = null;
      this.onAutoStop = null;
    }
    isRecording() {
      return !!this.recorder && this.recorder.state === "recording";
    }
    async start({ onAutoStop } = {}) {
      if (this.isRecording()) return;
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone API unavailable");
      }
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.chunks = [];
      this.onAutoStop = onAutoStop || null;
      // Prefer audio/webm which Chromium + Firefox both emit. The STT
      // service decodes webm/Opus via PyAV (libsndfile does not).
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";
      this.recorder = mime
        ? new MediaRecorder(this.stream, { mimeType: mime })
        : new MediaRecorder(this.stream);
      this.recorder.ondataavailable = (e) => {
        if (e.data && e.data.size) this.chunks.push(e.data);
      };
      // Single source of truth for "recording finished" — called on
      // both user-initiated stop() and auto-stop. Resolves any pending
      // stop() promise and fires onAutoStop if set.
      this._stopPromise = null;
      this._stopResolver = null;
      this.recorder.onstop = () => {
        const blob = new Blob(this.chunks, {
          type: this.recorder?.mimeType || "audio/webm",
        });
        this.stream?.getTracks().forEach((t) => t.stop());
        this.stream = null;
        this.recorder = null;
        if (this._stopResolver) this._stopResolver(blob);
        this._stopResolver = null;
        this._stopPromise = null;
        if (this.onAutoStop) {
          const cb = this.onAutoStop;
          this.onAutoStop = null;
          try {
            cb(blob);
          } catch (e) {
            console.warn("[AaaS] onAutoStop failed", e);
          }
        }
      };
      this.recorder.start();
      // Hard stop after maxRecordSeconds so a stuck mic doesn't eat the demo.
      this.timer = setTimeout(() => {
        if (this.isRecording()) this.recorder.stop();
      }, CONFIG.maxRecordSeconds * 1000);
    }
    stop() {
      // User-initiated stop. Clears the auto-stop hook so finishRecording
      // isn't double-invoked. Returns a promise that resolves once the
      // recorder's onstop fires with the final blob.
      if (!this.recorder) return Promise.reject(new Error("no active recorder"));
      clearTimeout(this.timer);
      this.onAutoStop = null;
      if (!this._stopPromise) {
        this._stopPromise = new Promise((resolve) => {
          this._stopResolver = resolve;
        });
      }
      if (this.recorder.state === "recording") this.recorder.stop();
      return this._stopPromise;
    }
  }

  /* ---------- host-page font injection ----------
   * Demo sites (and any host) that reference "Noto Sans Oriya" in their
   * CSS fall back to system fonts on Windows 10/11, where "Kalinga"
   * renders conjuncts poorly, or macOS, which ships no Oriya font at
   * all. Injecting the same @font-face we use in the Shadow DOM lets
   * any existing `font-family: "Noto Sans Oriya", ...` on the host
   * page automatically resolve to our bundled woff2 — no CSS edits
   * needed on the host side. unicode-range confines it to Oriya code
   * points so Latin still renders with the system stack.
   */
  function injectHostFont() {
    if (document.getElementById("__aaas_font_oriya__")) return;
    const el = document.createElement("style");
    el.id = "__aaas_font_oriya__";
    el.textContent = FONT_FACE_CSS;
    (document.head || document.documentElement).appendChild(el);
  }

  /* ---------- dyslexia mode ----------
   * Reformats the host page for readers with dyslexia. We bundle
   * Atkinson Hyperlegible (Latin subset, injected below) so the font
   * swap is guaranteed even on a stock judge laptop; the stack still
   * prefers OpenDyslexic first for readers who installed it, and falls
   * back to Comic Sans MS (ships with Windows + macOS, uneven x-heights)
   * and system-ui.
   *
   * Odia conjunct rendering is fragile: letter-spacing splits the
   * combining marks off the base glyph and the script collapses into
   * visible "base + mark" pieces. So letter-spacing is only applied
   * when the page is English-classified (data-aaas-dyslexia-latin,
   * set by injectDyslexiaStyles), and even then it is explicitly reset
   * on [lang] Indic subtrees and on elements tagged data-aaas-indic by
   * tagIndicElements(). The [lang|=or] block keeps the font swap and
   * line-height bump but deliberately forgoes letter-spacing, and
   * nudges word-spacing instead.
   */
  const ATKINSON_FONT_FACE_CSS = `
    @font-face {
      font-family: 'Atkinson Hyperlegible';
      font-style: normal;
      font-weight: 400;
      font-display: swap;
      src: url(data:font/woff2;base64,${ATKINSON_WOFF2_BASE64}) format('woff2');
      unicode-range: ${LATIN_UNICODE_RANGE};
    }
  `;
  const DYSLEXIA_CSS = `
    html[data-aaas-dyslexia="true"] body,
    html[data-aaas-dyslexia="true"] body * {
      font-family: "OpenDyslexic", "Atkinson Hyperlegible", "Comic Sans MS", Verdana, system-ui, sans-serif !important;
      line-height: 1.9 !important;
      word-spacing: 0.1em !important;
    }
    html[data-aaas-dyslexia="true"] body {
      background: #fbf7ef !important;
      color: #1b1b1b !important;
    }
    html[data-aaas-dyslexia="true"] p,
    html[data-aaas-dyslexia="true"] li,
    html[data-aaas-dyslexia="true"] dd,
    html[data-aaas-dyslexia="true"] blockquote {
      font-size: 1.08em !important;
      max-width: 72ch;
    }
    html[data-aaas-dyslexia="true"] h1,
    html[data-aaas-dyslexia="true"] h2,
    html[data-aaas-dyslexia="true"] h3 {
      line-height: 1.5 !important;
    }
    html[data-aaas-dyslexia="true"] a {
      text-decoration-thickness: 2px !important;
      text-underline-offset: 3px !important;
    }
    /* Odia-aware: the Noto Sans Oriya we inject from the widget handles
       conjuncts correctly, so keep it at the top of the stack for
       elements explicitly marked [lang|="or"]. Demo sites that don't
       mark their Odia spans still fall back safely — the top-level
       rule deliberately omits letter-spacing, which is the single
       property that would corrupt Indic conjunct shaping if applied
       blindly across a multi-script page. */
    html[data-aaas-dyslexia="true"] [lang|="or"],
    html[data-aaas-dyslexia="true"] [lang|="or"] * {
      font-family: "Noto Sans Oriya", "OpenDyslexic", "Atkinson Hyperlegible", "Comic Sans MS", system-ui, sans-serif !important;
      line-height: 2 !important;
      word-spacing: 0.12em !important;
    }
    /* Latin-only letter-spacing. The -latin attribute is set only when
       the page classifies as English; the reset block below wins on
       any Indic subtree so conjunct shaping is never disturbed. The
       resets repeat both html attributes on purpose — they need three
       attribute selectors to out-rank the two-attribute applying rule
       (both carry !important, so specificity decides). */
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] body,
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] body * {
      letter-spacing: 0.04em !important;
    }
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [lang|="or"],
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [lang|="or"] *,
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [lang|="hi"],
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [lang|="hi"] *,
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [data-aaas-indic],
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] [data-aaas-indic] * {
      letter-spacing: normal !important;
    }
    /* Widget's own shadow DOM is isolated by :host { all: initial; },
       so these rules never reach it. But the widget's own host <div>
       inherits a couple of properties — suppress the spacing there so
       the floating button stays round. */
    [data-aaas-widget] { line-height: normal !important; }
  `;

  // Safety net for unmarked Odia/Hindi on English-classified pages:
  // the CSS reset above needs *something* to select, so tag every
  // element whose text contains Indic codepoints. Runs once per
  // toggle-on; text injected later isn't re-tagged (re-toggle re-tags).
  const INDIC_CHAR_RE = /[ऀ-ॿ଀-୿]/;

  function tagIndicElements() {
    if (!document.body || !document.createTreeWalker) return;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    let node;
    while ((node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent || WALKER_SKIP_TAGS.has(parent.tagName)) continue;
      if (parent.closest("[data-aaas-widget]")) continue;
      if (INDIC_CHAR_RE.test(node.nodeValue)) {
        parent.setAttribute("data-aaas-indic", "");
      }
    }
  }

  function untagIndicElements() {
    document.querySelectorAll("[data-aaas-indic]").forEach((el) => {
      el.removeAttribute("data-aaas-indic");
    });
  }

  function injectDyslexiaStyles() {
    document.documentElement.setAttribute("data-aaas-dyslexia", "true");
    if (detectPageLang() === "en") {
      document.documentElement.setAttribute("data-aaas-dyslexia-latin", "true");
      tagIndicElements();
    }
    if (document.getElementById("__aaas_dyslexia__")) return;
    const el = document.createElement("style");
    el.id = "__aaas_dyslexia__";
    el.textContent = ATKINSON_FONT_FACE_CSS + DYSLEXIA_CSS;
    (document.head || document.documentElement).appendChild(el);
  }

  function removeDyslexiaStyles() {
    document.documentElement.removeAttribute("data-aaas-dyslexia");
    document.documentElement.removeAttribute("data-aaas-dyslexia-latin");
    untagIndicElements();
    const el = document.getElementById("__aaas_dyslexia__");
    if (el) el.remove();
  }

  /* ---------- reading ruler ----------
   * A line-focus band for readers who lose their place: one fixed,
   * pointer-events-none <div> whose huge box-shadow dims everything
   * outside the band. It lives in the host page (not the shadow root)
   * so it can cover host content, follows the mouse (rAF-throttled)
   * and jumps to the keyboard focus. Hidden until the first pointer or
   * focus event so enabling it doesn't dim a still page, and hidden
   * again when the pointer leaves the window. Known limitation: the
   * band freezes while the pointer is inside a cross-origin iframe
   * (no mousemove events reach us); keyboard focus still tracks.
   */
  const RULER_BAND_PX = 110;
  let _rulerEl = null;
  let _rulerMove = null;
  let _rulerFocus = null;
  let _rulerLeave = null;

  function positionRuler(centerY) {
    if (!_rulerEl) return;
    const vh = window.innerHeight || 800;
    let top = centerY - RULER_BAND_PX / 2;
    if (top < -RULER_BAND_PX) top = -RULER_BAND_PX;
    if (top > vh) top = vh;
    _rulerEl.style.visibility = "visible";
    _rulerEl.style.transform = "translate3d(0," + top + "px,0)";
  }

  function enableReadingRuler() {
    if (_rulerEl) return;
    const el = document.createElement("div");
    el.id = "__aaas_ruler__";
    el.setAttribute("aria-hidden", "true");
    el.style.cssText =
      "position:fixed;left:0;right:0;top:0;height:" + RULER_BAND_PX + "px;" +
      "pointer-events:none;z-index:2147483646;" +
      "box-shadow:0 0 0 200vmax rgba(15,20,25,0.38);" +
      "border-top:2px solid rgba(255,207,51,0.85);" +
      "border-bottom:2px solid rgba(255,207,51,0.85);" +
      "transform:translate3d(0,-200px,0);" +
      "transition:transform 80ms linear;" +
      "visibility:hidden;";
    (document.body || document.documentElement).appendChild(el);
    _rulerEl = el;
    let raf = 0;
    let lastY = 0;
    _rulerMove = (ev) => {
      lastY = ev.clientY;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        positionRuler(lastY);
      });
    };
    _rulerFocus = (ev) => {
      const t = ev.target;
      if (!t || !t.getBoundingClientRect) return;
      if (t.closest && t.closest("[data-aaas-widget]")) return;
      const r = t.getBoundingClientRect();
      positionRuler(r.top + r.height / 2);
    };
    _rulerLeave = () => {
      if (_rulerEl) _rulerEl.style.visibility = "hidden";
    };
    document.addEventListener("mousemove", _rulerMove, { passive: true });
    document.addEventListener("focusin", _rulerFocus, true);
    document.documentElement.addEventListener("mouseleave", _rulerLeave);
  }

  function disableReadingRuler() {
    if (!_rulerEl) return;
    document.removeEventListener("mousemove", _rulerMove);
    document.removeEventListener("focusin", _rulerFocus, true);
    document.documentElement.removeEventListener("mouseleave", _rulerLeave);
    _rulerEl.remove();
    _rulerEl = null;
    _rulerMove = null;
    _rulerFocus = null;
    _rulerLeave = null;
  }

  function getStoredFlag(key) {
    try {
      return window.localStorage?.getItem(key) === "1";
    } catch {
      return false;
    }
  }

  function setStoredFlag(key, on) {
    try {
      if (on) window.localStorage?.setItem(key, "1");
      else window.localStorage?.removeItem(key);
    } catch {
      /* localStorage may be disabled in private mode — ignore. */
    }
  }

  /* ---------- UI ---------- */

  function mount() {
    injectHostFont();

    const host = document.createElement("div");
    host.setAttribute("data-aaas-widget", "");
    host.style.all = "initial";
    const shadow = host.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = STYLE;
    shadow.append(style);

    const fab = document.createElement("button");
    fab.className = "fab";
    fab.type = "button";
    fab.setAttribute("aria-label", "Open accessibility panel");
    fab.textContent = "ଅ";
    shadow.append(fab);

    // The page's CURRENT language. Starts as the detected load-time
    // language, and is reassigned after a successful full-page
    // translate / Easy Read — the in-place rewrites genuinely change
    // what language the DOM is in, and every downstream consumer
    // (read-aloud, Easy Read, voice nav, a second translate click)
    // must see the new reality or it will re-translate already-Odia
    // text "from English" and garble the page.
    let pageLang = detectPageLang();

    const panel = document.createElement("div");
    panel.className = "panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Accessibility options");
    panel.innerHTML = `
      <p class="title">Accessibility</p>
      <p class="sub">Read aloud, translate, and speak to fill forms.</p>

      <div class="row">
        <label for="aaas-lang">Language</label>
        <select id="aaas-lang" class="lang" aria-label="Read-aloud language">
          <option value="auto"${CONFIG.defaultLang === "auto" ? " selected" : ""}>Auto (${pageLang})</option>
          <option value="or"${CONFIG.defaultLang === "or" ? " selected" : ""}>Odia · ଓଡ଼ିଆ</option>
          <option value="hi"${CONFIG.defaultLang === "hi" ? " selected" : ""}>Hindi · हिन्दी</option>
          <option value="en"${CONFIG.defaultLang === "en" ? " selected" : ""}>English</option>
        </select>
      </div>

      <div class="read-row">
        <button class="action read" type="button">
          <span aria-hidden="true">🔊</span>
          <span>Read this page</span>
        </button>
        <button class="pause" type="button" aria-label="Pause or resume" title="Pause (Space)">⏸</button>
      </div>

      <button class="action mic" type="button">
        <span aria-hidden="true">🎙️</span>
        <span>Speak (fill by voice)</span>
      </button>

      <button class="action voice" type="button">
        <span aria-hidden="true">🧭</span>
        <span>Navigate by voice</span>
      </button>

      <button class="action translate" type="button">
        <span aria-hidden="true">🌐</span>
        <span class="translate-label">Translate this page</span>
      </button>

      <button class="action easyread" type="button">
        <span aria-hidden="true">📖</span>
        <span class="easyread-label">Easy Read this page</span>
      </button>

      <button class="action ocr" type="button">
        <span aria-hidden="true">📄</span>
        <span>Read a scanned notice</span>
      </button>

      <label class="toggle">
        <input type="checkbox" id="aaas-dyslexia" />
        <span class="toggle-text">Dyslexia mode</span>
        <span class="toggle-hint">More spacing, softer contrast</span>
      </label>

      <label class="toggle">
        <input type="checkbox" id="aaas-hover" />
        <span class="toggle-text">Hover to speak</span>
        <span class="toggle-hint">Speaks whatever your mouse points at</span>
      </label>

      <label class="toggle">
        <input type="checkbox" id="aaas-ruler" />
        <span class="toggle-text">Reading ruler</span>
        <span class="toggle-hint">Focus band that follows your pointer</span>
      </label>

      <button class="shortcuts-link" type="button">⌨️ Keyboard shortcuts</button>

      <div class="transcript" role="status" aria-live="polite"></div>
      <div class="status" role="status" aria-live="polite">Ready</div>
      <div class="meta"></div>

      <div class="ocr-overlay" role="dialog" aria-label="Scanned notice">
        <button class="close-ocr" type="button" aria-label="Close notice">×</button>
        <h4>Scanned notice</h4>
        <div class="ocr-text" tabindex="0"></div>
        <div class="ocr-actions">
          <button class="ocr-read" type="button">🔊 Read aloud</button>
          <button class="ocr-copy" type="button">Copy</button>
        </div>
      </div>

      <div class="shortcuts-overlay" role="dialog" aria-label="Keyboard shortcuts">
        <button class="close-overlay" type="button" aria-label="Close shortcuts">×</button>
        <h4>Keyboard shortcuts</h4>
        <dl>
          <dt>Alt+R</dt><dd>Read this page</dd>
          <dt>Alt+M</dt><dd>Speak (fill by voice)</dd>
          <dt>Alt+V</dt><dd>Navigate by voice</dd>
          <dt>Space</dt><dd>Pause / resume (while reading)</dd>
          <dt>→</dt><dd>Skip to next chunk</dd>
          <dt>←</dt><dd>Replay previous chunk</dd>
          <dt>Esc</dt><dd>Stop</dd>
          <dt>?</dt><dd>Toggle this help</dd>
        </dl>
      </div>
    `;
    shadow.append(panel);
    document.body.append(host);

    const readBtn = panel.querySelector(".read");
    const readRow = panel.querySelector(".read-row");
    const pauseBtn = panel.querySelector(".pause");
    const micBtn = panel.querySelector(".mic");
    const langSel = panel.querySelector("#aaas-lang");
    const dyslexiaToggle = panel.querySelector("#aaas-dyslexia");
    const hoverToggle = panel.querySelector("#aaas-hover");
    const rulerToggle = panel.querySelector("#aaas-ruler");
    const shortcutsLink = panel.querySelector(".shortcuts-link");
    const shortcutsOverlay = panel.querySelector(".shortcuts-overlay");
    const overlayClose = shortcutsOverlay.querySelector(".close-overlay");
    const transcriptEl = panel.querySelector(".transcript");
    const statusEl = panel.querySelector(".status");
    const metaEl = panel.querySelector(".meta");
    const player = new Player();
    const recorder = new Recorder();

    // Session-level flag: if the gateway probe fails at panel open we
    // surface the outage in the status pill instead of prewarming, but
    // there is no engine switch — MMS is the only TTS.
    let gatewayOffline = false;

    const announcer = new Announcer({
      getTargetLang: () => resolvedLang(),
      getSourceLang: () => pageLang,
    });

    // Restore dyslexia mode from the last session so a reload doesn't
    // undo the user's preference. The attribute on <html> and the DOM
    // checkbox state are kept in sync by applyDyslexia.
    function applyDyslexia(on) {
      if (on) injectDyslexiaStyles();
      else removeDyslexiaStyles();
      dyslexiaToggle.checked = on;
    }
    applyDyslexia(getStoredFlag(LS_DYSLEXIA));
    dyslexiaToggle.addEventListener("change", () => {
      const on = dyslexiaToggle.checked;
      setStoredFlag(LS_DYSLEXIA, on);
      applyDyslexia(on);
    });

    function applyRuler(on) {
      if (on) enableReadingRuler();
      else disableReadingRuler();
      rulerToggle.checked = on;
    }
    applyRuler(getStoredFlag(LS_RULER));
    rulerToggle.addEventListener("change", () => {
      const on = rulerToggle.checked;
      setStoredFlag(LS_RULER, on);
      applyRuler(on);
    });

    const setStatus = (msg, kind) => {
      statusEl.textContent = msg;
      statusEl.className = "status";
      if (kind) {
        // Force a reflow between class swaps so the entry animation
        // replays even when the same notice fires twice in a row.
        void statusEl.offsetWidth;
        statusEl.className = "status " + kind;
      }
    };

    const resolvedLang = () => {
      const v = langSel.value;
      return v === "auto" ? pageLang : v;
    };

    // Short strings worth pre-caching per target language: with these
    // in phraseCache, the first hover/focus announcement of a button
    // or heading plays in ~50 ms instead of ~2 s. Runs fire-and-forget
    // on panel open. Generated from PREFIX_STRINGS so each language
    // gets its own set — previously the hardcoded English strings
    // 400'd every request when tgt was 'or' or 'hi'.
    function prefixesToPrefetch(tgt) {
      const table = PREFIX_STRINGS[tgt] || PREFIX_STRINGS.en;
      const out = [];
      for (const [role, value] of Object.entries(table)) {
        if (role === "heading") {
          for (let lvl = 1; lvl <= 6; lvl++) out.push(value(lvl));
        } else {
          out.push(value);
        }
      }
      return out;
    }

    async function prefetchPrefixes(tgt) {
      // Limit parallelism to 2 so the TTS service isn't slammed on a
      // cold boot. Failures are silently ignored — these are an
      // optimisation, not a correctness requirement.
      const queue = prefixesToPrefetch(tgt);
      const run = async () => {
        while (queue.length) {
          const p = queue.shift();
          try { await synthesise(p, tgt); } catch {}
        }
      };
      await Promise.all([run(), run()]);
    }

    async function warmupAndPrefetch(tgt) {
      // On-device runs inference on the page's single WASM thread, so any
      // synth here (model warmup + prefix prefetch) would freeze the tab for
      // ~35s on panel open. Defer all of it: the model loads lazily on the
      // first real Read, where the progress status makes the wait expected.
      // Warmup/prefetch only benefit the gateway path (hiding network latency).
      if (ON_DEVICE) return;
      // Warm the target-language model with a digit — valid in every MMS
      // voice (or/hi/en), unlike a script-specific letter such as "ଓ" which
      // 400s on the wrong model and surfaces as a spurious first-chunk error.
      try { await synthesise("1", tgt); } catch {}
      prefetchPrefixes(tgt);
      // Look-ahead translate the first atom's text, so clicking Read
      // feels instant. Skipped if src===tgt (no-op) or gateway offline.
      if (pageLang !== tgt) {
        try {
          const atoms = collectAtoms(document.body);
          if (atoms.length && atoms[0].text) {
            translateChunk(atoms[0].text, pageLang, tgt).catch(() => {});
          }
        } catch {}
      }
    }

    let panelProbed = false;

    const togglePanel = () => {
      const open = panel.getAttribute("data-open") === "true";
      panel.setAttribute("data-open", open ? "false" : "true");
      fab.setAttribute("aria-expanded", open ? "false" : "true");
      const nowOpen = !open;
      if (nowOpen && !isReading && !recorder.isRecording() && !panelProbed) {
        panelProbed = true;
        probeGateway().then((ok) => {
          gatewayOffline = !ok;
          if (!ok && !ON_DEVICE) {
            setStatus(
              "Server offline — TTS unavailable. Start the AaaS gateway to enable read-aloud.",
              "error"
            );
          } else {
            // On-device mode synthesises in the browser, so a missing gateway
            // is fine for read-aloud; warm the local (or server) backend now.
            warmupAndPrefetch(resolvedLang());
          }
        });
      }
      if (!nowOpen) {
        // Close shortcuts overlay alongside the panel.
        shortcutsOverlay.setAttribute("data-open", "false");
      }
    };

    // If the user switches target language after prefetch, warm the
    // new language's prefixes too.
    langSel.addEventListener("change", () => {
      if (!gatewayOffline && panelProbed) {
        prefetchPrefixes(resolvedLang());
      }
    });

    fab.addEventListener("click", togglePanel);

    /* ----- Read-aloud flow ----- */
    let isReading = false;
    let stopRequested = false;
    let currentAbort = null;

    function setReadingUI(on, label) {
      isReading = on;
      readRow.setAttribute("data-playing", on ? "true" : "false");
      readBtn.classList.toggle("stop", on);
      readBtn.querySelector("span:last-child").textContent = on ? "Stop" : "Read this page";
      pauseBtn.textContent = "⏸";
      pauseBtn.title = "Pause (Space)";
      if (label !== undefined) setStatus(label, on ? "ok" : "");
    }

    pauseBtn.addEventListener("click", () => {
      if (!isReading) return;
      if (player.isPaused()) {
        player.resume();
        pauseBtn.textContent = "⏸";
        pauseBtn.title = "Pause (Space)";
        setStatus("Playing…", "ok");
      } else {
        player.pause();
        pauseBtn.textContent = "▶";
        pauseBtn.title = "Resume (Space)";
        setStatus("Paused.", "");
      }
    });

    async function startReadPage() {
      if (isReading) {
        stopRequested = true;
        if (currentAbort) { try { currentAbort.abort(); } catch {} }
        player.stop();
        setReadingUI(false, "Stopped.");
        return;
      }
      stopRequested = false;
      announcer.cancel();

      // On-device mode does TTS in the browser, so an offline gateway must not
      // block read-aloud. Translation still needs the gateway, but that
      // degrades per-sentence below rather than failing the whole read.
      if (gatewayOffline && !ON_DEVICE) {
        setStatus(
          "Server offline — TTS unavailable. Start the AaaS gateway and try again.",
          "error"
        );
        return;
      }

      const atoms = collectAtoms(document.body);
      if (!atoms.length) {
        setStatus("No readable content found on this page.", "error");
        return;
      }
      const tgt = resolvedLang();
      const src = pageLang;

      // Expand paragraph-level atoms into sentence-level units so the
      // pipeline below can start playing on the first sentence instead
      // of waiting for a whole paragraph to synthesise. Only the first
      // unit of an atom carries the role prefix, so a heading's
      // "Heading level 2, …" announcement isn't re-spoken between
      // sentences of the same heading.
      const units = [];
      for (const atom of atoms) {
        const atomText = (atom.text || "").trim();
        if (!atomText) continue;
        const sentences = splitIntoSentences(atomText, CONFIG.maxChars);
        for (let i = 0; i < sentences.length; i++) {
          units.push({
            text: sentences[i],
            role: atom.role,
            prefix: i === 0 ? prefixFor(atom, tgt) : "",
          });
        }
      }
      if (!units.length) {
        setStatus("No readable content found on this page.", "error");
        return;
      }
      metaEl.textContent = `${units.length} sentences · ${src}→${tgt}`;
      setReadingUI(true, units.length > 1 ? `Preparing (1/${units.length})…` : "Preparing…");

      currentAbort = new AbortController();
      const abortSignal = currentAbort.signal;
      player.reset();

      let translateFailed = null;
      let ttsError = null;
      let translateOk = 0;
      let translateSkipped = 0;
      let synthOk = 0;
      let synthSkipped = 0;

      // Producer 1: translate each unit, pushing results into
      // `translated`. Skips translate when src===tgt, and also when
      // the sentence is already in the target script. Off-script
      // responses or per-unit exceptions skip that unit and continue;
      // we only abort the whole session if many consecutive units fail
      // with zero successes — the signal for a genuinely offline
      // service. A silent switch to source-language voice is not an
      // option here, and that path stays closed.
      const translated = new StreamQueue();
      const MAX_CONSEC_FAIL = 5;
      const runTranslate = async () => {
        for (const unit of units) {
          if (stopRequested || abortSignal.aborted) break;
          if (translateFailed) break;
          if (src === tgt) {
            translated.push({
              text: unit.prefix + unit.text,
              lang: tgt,
              role: unit.role,
            });
            continue;
          }
          if (looksLikeTargetScript(unit.text, tgt)) {
            translated.push({
              text: unit.prefix + unit.text,
              lang: tgt,
              role: unit.role,
            });
            translateOk++;
            continue;
          }
          try {
            const tt = await translateChunk(unit.text, src, tgt, { signal: abortSignal });
            if (looksLikeTargetScript(tt, tgt)) {
              translated.push({
                text: unit.prefix + tt,
                lang: tgt,
                role: unit.role,
              });
              translateOk++;
            } else {
              translateSkipped++;
            }
          } catch (err) {
            if (abortSignal.aborted) break;
            translateSkipped++;
            if (translateOk === 0 && translateSkipped >= MAX_CONSEC_FAIL) {
              translateFailed =
                `Translation unavailable (${src}→${tgt}) — ` +
                `${err?.message || "translate service error"}.`;
              break;
            }
          }
        }
        translated.close();
      };

      // Producer 2: synthesise each translated chunk, pushing blobs
      // into `synthesized`. Cache-hits are free. Per-atom TTS
      // rejections (the Odia tokeniser 400s on Latin-only chunks, for
      // example) skip just that chunk. Only surface the loud error if
      // TTS is genuinely down — many failures with zero successes.
      const synthesized = new StreamQueue();
      const runSynth = async () => {
        while (true) {
          if (stopRequested || abortSignal.aborted) break;
          const item = await translated.next();
          if (!item) break;
          try {
            const blob = await synthesise(item.text, item.lang, { signal: abortSignal });
            synthesized.push({ blob, text: item.text, lang: item.lang });
            synthOk++;
          } catch (err) {
            if (abortSignal.aborted) break;
            synthSkipped++;
            if (!ttsError && synthOk === 0 && synthSkipped >= MAX_CONSEC_FAIL) {
              ttsError = err;
              setStatus("TTS unavailable — check the gateway", "error");
            }
          }
        }
        synthesized.close();
      };

      // Consumer: feed Player. Progress chip ticks per advance so the
      // judges see motion even on cold chunks.
      let played = 0;
      player.onAdvance = () => {
        played += 1;
        if (!stopRequested) {
          setStatus(`Playing ${played}/${units.length}…`, "ok");
        }
      };
      const runPlay = async () => {
        const drainPromise = player.drain();
        while (true) {
          if (stopRequested || abortSignal.aborted) break;
          const item = await synthesized.next();
          if (!item) break;
          player.enqueue(item.blob);
        }
        player.finish();
        await drainPromise;
      };

      try {
        await Promise.all([runTranslate(), runSynth(), runPlay()]);
        if (!stopRequested) {
          if (translateFailed) {
            setStatus(translateFailed, "error");
          } else if (ttsError && synthOk === 0) {
            setStatus("TTS unavailable — check the gateway", "error");
          } else {
            const skipped = translateSkipped + synthSkipped;
            if (skipped > 0) {
              setStatus(
                `Done. Spoke ${synthOk}/${units.length}, skipped ${skipped} untranslatable sentence${skipped === 1 ? "" : "s"}.`,
                "ok",
              );
            } else {
              setStatus("Done.", "ok");
            }
          }
        }
      } catch (err) {
        if (!stopRequested) {
          console.warn("[AaaS] pipeline failed:", err);
          setStatus(`Read-aloud failed: ${err?.message || "unknown error"}`, "error");
        }
      } finally {
        player.onAdvance = null;
        currentAbort = null;
        setReadingUI(false);
      }
    }

    readBtn.addEventListener("click", startReadPage);

    // In-place full-page visual translation. Walks the DOM for text nodes,
    // translates each through translateChunk (Google Translate via the
    // background worker, gateway fallback), and replaces node values in place
    // so the user watches the page flip to Odia (or the picker's choice)
    // without a new tab or URL change. Source is the detected page language;
    // we cap concurrency and progress-report as each batch lands.
    const translateBtn = panel.querySelector(".translate");
    const translateLabel = translateBtn.querySelector(".translate-label");
    const LANG_DISPLAY = { or: "Odia", hi: "Hindi", en: "English" };
    const HAS_SCRIPT_CHAR = /[A-Za-zऀ-ॿ଀-୿]/;
    const SKIP_TAGS = new Set([
      "SCRIPT",
      "STYLE",
      "NOSCRIPT",
      "TEXTAREA",
      "INPUT",
      "CODE",
      "PRE",
    ]);

    function updateTranslateLabel() {
      const tgt = resolvedLang() || "or";
      translateLabel.textContent =
        tgt === "en"
          ? "Translate this page"
          : `Translate this page → ${LANG_DISPLAY[tgt] || tgt}`;
    }
    updateTranslateLabel();
    langSel.addEventListener("change", updateTranslateLabel);

    function collectTranslatableNodes() {
      const out = [];
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode(n) {
            const p = n.parentElement;
            if (!p) return NodeFilter.FILTER_REJECT;
            // Skip text inside the widget itself (lives in Shadow DOM
            // anyway, but defend in depth).
            if (p.closest && p.closest(".aaas-host")) {
              return NodeFilter.FILTER_REJECT;
            }
            if (SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT;
            if (p.isContentEditable) return NodeFilter.FILTER_REJECT;
            const v = n.nodeValue;
            if (!v || v.length < 2) return NodeFilter.FILTER_REJECT;
            if (!HAS_SCRIPT_CHAR.test(v)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          },
        },
      );
      let node;
      while ((node = walker.nextNode())) out.push(node);
      return out;
    }

    // Translate a single text node. Source is the detected page language; a
    // longer timeout than the read-aloud path accommodates whole-paragraph
    // nodes. Throws on failure (caller leaves the node untranslated).
    async function translateOne(text, tgt) {
      return translateChunk(text, pageLang, tgt, { timeoutMs: 20000 });
    }

    let translateInFlight = false;
    async function translatePageInPlace() {
      if (translateInFlight || easyReadInFlight) return;
      const statusEl = panel.querySelector(".status");
      const tgt = resolvedLang() || "or";
      // The page is already in the target language — either natively
      // or from an earlier click. Re-translating would feed tgt-language
      // text back through the engine labelled as pageLang and corrupt
      // the page, so refuse fast with a friendly status instead.
      if (tgt === pageLang) {
        setStatus(
          `Page is already in ${LANG_DISPLAY[tgt] || tgt} — reload to see the original`,
          "notice",
        );
        return;
      }
      translateInFlight = true;
      translateBtn.disabled = true;
      try {
        const nodes = collectTranslatableNodes();
        if (!nodes.length) {
          statusEl.textContent = "Nothing to translate on this page";
          return;
        }
        statusEl.textContent =
          `Translating 0 / ${nodes.length} → ${LANG_DISPLAY[tgt] || tgt}…`;
        const BATCH = 5;
        let done = 0;
        let changed = 0;
        for (let i = 0; i < nodes.length; i += BATCH) {
          const slice = nodes.slice(i, i + BATCH);
          await Promise.all(
            slice.map(async (node) => {
              try {
                const translated = await translateOne(node.nodeValue, tgt);
                if (translated) {
                  node.nodeValue = translated;
                  changed++;
                }
              } catch (err) {
                console.warn("[AaaS] translate node failed:", err);
              }
            }),
          );
          done += slice.length;
          statusEl.textContent =
            `Translating ${done} / ${nodes.length} → ${LANG_DISPLAY[tgt] || tgt}…`;
        }
        statusEl.textContent =
          `Page translated → ${LANG_DISPLAY[tgt] || tgt} (reload to revert)`;
        // The DOM is now in the target language; let read-aloud,
        // Easy Read, voice nav and repeat clicks act on that fact.
        // Guarded so a total failure (gateway down, every node left
        // untouched) doesn't mislabel an untranslated page.
        if (changed) pageLang = tgt;
      } finally {
        translateBtn.disabled = false;
        translateInFlight = false;
      }
    }
    translateBtn.addEventListener("click", translatePageInPlace);

    // Easy Read: same in-place rewrite as translate, but through the
    // rule-based /simplify endpoint — and when the picker's language
    // differs from the page's, the simplified text is then translated,
    // so an English notice ends up as plain Odia. Reload to revert,
    // same as translate; the done-flag stops double-simplification.
    const easyreadBtn = panel.querySelector(".easyread");
    let easyReadInFlight = false;
    let easyReadDone = false;

    // Simplify one text node. The service caps input at 2000 chars, so
    // longer nodes are pre-split at sentence boundaries and rejoined.
    async function simplifyOne(text) {
      if (text.length <= 1800) return simplifyChunk(text, pageLang);
      const pieces = splitIntoSentences(text, 1500);
      const out = [];
      for (const piece of pieces) {
        out.push(await simplifyChunk(piece, pageLang));
      }
      return out.join(" ");
    }

    async function easyReadPageInPlace() {
      if (easyReadInFlight || translateInFlight) return;
      if (easyReadDone) {
        setStatus("Page is already in Easy Read — reload to see the original", "notice");
        return;
      }
      easyReadInFlight = true;
      easyreadBtn.disabled = true;
      const tgt = resolvedLang() || pageLang;
      const chain = tgt !== pageLang;
      const suffix = chain ? ` → ${LANG_DISPLAY[tgt] || tgt}` : "";
      try {
        const nodes = collectTranslatableNodes();
        if (!nodes.length) {
          setStatus("Nothing to simplify on this page");
          return;
        }
        setStatus(`Simplifying 0 / ${nodes.length}${suffix}…`);
        const BATCH = 5;
        let done = 0;
        let succeeded = 0;
        for (let i = 0; i < nodes.length; i += BATCH) {
          const slice = nodes.slice(i, i + BATCH);
          await Promise.all(
            slice.map(async (node) => {
              try {
                let out = await simplifyOne(node.nodeValue);
                if (chain && out) {
                  out = stripPassthroughAnnotation(
                    await translateChunk(out, pageLang, tgt, { timeoutMs: 20000 }),
                  );
                }
                if (out) {
                  node.nodeValue = out;
                  succeeded++;
                }
              } catch (err) {
                console.warn("[AaaS] simplify node failed:", err);
              }
            }),
          );
          // If the entire first batch failed, the gateway is almost
          // certainly unreachable — bail out instead of grinding
          // through every node just to fail on each one.
          if (!succeeded && i === 0) {
            setStatus("Easy Read unavailable — check that services are running", "error");
            return;
          }
          done += slice.length;
          setStatus(`Simplifying ${done} / ${nodes.length}${suffix}…`);
        }
        easyReadDone = true;
        // Chained Easy Read leaves the DOM in the target language —
        // record it so read-aloud / voice nav / translate see reality.
        if (chain) pageLang = tgt;
        setStatus(`Page in Easy Read${suffix} (reload to revert)`, "ok");
      } finally {
        easyreadBtn.disabled = false;
        easyReadInFlight = false;
      }
    }
    easyreadBtn.addEventListener("click", easyReadPageInPlace);

    /* ----- Hover-speak toggle (persisted) ----- */
    function applyHoverPref(on) {
      hoverToggle.checked = on;
      setStoredFlag(LS_HOVER_SPEAK, on);
    }
    applyHoverPref(getStoredFlag(LS_HOVER_SPEAK));
    hoverToggle.addEventListener("change", () => applyHoverPref(hoverToggle.checked));

    /* ----- Shortcuts overlay ----- */
    const toggleShortcuts = (force) => {
      const isOpen = shortcutsOverlay.getAttribute("data-open") === "true";
      const next = typeof force === "boolean" ? force : !isOpen;
      shortcutsOverlay.setAttribute("data-open", next ? "true" : "false");
    };
    shortcutsLink.addEventListener("click", () => toggleShortcuts());
    overlayClose.addEventListener("click", () => toggleShortcuts(false));

    /* ----- Announcer event wiring (focus / hover / selection) -----
     * Listeners are capturing + document-scoped so they fire before
     * the host page's own handlers. All three funnel into a single
     * `announce()` that cancels any in-flight utterance first, so a
     * fast-tabbing user never queues up a backlog.
     */
    const widgetHost = host; // closed-over reference to the widget's own <div>
    function inWidget(el) {
      return el && widgetHost.contains(el);
    }

    function focusHandler(ev) {
      // Speaking on focus is opt-in via the same toggle as hover. Without
      // this guard, any page that autofocuses a control on load (e.g.
      // Wikipedia's search box) triggers synthesis on page load — and in
      // on-device mode that means a heavy, main-thread-blocking WASM model
      // load that freezes the whole tab. Off by default = no surprise.
      if (!hoverToggle.checked) return;
      const t = ev.target;
      if (!(t instanceof Element) || inWidget(t)) return;
      if (!t.matches(INTERACTIVE_SELECTOR)) return;
      const atom = describeAtom(t) || {
        text: getAccessibleName(t) || t.tagName.toLowerCase(),
        prefix: "",
        role: "focus",
        element: t,
      };
      announcer.announce(atom);
    }

    const hoverHandler = debounce((ev) => {
      if (!hoverToggle.checked) return;
      const t = ev.target;
      if (!(t instanceof Element) || inWidget(t)) return;
      // Only speak interactive things on hover — plain text hover is
      // spam-prone on content-heavy pages.
      const iv = t.closest(INTERACTIVE_SELECTOR);
      if (!iv || inWidget(iv)) return;
      const atom = describeAtom(iv);
      if (!atom) return;
      announcer.announce(atom);
    }, 200);

    // `selectionchange` fires many times per drag; debounce 400 ms
    // before we bother translating + synthesising.
    const selectionHandler = debounce(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return;
      const text = sel.toString().trim();
      if (!text) return;
      // Skip selections that start inside the widget itself.
      const anchor = sel.anchorNode instanceof Element
        ? sel.anchorNode
        : sel.anchorNode?.parentElement;
      if (inWidget(anchor)) return;
      // Cap selection length so a Ctrl+A doesn't DoS translate.
      const capped = text.slice(0, CONFIG.maxChars);
      announcer.announce({ text: capped, prefix: "", role: "selection", element: null });
    }, 400);

    document.addEventListener("focusin", focusHandler, true);
    document.addEventListener("mouseover", hoverHandler, true);
    document.addEventListener("selectionchange", selectionHandler);

    /* ----- Keyboard shortcuts -----
     * Capturing listener on window so we intercept before host-page
     * handlers. Input fields and contenteditable are respected
     * (unmodified keys pass through) — Alt-combos are always honoured.
     */
    function inEditable(el) {
      if (!el || !(el instanceof Element)) return false;
      if (inWidget(el)) return false;
      return !!el.closest('input, textarea, [contenteditable=""], [contenteditable="true"]');
    }

    window.addEventListener("keydown", (e) => {
      // Escape: always works. Closes panel if open, otherwise stops.
      if (e.key === "Escape") {
        if (shortcutsOverlay.getAttribute("data-open") === "true") {
          toggleShortcuts(false);
          e.preventDefault();
          return;
        }
        const ocrOv = panel.querySelector(".ocr-overlay");
        if (ocrOv && ocrOv.getAttribute("data-open") === "true") {
          ocrOv.querySelector(".close-ocr").click();
          e.preventDefault();
          return;
        }
        if (isReading) {
          stopRequested = true;
          if (currentAbort) { try { currentAbort.abort(); } catch {} }
          player.stop();
          setReadingUI(false, "Stopped.");
          e.preventDefault();
          return;
        }
        announcer.cancel();
        if (panel.getAttribute("data-open") === "true") {
          togglePanel();
          fab.focus();
          e.preventDefault();
        }
        return;
      }

      // Alt+R / Alt+M: global accelerators, always honoured.
      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const k = e.key.toLowerCase();
        if (k === "r") {
          e.preventDefault();
          if (panel.getAttribute("data-open") !== "true") togglePanel();
          startReadPage();
          return;
        }
        if (k === "m") {
          e.preventDefault();
          if (panel.getAttribute("data-open") !== "true") togglePanel();
          micBtn.click();
          return;
        }
        if (k === "v") {
          e.preventDefault();
          if (panel.getAttribute("data-open") !== "true") togglePanel();
          voiceBtn.click();
          return;
        }
      }

      // Everything below is reading-time only and should never hijack
      // typing into an input or contenteditable.
      if (inEditable(e.target)) return;

      if (e.key === " " || e.code === "Space") {
        if (isReading) {
          e.preventDefault();
          pauseBtn.click();
        }
        return;
      }
      if (e.key === "ArrowRight") {
        if (isReading) {
          e.preventDefault();
          player.skipCurrent();
        }
        return;
      }
      if (e.key === "ArrowLeft") {
        if (isReading) {
          e.preventDefault();
          player.replayPrevious();
        }
        return;
      }
      if (e.key === "?" && panel.getAttribute("data-open") === "true") {
        e.preventDefault();
        toggleShortcuts();
      }
    }, true);

    /* ----- Mic (STT) flow -----
     * User-initiated stop and the auto-stop timer both funnel into
     * handleRecorded(blob). Keep a single exit point so the UI is
     * consistent no matter which path triggered the transcription.
     */

    // Track the most recently focused editable field on the host page.
    // Clicking the widget's mic button steals focus, so by the time the
    // transcript arrives `document.activeElement` is the mic button
    // itself — no help. This listener captures focusin earlier, outside
    // the widget, and remembers the last input/textarea/contenteditable
    // the user actually touched.
    let lastEditableEl = null;
    function isEditableTarget(el) {
      if (!el || !(el instanceof Element)) return false;
      if (inWidget(el)) return false;
      if (el.isContentEditable) return true;
      const tag = el.tagName;
      if (tag === "TEXTAREA") return true;
      if (tag === "INPUT") {
        const t = (el.type || "text").toLowerCase();
        // Editable text-y inputs. Explicitly skip checkbox / radio /
        // file / button / color / range — writing a transcript into
        // those makes no sense.
        return [
          "text",
          "search",
          "email",
          "url",
          "tel",
          "number",
          "password",
          "",
        ].includes(t);
      }
      return false;
    }
    document.addEventListener(
      "focusin",
      (ev) => {
        if (isEditableTarget(ev.target)) lastEditableEl = ev.target;
      },
      true,
    );

    // Write `text` into an input / textarea / contenteditable in a way
    // that React-style controlled inputs notice. React hijacks the
    // `value` setter on HTMLInputElement.prototype to detect changes;
    // assigning `.value` directly is invisible to it, so we call the
    // native setter via its property descriptor and then dispatch an
    // input event — the pattern React's own devtools use to fake input.
    function writeToField(el, text) {
      if (!el || !el.isConnected) return false;
      if (el.isContentEditable) {
        el.focus();
        el.textContent = text;
        el.dispatchEvent(
          new InputEvent("input", {
            bubbles: true,
            cancelable: true,
            inputType: "insertText",
            data: text,
          }),
        );
        return true;
      }
      const tag = el.tagName;
      if (tag !== "INPUT" && tag !== "TEXTAREA") return false;
      const proto =
        tag === "INPUT"
          ? HTMLInputElement.prototype
          : HTMLTextAreaElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, "value");
      try {
        el.focus();
      } catch {}
      if (desc?.set) {
        desc.set.call(el, text);
      } else {
        el.value = text;
      }
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }

    async function handleRecorded(blob) {
      micBtn.classList.remove("recording");
      micBtn.querySelector("span:last-child").textContent = "Speak (fill by voice)";
      setStatus("Transcribing…");
      try {
        const result = await transcribe(blob, resolvedLang());
        // Transcript box always shows the native-script speech the STT
        // heard — proof to the user that their voice was understood.
        // Form field gets English (below) because the AaaS target user
        // is an Odia/Hindi speaker filling an English-only form.
        transcriptEl.textContent = result.text || "(no speech detected)";
        const label = result.engine === "mock" ? " (mock)" : "";
        const src = (result.language || "").toLowerCase().split("-")[0];

        let fillText = toWesternDigits(result.text || "");
        let translateFailed = false;
        if (result.text && src && src !== "en") {
          try {
            const raw = await translateChunk(result.text, src, "en");
            // Strip any `[or->en] ` passthrough that mock emits for
            // uncovered phrases, then verify the body is actually Latin
            // script. Off-script output means the translator couldn't
            // handle this phrase; writing Odia into an English form
            // would defeat the whole accessibility flow, so we leave
            // the field empty and surface the failure loudly.
            const stripped = stripPassthroughAnnotation(raw || "").trim();
            if (stripped && looksLikeTargetScript(stripped, "en")) {
              fillText = toWesternDigits(stripped);
            } else {
              translateFailed = true;
              fillText = "";
            }
          } catch (err) {
            console.warn("[AaaS] translate to English failed", err);
            translateFailed = true;
            fillText = "";
          }
        }

        // Auto-fill the last editable field the user touched. Cooperating
        // demo sites also get the CustomEvent below for custom handling.
        let filled = false;
        if (fillText && lastEditableEl) {
          filled = writeToField(lastEditableEl, fillText);
        }
        const arrow = src && src !== "en" ? " → en" : "";
        if (translateFailed) {
          setStatus(
            `Transcribed (${src})${label} — translation to English unavailable; form field left empty. Install real translate engine for real translations.`,
            "error",
          );
        } else if (filled) {
          setStatus(`Filled field (${src}${arrow})${label}`, "ok");
        } else if (fillText) {
          setStatus(
            `Transcribed (${src}${arrow})${label} — click into a text box first to auto-fill`,
            "ok",
          );
        } else {
          setStatus(`No speech detected (${src || "unknown"})${label}`, "error");
        }

        document.dispatchEvent(
          new CustomEvent("aaas-transcript", {
            detail: {
              text: result.text,
              filledText: fillText,
              language: result.language,
              engine: result.engine,
              filled,
              translateFailed,
            },
          })
        );
      } catch (err) {
        console.warn("[AaaS] transcribe failed", {
          error: err,
          message: err?.message,
          blobSize: blob?.size ?? 0,
          blobType: blob?.type ?? "",
          gateway: CONFIG.gateway,
        });
        transcriptEl.textContent = `(failed: ${err.message || "unknown error"})`;
        setStatus(`Could not transcribe: ${err.message}`, "error");
      }
    }

    micBtn.addEventListener("click", async () => {
      if (recorder.isRecording()) {
        if (voiceNavRecording) {
          setStatus("Mic busy — finish the voice command first", "error");
          return;
        }
        try {
          const blob = await recorder.stop();
          await handleRecorded(blob);
        } catch (err) {
          setStatus(`Mic error: ${err.message}`, "error");
        }
        return;
      }
      transcriptEl.textContent = "";
      try {
        await recorder.start({ onAutoStop: handleRecorded });
        micBtn.classList.add("recording");
        micBtn.querySelector("span:last-child").textContent =
          `Recording (tap to stop, ${CONFIG.maxRecordSeconds}s max)…`;
        setStatus("Listening…");
      } catch (err) {
        setStatus(`Mic unavailable: ${err.message}`, "error");
      }
    });

    /* ----- Voice navigation -----
     * Same Recorder + transcribe() as the form-fill mic, but the
     * transcript is treated as a command: global widget actions first
     * (read / stop / translate / easy read / top / search), otherwise
     * matched against the page's links and buttons. The
     * "aaas-voice-command" CustomEvent is a mic-free input path — demo
     * scripts and tests can drive navigation with typed text.
     */
    const voiceBtn = panel.querySelector(".voice");

    function highlightVoiceTarget(el) {
      if (!document.getElementById("__aaas_voicenav__")) {
        const st = document.createElement("style");
        st.id = "__aaas_voicenav__";
        st.textContent =
          "[data-aaas-voice-target] { outline: 3px solid #ffcf33 !important; outline-offset: 2px !important; }";
        (document.head || document.documentElement).appendChild(st);
      }
      el.setAttribute("data-aaas-voice-target", "");
      setTimeout(() => el.removeAttribute("data-aaas-voice-target"), 1600);
    }

    async function executeVoiceCommand(rawText, langHint) {
      const norm = normalizeCommandText(rawText || "");
      if (!norm) {
        setStatus("No speech detected", "error");
        return;
      }
      const lang =
        dominantScript(rawText) ||
        (langHint || "").toLowerCase().split("-")[0] ||
        "en";

      const action = matchGlobalCommand(norm, lang);
      if (action === "read") {
        startReadPage();
        return;
      }
      if (action === "stop") {
        stopRequested = true;
        if (currentAbort) { try { currentAbort.abort(); } catch {} }
        player.stop();
        announcer.cancel();
        setReadingUI(false, "Stopped.");
        return;
      }
      if (action === "translate") {
        translatePageInPlace();
        return;
      }
      if (action === "easyread") {
        easyReadPageInPlace();
        return;
      }
      if (action === "top") {
        window.scrollTo({ top: 0, behavior: "smooth" });
        setStatus("Top of page", "ok");
        return;
      }
      if (action === "search") {
        const search = document.querySelector(
          'input[type="search"], [role="search"] input, input[name*="search" i], input[type="text"]',
        );
        if (search) {
          search.focus();
          setStatus("Search box focused — speak again to fill it", "ok");
        } else {
          setStatus("No search box on this page", "error");
        }
        return;
      }

      const targets = collectVoiceTargets();
      if (!targets.length) {
        setStatus("No links or buttons found on this page", "error");
        return;
      }
      // Cross-language: an Odia command on an English page is matched
      // three ways — as spoken, through the deterministic nav glossary
      // (reliable for common terms, immune to MT synonym drift), and
      // through full machine translation (covers everything else).
      // `understood` is surfaced in failure statuses so the user can
      // see how their words came across and rephrase.
      const candidates = [rawText];
      const understood = [];
      if (lang === "or" && pageLang === "en") {
        const g = glossaryTranslateOdia(norm);
        if (g) {
          candidates.push(g);
          understood.push(g);
        }
      }
      if (lang !== pageLang) {
        try {
          const tr = stripPassthroughAnnotation(
            (await translateChunk(rawText, lang, pageLang, { timeoutMs: 12000 })) || "",
          ).trim();
          if (tr && looksLikeTargetScript(tr, pageLang)) {
            candidates.push(tr);
            understood.push(tr);
          }
        } catch {}
      }
      const byElement = new Map();
      for (const cand of candidates) {
        for (const r of rankVoiceTargets(cand, targets)) {
          const prev = byElement.get(r.element);
          if (!prev || r.score > prev.score) byElement.set(r.element, r);
        }
      }
      const ranked = Array.from(byElement.values()).sort((a, b) => b.score - a.score);

      if (shouldActOnVoiceMatch(ranked)) {
        const best = ranked[0];
        try { best.element.scrollIntoView({ block: "center", behavior: "smooth" }); } catch {}
        try { best.element.focus(); } catch {}
        highlightVoiceTarget(best.element);
        setStatus(`Opening "${best.name}"…`, "ok");
        // A visible beat between highlight and click so the user sees
        // what was chosen before any navigation happens.
        setTimeout(() => { try { best.element.click(); } catch {} }, 600);
      } else if (ranked.length) {
        const names = ranked.slice(0, 3).map((r) => `"${r.name}"`).join(" · ");
        setStatus(`Not sure. Did you mean: ${names}?`, "error");
      } else {
        const heard = understood.length
          ? ` (understood as: ${understood.map((u) => `"${u}"`).join(" / ")})`
          : "";
        setStatus(`No link or button matches "${rawText}"${heard}`, "error");
      }
    }

    document.addEventListener("aaas-voice-command", (e) => {
      executeVoiceCommand(e.detail && e.detail.text, e.detail && e.detail.lang);
    });

    let voiceNavRecording = false;
    async function handleVoiceRecorded(blob) {
      voiceNavRecording = false;
      voiceBtn.classList.remove("recording");
      voiceBtn.querySelector("span:last-child").textContent = "Navigate by voice";
      setStatus("Transcribing command…");
      try {
        const result = await transcribe(blob, resolvedLang());
        transcriptEl.textContent = result.text || "(no speech detected)";
        await executeVoiceCommand(result.text, result.language);
        if (result.engine === "mock") {
          setStatus(
            `${statusEl.textContent} — mock STT hears canned phrases only; enable whisper for live voice`,
            "error",
          );
        }
      } catch (err) {
        setStatus(`Could not transcribe: ${err.message}`, "error");
      }
    }

    voiceBtn.addEventListener("click", async () => {
      if (recorder.isRecording()) {
        if (!voiceNavRecording) {
          setStatus("Mic busy — finish the form-fill recording first", "error");
          return;
        }
        try {
          const blob = await recorder.stop();
          await handleVoiceRecorded(blob);
        } catch (err) {
          setStatus(`Mic error: ${err.message}`, "error");
        }
        return;
      }
      transcriptEl.textContent = "";
      try {
        await recorder.start({ onAutoStop: handleVoiceRecorded });
        voiceNavRecording = true;
        voiceBtn.classList.add("recording");
        voiceBtn.querySelector("span:last-child").textContent = "Listening for a command…";
        setStatus("Say a command or a link name…");
      } catch (err) {
        setStatus(`Mic unavailable: ${err.message}`, "error");
      }
    });

    /* ----- Scanned-notice OCR -----
     * Pick mode: the user clicks a scanned image or a PDF link on the
     * host page; the document goes to /translate/ocr; the recognized
     * text runs through simplify (+ translate when the picker language
     * differs) and lands in a result overlay with its own read-aloud.
     * While picking, ALL host-page clicks are swallowed so a stray
     * click can't navigate away mid-pick; Esc cancels.
     */
    const ocrBtn = panel.querySelector(".ocr");
    const ocrOverlay = panel.querySelector(".ocr-overlay");
    const ocrTextEl = ocrOverlay.querySelector(".ocr-text");
    const ocrReadBtn = ocrOverlay.querySelector(".ocr-read");
    const ocrCopyBtn = ocrOverlay.querySelector(".ocr-copy");
    const ocrCloseBtn = ocrOverlay.querySelector(".close-ocr");

    let ocrPicking = false;
    let _ocrHover = null;
    let _ocrClick = null;
    let _ocrKey = null;

    function exitOcrPick(message) {
      if (!ocrPicking) return;
      ocrPicking = false;
      document.removeEventListener("mouseover", _ocrHover, true);
      document.removeEventListener("click", _ocrClick, true);
      window.removeEventListener("keydown", _ocrKey, true);
      _ocrHover = null;
      _ocrClick = null;
      _ocrKey = null;
      document.querySelectorAll("[data-aaas-ocr-hover]").forEach((el) => {
        el.removeAttribute("data-aaas-ocr-hover");
      });
      const st = document.getElementById("__aaas_ocrpick__");
      if (st) st.remove();
      if (message) setStatus(message);
    }

    function enterOcrPick() {
      if (ocrPicking) {
        exitOcrPick("Pick cancelled");
        return;
      }
      ocrPicking = true;
      if (!document.getElementById("__aaas_ocrpick__")) {
        const st = document.createElement("style");
        st.id = "__aaas_ocrpick__";
        st.textContent =
          "[data-aaas-ocr-hover] { outline: 3px dashed #ffcf33 !important; outline-offset: 3px !important; cursor: crosshair !important; }";
        (document.head || document.documentElement).appendChild(st);
      }
      _ocrHover = (ev) => {
        document.querySelectorAll("[data-aaas-ocr-hover]").forEach((el) => {
          el.removeAttribute("data-aaas-ocr-hover");
        });
        const t = ev.target;
        if (!t || !(t instanceof Element) || inWidget(t)) return;
        if (describeOcrTarget(t)) {
          const mark = t.tagName === "IMG" ? t : t.closest("a[href]");
          if (mark) mark.setAttribute("data-aaas-ocr-hover", "");
        }
      };
      _ocrClick = (ev) => {
        const t = ev.target;
        if (!t || !(t instanceof Element) || inWidget(t)) return;
        ev.preventDefault();
        ev.stopPropagation();
        const desc = describeOcrTarget(t);
        if (!desc) {
          setStatus("Not a scanned image or PDF link — try again (Esc to cancel)", "error");
          return;
        }
        exitOcrPick();
        runOcrPipeline(desc);
      };
      _ocrKey = (ev) => {
        if (ev.key === "Escape") {
          ev.preventDefault();
          ev.stopPropagation();
          exitOcrPick("Pick cancelled");
        }
      };
      document.addEventListener("mouseover", _ocrHover, true);
      document.addEventListener("click", _ocrClick, true);
      window.addEventListener("keydown", _ocrKey, true);
      setStatus("Click a scanned image or a PDF link (Esc to cancel)");
    }
    ocrBtn.addEventListener("click", enterOcrPick);

    let ocrBusy = false;
    async function runOcrPipeline(desc) {
      if (ocrBusy) return;
      ocrBusy = true;
      ocrBtn.disabled = true;
      try {
        setStatus(desc.kind === "pdf" ? "Reading the scanned PDF…" : "Reading the scan…");
        const result = await ocrFetchAndRecognize(desc.url, ocrLangHint(pageLang));
        let text = (result.text || "").trim();
        if (!text) {
          setStatus("No readable text found in that document", "error");
          return;
        }
        const srcLang = dominantScript(text) || "en";
        const tgt = resolvedLang() || srcLang;
        // Simplify first (rule-based, offline). A failure here is not
        // fatal — the raw OCR text is already the accessibility win.
        try {
          setStatus("Simplifying…");
          const pieces = splitIntoSentences(text, 1500);
          const simplified = [];
          for (const piece of pieces) {
            simplified.push(await simplifyChunk(piece, srcLang));
          }
          text = simplified.join(" ");
        } catch (err) {
          console.warn("[AaaS] OCR simplify failed:", err);
        }
        if (tgt !== srcLang) {
          try {
            setStatus(`Translating → ${LANG_DISPLAY[tgt] || tgt}…`);
            const pieces = splitIntoSentences(text, 800);
            const translated = [];
            for (const piece of pieces) {
              translated.push(
                stripPassthroughAnnotation(
                  await translateChunk(piece, srcLang, tgt, { timeoutMs: 20000 }),
                ),
              );
            }
            text = translated.join(" ");
          } catch (err) {
            console.warn("[AaaS] OCR translate failed:", err);
            setStatus("Could not translate — showing the original text", "error");
          }
        }
        ocrTextEl.textContent = text;
        ocrOverlay.setAttribute("data-open", "true");
        ocrTextEl.focus();
        if (result.engine === "mock") {
          setStatus("Notice ready (mock OCR — install tesseract for real scans)", "error");
        } else {
          setStatus("Notice ready", "ok");
        }
      } catch (err) {
        setStatus(`Could not read the document: ${err.message}`, "error");
      } finally {
        ocrBusy = false;
        ocrBtn.disabled = false;
      }
    }

    function closeOcrOverlay() {
      ocrOverlay.setAttribute("data-open", "false");
      if (ocrReading) {
        ocrReading = false;
        player.stop();
        ocrReadBtn.textContent = "🔊 Read aloud";
      }
    }
    ocrCloseBtn.addEventListener("click", closeOcrOverlay);

    ocrCopyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(ocrTextEl.textContent || "");
        setStatus("Copied to clipboard", "ok");
      } catch {
        setStatus("Copy failed — select the text manually", "error");
      }
    });

    let ocrReading = false;
    ocrReadBtn.addEventListener("click", async () => {
      if (ocrReading) {
        ocrReading = false;
        player.stop();
        ocrReadBtn.textContent = "🔊 Read aloud";
        return;
      }
      if (isReading) {
        setStatus("Already reading the page — press Esc to stop that first", "error");
        return;
      }
      const text = (ocrTextEl.textContent || "").trim();
      if (!text) return;
      ocrReading = true;
      ocrReadBtn.textContent = "⏹ Stop";
      const lang = dominantScript(text) || resolvedLang() || "en";
      try {
        player.reset();
        const draining = player.drain();
        const chunks = splitIntoSentences(text, CONFIG.maxChars);
        let enqueued = 0;
        for (const chunk of chunks) {
          if (!ocrReading) break;
          try {
            const blob = await synthesise(chunk, lang);
            if (!ocrReading) break;
            player.enqueue(blob);
            enqueued++;
          } catch (err) {
            console.warn("[AaaS] OCR TTS chunk failed:", err);
          }
        }
        player.finish();
        await draining;
        if (!enqueued) setStatus("TTS unavailable — check the gateway", "error");
      } finally {
        ocrReading = false;
        ocrReadBtn.textContent = "🔊 Read aloud";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
