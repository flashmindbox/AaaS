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
 *     data-key="aaas_live_<your tenant key>"
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
  // OpenDyslexic (SIL-OFL): bottom-weighted letters that resist
  // flipping/rotation. The Comfortable-letters stack always preferred
  // it; bundling it makes that first choice real on every machine
  // (user-picked over Atkinson from a side-by-side demo, 2026-07-06).
  const OPENDYSLEXIC_WOFF_BASE64 = "__AAAS_OPENDYSLEXIC_B64__";
  const OPENDYSLEXIC_BOLD_WOFF_BASE64 = "__AAAS_OPENDYSLEXIC_BOLD_B64__";
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
    // A page that embeds widget.js talks to the gateway it was served from,
    // even when the extension is also installed — otherwise the offline
    // laptop demo would follow the extension's hosted URL and break.
    gateway:
      CURRENT_SCRIPT?.dataset.gateway ||
      window.AAAS_GATEWAY_URL ||
      SCRIPT_ORIGIN ||
      HTML_DATASET.aaasGateway ||
      "http://127.0.0.1:8000",
    apiKey:
      CURRENT_SCRIPT?.dataset.key ||
      window.AAAS_API_KEY ||
      HTML_DATASET.aaasKey ||
      // Public extension key (non-operator "aaas-companion" tenant).
      "aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18",
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
  // A page that embeds widget.js sits next to its own gateway (no CSP
  // problem), and the server voice starts in ~1-3 s against 6-14 s for
  // loading the in-browser model — so on-device mode only applies to the
  // copy the extension injects, even when the extension is also installed.
  const ON_DEVICE = HTML_DATASET.aaasOnDevice === "1" && !CURRENT_SCRIPT;
  const EXT_ROOT = HTML_DATASET.aaasExtRoot || "";

  // Set by the extension's isolated-world bridge (inject-config.js). When
  // present and the page's CSP blocks our direct fetch to the gateway,
  // translation is retried through the background service worker (which
  // isn't bound by page CSP). On a plain <script> embed this is empty and
  // the gateway is the only translation path.
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
  // v2: TTS now verbalises numbers and splices mixed-script audio
  // server-side — the version tag orphans stale pre-fix clips in the
  // persistent cache instead of replaying broken audio forever.
  const phraseKey = (lang, text) => `v2:${lang}:${text}`;

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
    // Translations saved before the server's number guard could carry
    // altered dates/amounts ("48. 5 ଲକ୍ଷ", 2026→2021), so translate keys
    // get a generation prefix and old rows are never read (they age out
    // via MAX_ENTRIES). Deliberately NOT a DB version bump: an upgrade
    // blocks until every other tab with the old widget closes, which
    // froze the document reader mid-demo.
    const KEY_GEN = { translate: "g2|" };
    const STORES = ["tts", "translate"];
    // Soft caps so the cache can't grow without bound; oldest writes evicted.
    const MAX_ENTRIES = { tts: 600, translate: 2000 };
    let dbPromise = null;

    function openDb() {
      if (dbPromise) return dbPromise;
      dbPromise = new Promise((resolve) => {
        let req;
        try {
          // No version: opens whatever exists (a fresh DB starts at 1),
          // so a profile that ever saw another version can't VersionError.
          req = indexedDB.open(DB_NAME);
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
        req.onsuccess = () => {
          const db = req.result;
          // Never be the tab that blocks someone else's upgrade.
          db.onversionchange = () => {
            db.close();
            dbPromise = null; // next get/put reopens instead of failing
          };
          if (STORES.some((s) => !db.objectStoreNames.contains(s))) {
            db.close();
            resolve(null);
            return;
          }
          resolve(db);
        };
        req.onerror = () => resolve(null);
        req.onblocked = () => resolve(null);
      });
      return dbPromise;
    }

    async function get(store, key) {
      key = (KEY_GEN[store] || "") + key;
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
      key = (KEY_GEN[store] || "") + key;
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
  // A terminator only ends a sentence when whitespace or the end follows,
  // so "05.04.2026" / "Rs.1000" stay whole (they were split and rejoined
  // as "05. 04. 2026").
  const _SENTENCE_SPLIT_RE = /[\s\S]+?(?:[.!?।॥]+(?=\s|$)\s*|$)/g;
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
      // includes list-decoration bullets — sites render the same link
      // with and without them ("• M.Tech Admission" vs "M.Tech
      // Admission"), which must normalize identically
      .replace(/[.,!?;:()"'«»।॥/\-–—•·▪●○◦►▶»*+|]+/g, " ")
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
          // Odia STT often glues the trailing verb onto the command and
          // slips one letter: "ଅନୁବାଦ କର" came back as "ଅନୁବାଜକ". Compare
          // the phrase against the same-length start of what was heard,
          // allowing a single slip on phrases of 5+ letters. Only Indic
          // phrases, and only a glued fragment of 1-2 letters, so a link
          // like "Search Results" still opens instead of running "search".
          const extra = norm.length - p.length;
          if (p.length >= 5 && extra >= 1 && extra <= 2 && /[^\x00-\x7F]/.test(p) &&
              editDistance(norm.slice(0, p.length), p) <= 1) {
            return cmd.action;
          }
          // Phonetic pass: "rid pej" (romanized Odia STT hearing
          // English) still finds "read page".
          const nq = phoneticSquash(norm);
          const pq = phoneticSquash(p);
          if (nq.length >= 3 && pq.length >= 3) {
            const sq = 1 - editDistance(nq, pq) / Math.max(nq.length, pq.length);
            if (sq >= 0.8) return cmd.action;
            const nk = consonantSkeleton(nq);
            const pk = consonantSkeleton(pq);
            if (nk.length >= 4 && pk.length >= 4) {
              const sk = 1 - editDistance(nk, pk) / Math.max(nk.length, pk.length);
              if (sk >= 0.8) return cmd.action;
            }
          }
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

  // Phonetic squash: collapse Indian-English romanization variants so
  // sound-alike words compare equal-ish ("Kantakta" -> "kantakt",
  // "Contact" -> "kontakt" — one edit apart). Applied to BOTH sides
  // before fuzzy comparison; this is what lets an Odia-only STT hear
  // English link names ("କଣ୍ଟାକ୍ଟ") and still find "Contact".
  function phoneticSquash(text) {
    let t = (text || "").toLowerCase();
    const subs = [
      ["chh", "c"], ["ch", "c"], ["ph", "f"], ["bh", "b"], ["dh", "d"],
      ["th", "t"], ["gh", "g"], ["jh", "j"], ["kh", "k"], ["sh", "s"],
      ["ck", "k"], ["c", "k"], ["w", "v"], ["z", "j"], ["x", "ks"], ["q", "k"],
    ];
    for (const pair of subs) t = t.split(pair[0]).join(pair[1]);
    t = t.replace(/[aeiou]+/g, (m) => m[0]); // collapse vowel runs
    t = t.replace(/([a-z])\1+/g, "$1"); // collapse doubled letters
    t = t.replace(/a\b/g, ""); // romanized schwa: drop word-final 'a'
    return t.trim();
  }

  // Vowels carry most of the accent/romanization noise; consonants
  // carry the identity. "notifikesan" and "notifikatins" disagree on
  // vowels but share the skeleton "ntfksn"~"ntfktns".
  function consonantSkeleton(text) {
    return (text || "").replace(/(?!^)[aeiou]/g, "");
  }

  function _tokenSim(a, b) {
    if (a === b) return 1;
    let best = 0;
    if (a.length >= 4 && b.length >= 4) {
      best = 1 - editDistance(a, b) / Math.max(a.length, b.length);
    }
    // Odia-script tokens: matras and viramas carry the STT noise
    // ("ପେନସନ" vs "ପେନ୍ସନ୍") — compare their skeletons, the same
    // trick the glossary uses.
    const ak = odiaSkeleton(a);
    const bk = odiaSkeleton(b);
    if ((ak !== a || bk !== b) && ak.length >= 2 && bk.length >= 2) {
      const s = ak === bk ? 0.95 : 1 - editDistance(ak, bk) / Math.max(ak.length, bk.length);
      if (s > best) best = s;
    }
    const aq = phoneticSquash(a);
    const bq = phoneticSquash(b);
    if (aq && bq && aq.length >= 3 && bq.length >= 3) {
      const s = aq === bq ? 0.98 : 1 - editDistance(aq, bq) / Math.max(aq.length, bq.length);
      if (s > best) best = s;
      if (aq.length >= 5 && bq.length >= 5) {
        const ak = consonantSkeleton(aq);
        const bk = consonantSkeleton(bq);
        if (ak.length >= 3 && bk.length >= 3) {
          const sk = (1 - editDistance(ak, bk) / Math.max(ak.length, bk.length)) * 0.95;
          if (sk > best) best = sk;
        }
      }
    }
    return best;
  }

  // Score a transcript against one accessible name. 1.0 exact;
  // 0.75–0.95 containment (scaled by length ratio); otherwise a
  // token-overlap blend: coverage = how much of the transcript matched,
  // precision = how much of the name it accounts for. Tokens compare
  // raw AND phonetically squashed, whichever is stronger.
  function scoreVoiceTarget(transcript, name) {
    const t = normalizeCommandText(transcript);
    const n = normalizeCommandText(name);
    if (!t || !n) return 0;
    if (t === n) return 1;
    // Containment needs substance on BOTH sides: one-letter names
    // ("A", "A-" font-size buttons on gov sites) are contained in
    // every transcript and must never match this way.
    if (Math.min(t.length, n.length) >= 3 && (n.includes(t) || t.includes(n))) {
      const ratio = Math.min(t.length, n.length) / Math.max(t.length, n.length);
      return 0.75 + 0.2 * ratio;
    }
    const tq = phoneticSquash(t).replace(/\s+/g, "");
    const nq = phoneticSquash(n).replace(/\s+/g, "");
    if (tq && nq && Math.min(tq.length, nq.length) >= 3 && (nq.includes(tq) || tq.includes(nq))) {
      const ratio = Math.min(tq.length, nq.length) / Math.max(tq.length, nq.length);
      return 0.72 + 0.2 * ratio;
    }
    const tTokens = t.split(" ");
    const nTokens = n.split(" ");
    // One word against one word: the token similarity IS the score —
    // a counting bar only makes sense with multiple tokens.
    if (tTokens.length === 1 && nTokens.length === 1) {
      return _tokenSim(tTokens[0], nTokens[0]);
    }
    let sum = 0;
    for (const tok of tTokens) {
      let best = 0;
      for (const cand of nTokens) {
        const s = _tokenSim(tok, cand);
        if (s > best) best = s;
      }
      if (best >= 0.7) sum += best;
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
      // Hidden targets carry a small penalty so a visible match always
      // outranks an identically-named hidden one.
      let score = scoreVoiceTarget(transcript, target.name || "");
      if (target.hidden) score *= 0.92;
      if (score > 0.25) {
        ranked.push({
          score,
          name: target.name,
          element: target.element || null,
          hidden: !!target.hidden,
        });
      }
    }
    ranked.sort((a, b) => b.score - a.score);
    return ranked;
  }

  // Real sites render the same link several times — header + footer
  // copies, and news tickers that repeat a notice with its title
  // truncated ("NOTICE INVITING… COUNTRY LIQUO…"). Same name, or one
  // name being a truncation of the other, means same intent.
  function sameVoiceName(a, b) {
    const na = normalizeCommandText(a || "");
    const nb = normalizeCommandText(b || "");
    if (!na || !nb) return false;
    if (na === nb) return true;
    const min = Math.min(na.length, nb.length);
    return min >= 20 && na.slice(0, min - 3) === nb.slice(0, min - 3);
  }

  // Two ranked entries are the same intent when their names match
  // (exact or truncation) OR they are links to the SAME destination —
  // a ticker and a notice list often word the same document
  // differently.
  function sameVoiceTarget(a, b) {
    if (sameVoiceName(a.name, b.name)) return true;
    const ha = a.element && a.element.tagName === "A" ? a.element.href : "";
    const hb = b.element && b.element.tagName === "A" ? b.element.href : "";
    return !!ha && ha === hb;
  }

  // Act on a clearly-best candidate, never on an ambiguous one: a sure
  // hit clicks, a plausible hit clicks only with daylight to the
  // runner-up, everything else just reports candidates.
  function shouldActOnVoiceMatch(ranked) {
    if (!ranked.length) return false;
    const top = ranked[0].score;
    if (top >= VOICE_SURE_THRESHOLD) return true;
    if (top < VOICE_ACT_THRESHOLD) return false;
    // Duplicate runner-ups are the same intent, not ambiguity —
    // measure the gap to the first genuinely DIFFERENT rival.
    const rival = ranked.find((r) => !sameVoiceTarget(r, ranked[0]));
    return !rival || top - rival.score >= VOICE_AMBIGUITY_GAP;
  }

  const VOICE_TARGET_SELECTOR =
    'a[href], button, [role="button"], [role="link"], input[type="submit"], input[type="button"], summary';

  function collectVoiceTargets() {
    const seen = new Set();
    const out = [];
    document.querySelectorAll(VOICE_TARGET_SELECTOR).forEach((el) => {
      const visible = isVisible(el);
      // Real government sites keep their most-asked-for links (notices,
      // tenders) inside carousel slides and dropdown menus — hidden at
      // any given moment. A hidden <a href> still navigates on click,
      // and the user asked for it BY NAME, so anchors join the pool
      // flagged hidden (ranked at a penalty). Hidden buttons stay
      // excluded — their click behavior is unpredictable.
      if (!visible && !(el.tagName === "A" && el.getAttribute("href"))) return;
      if (el.closest("[data-aaas-widget]")) return;
      // getAccessibleName skips <input> value; submit buttons name
      // themselves through it ("<input type=submit value=Search>").
      const name = getAccessibleName(el) || (el.tagName === "INPUT" ? (el.value || "").trim() : "");
      if (!name) return;
      const key = name + "§" + (el.getAttribute("href") || el.tagName);
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ name, element: el, hidden: !visible });
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

  // Human name for a document candidate, best-effort: alt text /
  // figcaption for images, link text / filename for PDFs. Shown in the
  // chooser list, so it must never be empty.
  function ocrCandidateName(el, kind) {
    if (kind === "image") {
      const alt = (el.getAttribute("alt") || "").trim();
      if (alt) return alt;
      const fig = el.closest ? el.closest("figure") : null;
      const cap = fig && fig.querySelector ? fig.querySelector("figcaption") : null;
      if (cap && cap.textContent.trim()) return cap.textContent.replace(/\s+/g, " ").trim();
      return "Image on this page";
    }
    const text = (el.textContent || "").replace(/\s+/g, " ").trim();
    if (text) return text;
    try {
      const name = decodeURIComponent(new URL(el.href).pathname.split("/").pop());
      if (name) return name;
    } catch {}
    return "PDF document";
  }

  // Documents the widget can read on this page: document-sized images
  // (icons and logos filtered out by size) and PDF links. The user
  // never has to hunt — this list drives the chooser.
  const OCR_MIN_IMG_W = 200;
  const OCR_MIN_IMG_H = 150;

  function collectOcrCandidates() {
    const out = [];
    const seen = new Set();
    document.querySelectorAll("img").forEach((img) => {
      if (!isVisible(img)) return;
      if (img.closest("[data-aaas-widget]")) return;
      const w = img.naturalWidth || img.width || 0;
      const h = img.naturalHeight || img.height || 0;
      if (w < OCR_MIN_IMG_W || h < OCR_MIN_IMG_H) return;
      const url = img.currentSrc || img.src || "";
      if (!url || seen.has(url)) return;
      seen.add(url);
      out.push({ kind: "image", url, name: ocrCandidateName(img, "image"), element: img });
    });
    document.querySelectorAll("a[href]").forEach((a) => {
      if (a.closest("[data-aaas-widget]")) return;
      if (!isVisible(a)) return;
      let path = "";
      try {
        path = new URL(a.href, document.baseURI).pathname;
      } catch {
        return;
      }
      if (!/\.pdf$/i.test(path)) return;
      if (seen.has(a.href)) return;
      seen.add(a.href);
      out.push({ kind: "pdf", url: a.href, name: ocrCandidateName(a, "pdf"), element: a });
    });
    return out;
  }

  /* ---------- guided voice form fill ----------
   * "Speak to fill" walks a form field by field: highlight, speak the
   * label, listen, clean the answer to fit the field type, write it,
   * move on. Pure helpers live here (smoke-testable); the loop itself
   * is in mount(). It NEVER submits — the user always presses Submit.
   */

  /* Odia → Latin romanization for form values. Spoken names and
   * places must reach English-only forms as the SAME name in Latin
   * letters ("ପୂର୍ଣ୍ଣଚନ୍ଦ୍ର" -> "Purnnachandra", "ବଡ଼ଚଣା" ->
   * "Badachana") — meaning-translation turns names into nonsense
   * ("full moon", "firework") and raw Odia is rejected by most sites.
   * Rule-based phonetic mapping: consonants carry an inherent 'a'
   * unless a matra or virama follows; words are title-cased.
   */
  const ODIA_VOWELS = {
    "ଅ": "a", "ଆ": "aa", "ଇ": "i", "ଈ": "i", "ଉ": "u", "ଊ": "u",
    "ଋ": "ru", "ୠ": "ru", "ଏ": "e", "ଐ": "ai", "ଓ": "o", "ଔ": "au",
  };
  const ODIA_CONSONANTS = {
    "କ": "k", "ଖ": "kh", "ଗ": "g", "ଘ": "gh", "ଙ": "ng",
    "ଚ": "ch", "ଛ": "chh", "ଜ": "j", "ଝ": "jh", "ଞ": "n",
    "ଟ": "t", "ଠ": "th", "ଡ": "d", "ଢ": "dh", "ଣ": "n",
    "ତ": "t", "ଥ": "th", "ଦ": "d", "ଧ": "dh", "ନ": "n",
    "ପ": "p", "ଫ": "ph", "ବ": "b", "ଭ": "bh", "ମ": "m",
    "ଯ": "j", "ର": "r", "ଲ": "l", "ଳ": "l", "ଵ": "v", "ୱ": "w",
    "ଶ": "sh", "ଷ": "sh", "ସ": "s", "ହ": "h", "ୟ": "y",
    "ଡ଼": "d", "ଢ଼": "rh",
  };
  const ODIA_MATRAS = {
    "ା": "a", "ି": "i", "ୀ": "i", "ୁ": "u", "ୂ": "u",
    "ୃ": "ru", "ୄ": "ru", "େ": "e", "ୈ": "ai", "ୋ": "o", "ୌ": "au",
  };
  const ODIA_SIGNS = { "ଂ": "n", "ଁ": "n", "ଃ": "h", "।": ".", "॥": "." };

  function romanizeOdia(text) {
    let out = "";
    let pendingA = false; // a consonant's inherent vowel, not yet emitted
    const flush = () => {
      if (pendingA) {
        out += "a";
        pendingA = false;
      }
    };
    for (const ch of text || "") {
      if (ch === "଼") continue; // nukta — modifier only
      if (ODIA_CONSONANTS[ch] !== undefined) {
        flush();
        out += ODIA_CONSONANTS[ch];
        pendingA = true;
      } else if (ODIA_MATRAS[ch] !== undefined) {
        pendingA = false;
        out += ODIA_MATRAS[ch];
      } else if (ch === "୍") {
        pendingA = false; // virama kills the inherent vowel
      } else if (ODIA_VOWELS[ch] !== undefined) {
        flush();
        out += ODIA_VOWELS[ch];
      } else if (ODIA_SIGNS[ch] !== undefined) {
        flush();
        out += ODIA_SIGNS[ch];
      } else if (ch >= "୦" && ch <= "୯") {
        flush();
        out += String(ch.charCodeAt(0) - 0x0b66);
      } else {
        flush();
        out += ch;
      }
    }
    flush();
    // Title-case each word so names look like names.
    return out.replace(/(^|[\s,.-])([a-z])/g, (m, sep, c) => sep + c.toUpperCase());
  }

  /* Spoken numbers arrive as WORDS, not digits — Odia words (ପାଞ୍ଚ),
   * English words written phonetically in Odia script by the STT
   * (ଫାଇଭ, ଥ୍ରୀ), plain English ("five"), or romanized forms
   * ("Phaiba"). This is what real STT calls inverse text
   * normalization; without it, phone fields got word salad and
   * number inputs rejected everything. Fuzzy token matching (the
   * voice-nav editDistance) absorbs accent spellings.
   */
  const DIGIT_WORDS = {
    0: ["ଶୂନ", "ଶୂନ୍ୟ", "ଜିରୋ", "ଜିରର", "zero", "jiro", "shunya", "suna", "o"],
    1: ["ଏକ", "ୱାନ", "ଵାନ", "one", "wan", "eka"],
    2: ["ଦୁଇ", "ଟୁ", "two", "tu", "dui"],
    3: ["ତିନି", "ଥ୍ରୀ", "ଥ୍ରି", "three", "thri", "tini"],
    4: ["ଚାରି", "ଫୋର", "ଫୋର୍", "four", "phora", "for", "chari"],
    5: ["ପାଞ୍ଚ", "ଫାଇଭ", "ଫାଇବ", "five", "phaibh", "phaiba", "pancha"],
    6: ["ଛଅ", "ସିକ୍ସ", "ସିକସ", "six", "sikas", "sikash", "sikashas", "chhaa"],
    7: ["ସାତ", "ସେଭେନ", "ସେବେନ", "seven", "sebhen", "sebhena", "sata"],
    8: ["ଆଠ", "ଏଟ", "ଏଇଟ", "eight", "eit", "eta", "atha"],
    9: ["ନଅ", "ନାଇନ", "ନାଇନ୍", "nine", "nain", "naina", "naa"],
  };
  const TENS_WORDS = {
    10: ["ଦଶ", "ten", "dasha"],
    11: ["ଏଗାର", "ଏଗାରା", "eleven", "egara"],
    12: ["ବାର", "twelve", "bara"],
    13: ["ତେର", "thirteen", "tera"],
    14: ["ଚଉଦ", "fourteen", "chauda"],
    15: ["ପନ୍ଦର", "fifteen", "pandara"],
    16: ["ଷୋହଳ", "sixteen", "shohala"],
    17: ["ସତର", "seventeen", "satara"],
    18: ["ଅଠର", "eighteen", "athara"],
    19: ["ଉଣେଇଶ", "nineteen", "uneisha"],
    20: ["କୋଡ଼ିଏ", "twenty", "kodie"],
    30: ["ତିରିଶ", "thirty", "tirisha"],
    40: ["ଚାଳିଶ", "forty", "chalisha"],
    50: ["ପଚାଶ", "fifty", "pachasha"],
    60: ["ଷାଠିଏ", "sixty", "shathie"],
    70: ["ସତୁରି", "seventy", "saturi"],
    80: ["ଅଶୀ", "eighty", "ashi"],
    90: ["ନବେ", "ninety", "nabe"],
  };
  const REPEAT_WORDS = { 2: ["ଡବଲ", "ଡବଲ୍", "double", "dabal"], 3: ["ଟ୍ରିପଲ", "triple", "tripal"] };

  function _matchNumberWord(token, table) {
    const t = token.toLowerCase();
    for (const value of Object.keys(table)) {
      for (const word of table[value]) {
        if (t === word) return value;
        if (t.length >= 2 && word.length >= 2) {
          const sim = 1 - editDistance(t, word) / Math.max(t.length, word.length);
          if (sim >= 0.7) return value;
        }
      }
    }
    return null;
  }

  // Parse a spoken number phrase into a digit string, or null when
  // the speech clearly wasn't a number. `allowTens` sums a tens word
  // with a following unit ("ଚାଳିଶ ପାଞ୍ଚ" -> 45) for age-like fields.
  function spokenToDigits(text, allowTens) {
    const tokens = toWesternDigits(text || "")
      .split(/[\s,.\-।॥]+/)
      .filter(Boolean);
    if (!tokens.length) return null;
    const parts = [];
    let matched = 0;
    let repeat = 1;
    for (const token of tokens) {
      if (/^\d+$/.test(token)) {
        parts.push(token.repeat(repeat));
        repeat = 1;
        matched++;
        continue;
      }
      const rep = _matchNumberWord(token, REPEAT_WORDS);
      if (rep !== null) {
        repeat = Number(rep);
        matched++;
        continue;
      }
      const digit = _matchNumberWord(token, DIGIT_WORDS);
      if (digit !== null) {
        parts.push(String(digit).repeat(repeat));
        repeat = 1;
        matched++;
        continue;
      }
      if (allowTens) {
        const tens = _matchNumberWord(token, TENS_WORDS);
        if (tens !== null) {
          parts.push({ tens: Number(tens) });
          repeat = 1;
          matched++;
          continue;
        }
      }
      // unknown token — tolerated, but counts against confidence
    }
    if (!parts.length || matched / tokens.length < 0.6) return null;
    // Combine: a tens marker absorbs one following unit digit (45),
    // otherwise contributes its own two digits (50).
    let out = "";
    for (let i = 0; i < parts.length; i++) {
      const p = parts[i];
      if (typeof p === "string") {
        out += p;
        continue;
      }
      const next = parts[i + 1];
      if (typeof next === "string" && next.length === 1 && next !== "0") {
        out += String(p.tens + Number(next));
        i++;
      } else {
        out += String(p.tens);
      }
    }
    return out || null;
  }

  // Clean a spoken answer to fit the field it's going into.
  function normalizeSpokenValue(type, text) {
    const t = (text || "").trim();
    if (!t) return t;
    if (type === "tel" || type === "number") {
      // Digits first ("98 76 54" -> "987654"); then spoken-word
      // parsing ("ଫାଇଭ ଥ୍ରୀ" -> "53"). If neither yields a number,
      // return EMPTY — words in a phone field are worse than a blank
      // the user is asked to repeat.
      const digits = toWesternDigits(t).replace(/\D+/g, "");
      if (digits) return digits;
      return spokenToDigits(t, type === "number") || "";
    }
    if (type === "email") {
      return toWesternDigits(t)
        .toLowerCase()
        .replace(/\s+(at|@)\s+/g, "@")
        .replace(/\s+dot\s+/g, ".")
        .replace(/[\s।]+/g, "")
        .replace(/\.+$/, "");
    }
    // Plain text: drop a trailing danda/period the STT likes to add.
    return t.replace(/[।.]+$/, "").trim();
  }

  // The editable, visible, fillable fields on the page, in DOM order.
  const GUIDED_INPUT_TYPES = ["text", "search", "email", "url", "tel", "number", ""];

  function collectFormFields() {
    const out = [];
    document.querySelectorAll("input, textarea").forEach((el) => {
      if (el.closest("[data-aaas-widget]")) return;
      if (el.disabled || el.readOnly) return;
      if (el.tagName === "INPUT") {
        const type = (el.type || "text").toLowerCase();
        if (!GUIDED_INPUT_TYPES.includes(type)) return;
      }
      if (!isVisible(el)) return;
      out.push(el);
    });
    return out;
  }

  async function probeGateway() {
    const healthy = async (base) => {
      try {
        const r = await fetch(`${base}/healthz`, { cache: "no-store" });
        return r.ok;
      } catch {
        return false;
      }
    };
    if (await healthy(CONFIG.gateway)) return true;
    // Extension only: the hosted server is unreachable (no internet at the
    // venue) but the laptop's offline bundle may be running — use it.
    const fallback = HTML_DATASET.aaasGatewayFallback;
    if (EXT_BRIDGE && fallback && fallback !== CONFIG.gateway && (await healthy(fallback))) {
      console.warn("[AaaS] gateway unreachable, using local fallback:", fallback);
      CONFIG.gateway = fallback;
      return true;
    }
    return false;
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
  // Sizes are px, not rem: rem follows the HOST page's <html> font-size,
  // so sites with `html { font-size: 62.5% }` shrank the whole panel.
  // 1rem was 16px on our demo sites; these values keep that look.
  const STYLE = `
    ${FONT_FACE_CSS}
    :host { all: initial; }
    * { box-sizing: border-box; font-family: 'Noto Sans Oriya', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
    .fab {
      position: fixed;
      right: 20px;
      bottom: 20px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: #1a66cc;
      color: white;
      border: 0;
      box-shadow: 0 6px 18px rgba(0,0,0,0.25);
      font-size: 25.6px;
      cursor: pointer;
      z-index: 2147483647;
    }
    .fab:hover { background: #2d7ad9; }
    .fab:focus-visible { outline: 3px solid #ffcf33; outline-offset: 2px; }

    .panel {
      position: fixed;
      right: 20px;
      bottom: 88px;
      width: min(304px, calc(100vw - 40px));
      background: #0f1419;
      color: #e8edf2;
      border-radius: 16px;
      border: 1px solid #253040;
      box-shadow: 0 18px 40px rgba(0,0,0,0.35);
      padding: 0 0 9.6px;
      z-index: 2147483647;
      display: none;
    }
    .panel[data-open="true"] { display: block; }

    .whead {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10.4px 12.8px 8.8px;
      border-bottom: 1px solid #1d2733;
      margin-bottom: 9.6px;
    }
    .title { font-size: 15.2px; font-weight: 700; margin: 0; flex: 1; }

    select.lang {
      background: #1b2530;
      color: #e8edf2;
      border: 1px solid #2c3a4c;
      border-radius: 8px;
      padding: 4.8px 6.4px;
      font-size: 13.12px;
      max-width: 136px;
    }
    select.lang:focus-visible { outline: 2px solid #ffcf33; outline-offset: 1px; }

    /* Icon-grid tiles: Odia-first label, English under it. Same class
       hooks as the old full-width buttons so all wiring is unchanged. */
    .agrid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 7px;
      padding: 0 9.6px;
      margin-bottom: 8.8px;
    }
    button.action {
      width: 100%;
      background: #1a2430;
      color: #e8edf2;
      border: 1px solid #2c3a4c;
      border-radius: 12px;
      padding: 8.8px 4px 8px;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      min-height: 73.6px;
    }
    button.action .ic { font-size: 21.6px; line-height: 1.15; }
    button.action .or { font-size: 13.76px; font-weight: 700; line-height: 1.2; }
    button.action .en { font-size: 10.24px; color: #9fb2c8; line-height: 1.25; text-align: center; }
    button.action:hover:not(:disabled) { background: #24344a; border-color: #4a6a96; }
    button.action:focus-visible { outline: 2px solid #ffcf33; outline-offset: 1px; }
    button.action:disabled { opacity: 0.55; cursor: not-allowed; }
    button.action.stop { background: #7c2f35; border-color: #c7444c; }
    button.action.stop:hover { background: #94393f; }
    button.action.mic .ic::after { content: ""; }
    button.action.mic.recording,
    button.action.voice.recording { background: #7c2f35; border-color: #c7444c; animation: pulse 1.2s infinite; }
    @keyframes pulse { 50% { box-shadow: 0 0 0 6px rgba(199,68,76,0.35); } }

    .transcript {
      margin: 4.8px 12.8px 0;
      padding: 8.8px 11.2px;
      background: #1b2530;
      border-radius: 8px;
      border: 1px solid #2c3a4c;
      font-size: 14.4px;
      color: #d0dce8;
      min-height: 1.2em;
      word-break: break-word;
    }
    .transcript:empty { display: none; }

    /* Tappable "did you mean" candidates after an unsure voice
       command — a dead-end error becomes a one-tap success. */
    .voice-choices {
      margin: 5.6px 12.8px 0;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .voice-choices:empty { display: none; }
    .voice-choices .vc-hint { font-size: 11.52px; color: #9fb2c8; }
    .voice-choices button {
      background: #1d2938;
      border: 1px solid #4a6a96;
      border-radius: 9px;
      color: #e8edf2;
      padding: 8px 9.6px;
      font-size: 13.6px;
      text-align: left;
      cursor: pointer;
      /* Long notice titles must WRAP — truncation makes two different
         notices look identical. Cap at three lines. */
      white-space: normal;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .voice-choices button:hover { background: #24344a; border-color: #ffcf33; }

    .status {
      margin: 7.2px 12.8px 0;
      min-height: 20.8px;
      color: #8b96a5;
      font-size: 13.12px;
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
      padding: 6.4px 9.6px;
      font-weight: 600;
      animation: aaas-notice-pop 0.35s ease;
    }
    @keyframes aaas-notice-pop {
      0%   { transform: scale(0.94); opacity: 0.3; }
      55%  { transform: scale(1.03); }
      100% { transform: scale(1); opacity: 1; }
    }

    .meta {
      margin: 4.8px 12.8px 0;
      font-size: 11.52px;
      color: #5e6778;
    }

    /* Skip / replay controls — visible only while reading, bottom
       right beside the "Playing N/M" status. Buttons for what ← / →
       already did on the keyboard; non-technical users never find
       keyboard shortcuts. */
    .playctl {
      display: none;
      position: absolute;
      right: 9.6px;
      bottom: 8px;
      gap: 5.6px;
    }
    .panel[data-reading="true"] .playctl { display: flex; }
    .panel[data-reading="true"] .status,
    .panel[data-reading="true"] .meta { margin-right: 89.6px; }
    .playctl button {
      width: 36px;
      height: 34px;
      background: #1a2430;
      border: 1px solid #31415a;
      border-radius: 9px;
      color: #e8edf2;
      font-size: 15.2px;
      cursor: pointer;
      line-height: 1;
    }
    .playctl button:hover { background: #24344a; border-color: #4a6a96; }
    .playctl button:focus-visible { outline: 2px solid #ffcf33; outline-offset: 1px; }

    /* Reading-comfort settings: one collapsed row, toggles inside. */
    .comfort {
      margin: 0 9.6px 5.6px;
      border: 1px solid #2c3a4c;
      border-radius: 12px;
      overflow: hidden;
    }
    .comfort-head {
      width: 100%;
      background: #161f2a;
      color: #cdd9e5;
      border: 0;
      padding: 8px 11.2px;
      font-size: 12.8px;
      cursor: pointer;
      text-align: left;
      display: flex;
      align-items: center;
      gap: 6.4px;
    }
    .comfort-head .chev { margin-left: auto; transition: transform 0.15s; }
    .comfort.open .comfort-head .chev { transform: rotate(180deg); }
    .comfort-body { display: none; background: #121a24; padding: 6px 8px 4px; }
    .comfort.open .comfort-body { display: block; }

    label.toggle {
      display: grid;
      grid-template-columns: auto 1fr;
      grid-template-rows: auto auto;
      column-gap: 8.8px;
      align-items: center;
      padding: 6.4px 7.2px;
      border-radius: 8px;
      margin-bottom: 2.4px;
      cursor: pointer;
      user-select: none;
    }
    label.toggle:hover { background: #1a2430; }
    label.toggle input[type="checkbox"] {
      grid-row: 1 / span 2;
      width: 18px;
      height: 18px;
      accent-color: #1a66cc;
      cursor: pointer;
    }
    label.toggle .toggle-text {
      font-size: 13.6px;
      color: #e8edf2;
      font-weight: 600;
    }
    label.toggle .toggle-hint {
      font-size: 11.2px;
      color: #8b96a5;
    }

    .read-row,
    .tile-wrap {
      position: relative;
      display: block;
    }
    button.pause {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 30px;
      height: 30px;
      padding: 0;
      background: #10151d;
      border: 1px solid #c7444c;
      color: #e8edf2;
      border-radius: 8px;
      font-size: 13.6px;
      cursor: pointer;
      display: none;
      z-index: 2;
    }
    button.pause:hover:not(:disabled) { background: #24303e; }
    .read-row[data-playing="true"] button.pause { display: block; }
    .read-row button.action,
    .tile-wrap button.action { width: 100%; height: 100%; }

    /* Undo overlay on the Translate / Easy Read tiles — appears once
       that action has rewritten the page, same pattern as the pause
       button on the Read tile. */
    button.undo {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 30px;
      height: 30px;
      padding: 0;
      background: #10151d;
      border: 1px solid #4a6a96;
      color: #e8edf2;
      border-radius: 8px;
      font-size: 13.6px;
      cursor: pointer;
      display: none;
      z-index: 2;
    }
    button.undo:hover { background: #24303e; border-color: #ffcf33; }
    .tile-wrap[data-undoable="true"] button.undo { display: block; }

    .shortcuts-link {
      display: inline-block;
      margin-top: 4px;
      margin-bottom: 4.8px;
      background: none;
      border: 0;
      padding: 0;
      color: #6e95cc;
      font-size: 12.8px;
      cursor: pointer;
      text-decoration: underline dotted;
    }
    .shortcuts-link:hover { color: #8fb0e0; }

    .shortcuts-overlay {
      position: absolute;
      right: 16px;
      bottom: 16px;
      left: 16px;
      background: #1b2530;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      padding: 12.8px 14.4px;
      font-size: 13.12px;
      color: #d0dce8;
      display: none;
      z-index: 10;
    }
    .shortcuts-overlay[data-open="true"] { display: block; }
    .shortcuts-overlay h4 {
      margin: 0 0 8px;
      font-size: 14.08px;
      color: #e8edf2;
    }
    .shortcuts-overlay dl {
      margin: 0;
      display: grid;
      grid-template-columns: auto 1fr;
      row-gap: 4.48px;
      column-gap: 12.8px;
    }
    .shortcuts-overlay dt {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      color: #ffcf33;
    }
    .shortcuts-overlay dd { margin: 0; }
    .shortcuts-overlay .close-overlay {
      position: absolute;
      top: 4.8px;
      right: 8px;
      background: none;
      border: 0;
      color: #8b96a5;
      cursor: pointer;
      font-size: 16px;
    }

    /* Document reader modal — a big, centered, plain-language surface.
       Fixed to the viewport and appended to the shadow ROOT (not the
       panel, whose transform would re-anchor position:fixed). Sized
       and typeset for non-technical, low-literacy and elderly users:
       large text, generous spacing, few big buttons. */
    .docmodal {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(8, 12, 18, 0.6);
      z-index: 2147483647;
    }
    .docmodal[data-open="true"] { display: flex; }
    .docmodal-box {
      background: #16202b;
      border: 1px solid #31415a;
      border-radius: 16px;
      width: min(92vw, 560px);
      max-height: 84vh;
      display: flex;
      flex-direction: column;
      padding: 17.6px 19.2px 19.2px;
      color: #e8edf2;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.5);
      position: relative;
    }
    .docmodal-title {
      margin: 0 32px 12px 0;
      font-size: 18.4px;
      font-weight: 700;
    }
    .docmodal-close,
    .docmodal-max {
      position: absolute;
      top: 11.2px;
      background: #22303f;
      border: 0;
      border-radius: 8px;
      color: #c7d3e0;
      cursor: pointer;
      font-size: 17.6px;
      width: 32px;
      height: 32px;
      line-height: 1;
    }
    .docmodal-close { right: 12.8px; }
    .docmodal-max { right: 49.6px; font-size: 15.2px; }
    .docmodal-close:hover,
    .docmodal-max:hover { background: #2d3f52; }

    /* Maximized: near-fullscreen, inner panes grow to fill. */
    .docmodal-box.maximized {
      width: 96vw !important;
      height: 94vh;
      max-height: 94vh;
    }
    .docmodal-box.maximized .docmodal-body {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }
    .docmodal-box.maximized .doc-split {
      flex: 1;
      min-height: 0;
    }
    .docmodal-box.maximized .doc-split > * { min-height: 0; }
    .docmodal-box.maximized .doc-preview,
    .docmodal-box.maximized .doc-split .doc-text { max-height: 100%; }
    .docmodal-body {
      overflow-y: auto;
      min-height: 64px;
    }
    /* Chooser rows: one big obvious button per document. */
    .doc-row {
      display: flex;
      align-items: center;
      gap: 11.2px;
      width: 100%;
      text-align: left;
      background: #1d2938;
      border: 1px solid #31415a;
      border-radius: 10px;
      color: #e8edf2;
      padding: 12px 12.8px;
      margin-bottom: 8px;
      font-size: 15.2px;
      line-height: 1.45;
      cursor: pointer;
    }
    .doc-row:hover, .doc-row:focus { background: #24344a; border-color: #4a6a96; }
    .doc-row .doc-ico {
      flex: none;
      width: 72px;
      height: 54px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      border-radius: 6px;
      background: #0f1822;
      border: 1px solid #31415a;
      overflow: hidden;
    }
    .doc-row .doc-ico img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .doc-row .doc-kind {
      flex: none;
      font-size: 11.52px;
      color: #9fb2c8;
      border: 1px solid #31415a;
      border-radius: 6px;
      padding: 1.6px 6.4px;
      margin-left: auto;
    }
    /* Progress: big friendly step text + spinner. */
    .doc-progress {
      text-align: center;
      padding: 25.6px 8px 19.2px;
    }
    .doc-progress .doc-spin {
      width: 38.4px;
      height: 38.4px;
      margin: 0 auto 14.4px;
      border: 4px solid #2c3a4c;
      border-top-color: #ffcf33;
      border-radius: 50%;
      animation: aaas-doc-spin 0.9s linear infinite;
    }
    @keyframes aaas-doc-spin { to { transform: rotate(360deg); } }
    .doc-progress .doc-step { font-size: 17.6px; font-weight: 600; }
    .doc-progress .doc-substep { font-size: 14.08px; color: #9fb2c8; margin-top: 6.4px; }
    /* Result: large-print reading text. */
    .doc-text {
      user-select: text;
      -webkit-user-select: text;
      font-size: 16.8px;
      line-height: 1.85;
      white-space: pre-wrap;
      background: #101820;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      padding: 12.8px 14.4px;
    }
    /* Side-by-side result: the document on the left, its text on the
       right, so the user SEES which page is being spoken. */
    .docmodal-box.with-preview { width: min(94vw, 920px); }
    .doc-split {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
      gap: 11.2px;
    }
    @media (max-width: 760px) { .doc-split { grid-template-columns: 1fr; } }
    .doc-preview {
      overflow-y: auto;
      max-height: 56vh;
      background: #101820;
      border: 1px solid #2c3a4c;
      border-radius: 10px;
      padding: 8px;
    }
    .doc-pagelabel { font-size: 11.2px; color: #9fb2c8; margin: 2.4px 0 4.8px; }
    .doc-preview img.doc-page {
      width: 100%;
      display: block;
      border-radius: 6px;
      border: 2px solid #2c3a4c;
      margin-bottom: 8.8px;
      background: #fff;
    }
    .doc-preview img.doc-page.speaking {
      border-color: #ffcf33;
      box-shadow: 0 0 0 2px rgba(255, 207, 51, 0.35);
    }
    .doc-split .doc-text { max-height: 56vh; overflow-y: auto; }
    .doc-ptext {
      padding: 4.8px 6.4px 4.8px 8.8px;
      border-left: 3px solid transparent;
      border-radius: 4px;
    }
    .doc-ptext.speaking {
      border-left-color: #ffcf33;
      background: rgba(255, 207, 51, 0.07);
    }
    .doc-ptext .doc-chip {
      display: block;
      font-size: 10.88px;
      color: #9fb2c8;
      margin-bottom: 2.4px;
    }
    .doc-error {
      font-size: 16px;
      line-height: 1.7;
      padding: 12.8px 6.4px;
    }
    .docmodal-actions {
      display: flex;
      gap: 9.6px;
      margin-top: 14.4px;
      flex: none;
    }
    .docmodal-actions button {
      border: 0;
      border-radius: 10px;
      color: #fff;
      padding: 11.2px 12.8px;
      font-size: 15.2px;
      font-weight: 600;
      cursor: pointer;
    }
    .docmodal-actions .doc-primary {
      flex: 2;
      background: #2563b0;
      font-size: 16.32px;
    }
    .docmodal-actions .doc-primary:hover { background: #2f74c8; }
    .docmodal-actions .doc-primary.speaking { background: #c7444c; }
    .docmodal-actions .doc-secondary {
      flex: 1;
      background: #22303f;
      color: #c7d3e0;
    }
    .docmodal-actions .doc-secondary:hover { background: #2d3f52; }
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
      // Links read as their text alone — government pages are mostly links,
      // and "Link, …" before every menu item and notice drowned the content.
      link: "",
      button: "Button, ",
      checkbox: "Checkbox, ",
      radio: "Radio button, ",
      switch: "Switch, ",
      field: "Form field, ",
      image: "Image, ",
    },
    or: {
      heading: (lvl) => `ଶୀର୍ଷକ ସ୍ତର ${lvl}, `,
      link: "",
      button: "ବଟନ, ",
      checkbox: "ଚେକ୍ ବକ୍ସ, ",
      radio: "ରେଡିଓ ବଟନ, ",
      switch: "ସ୍ୱିଚ, ",
      field: "ଫର୍ମ କ୍ଷେତ୍ର, ",
      image: "ଛବି, ",
    },
    hi: {
      heading: (lvl) => `शीर्षक स्तर ${lvl}, `,
      link: "",
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
      // A link with no readable name (icon, empty banner) is skipped: reading
      // out a URL fragment or the bare word "link" is just noise.
      const name = getAccessibleName(el);
      if (!name) return null;
      return { text: name, role: "link", element: el };
    }
    if (tag === "BUTTON" || role === "button" || tag === "SUMMARY") {
      const name = getAccessibleName(el);
      if (!name) return null;
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
  // Block-level tags used as prose-flush boundaries AND as the visual
  // highlight target while read-aloud speaks that text.
  const PROSE_BLOCK_SELECTOR =
    "p, li, td, th, blockquote, figcaption, dd, dt, h1, h2, h3, h4, h5, h6, pre, summary, caption, div, body";

  function collectAtoms(root) {
    const out = [];
    let proseBuf = [];
    let proseBlockEl = null; // block element the current buffer belongs to
    const flushProse = () => {
      if (!proseBuf.length) return;
      const joined = proseBuf.join(" ").replace(/\s+/g, " ").trim();
      const blockEl = proseBlockEl;
      proseBuf = [];
      if (!joined) return;
      for (const piece of splitLongProse(joined, CONFIG.maxChars)) {
        out.push({ text: piece, prefix: "", role: "prose", element: blockEl });
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
        if (t) {
          // Flush at block boundaries so each prose atom maps to ONE
          // block element — the thing the reading highlight outlines.
          const blk = node.parentElement
            ? node.parentElement.closest(PROSE_BLOCK_SELECTOR)
            : null;
          if (blk !== proseBlockEl) {
            flushProse();
            proseBlockEl = blk;
          }
          proseBuf.push(t);
        }
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

  // Translate via the extension's background worker, which calls the gateway
  // outside the page's CSP, so this works on any site. Communicates over
  // window.postMessage because the widget runs in the page's MAIN world and
  // can't touch chrome.runtime directly.
  let _bridgeSeq = 0;
  function gatewayTranslateViaBridge(text, src, tgt, timeoutMs) {
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
        { source: "aaas-widget", kind: "translate-req", id, text, src, tgt },
        "*",
      );
    });
  }

  // Download a document through the extension's background worker, which
  // isn't bound by the page's CORS. The bytes come back base64-encoded
  // because extension messaging only carries JSON.
  function fetchDocViaBridge(url, timeoutMs) {
    return new Promise((resolve, reject) => {
      const id = "doc-" + ++_bridgeSeq;
      const onMsg = (ev) => {
        if (ev.source !== window) return;
        const d = ev.data;
        if (!d || d.source !== "aaas-bridge" || d.kind !== "fetch-doc-res" || d.id !== id) {
          return;
        }
        window.removeEventListener("message", onMsg);
        clearTimeout(timer);
        if (!d.ok || typeof d.base64 !== "string") {
          reject(new Error(d.error || "document download failed"));
          return;
        }
        const bin = atob(d.base64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        resolve(new Blob([bytes], { type: d.contentType || "application/octet-stream" }));
      };
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMsg);
        reject(new Error("document download timed out"));
      }, Math.max(timeoutMs || 0, 20000));
      window.addEventListener("message", onMsg);
      window.postMessage({ source: "aaas-widget", kind: "fetch-doc-req", id, url }, "*");
    });
  }

  // Gateway translate (IndicTrans2) — the only translation engine, and the
  // reason the portable demo bundle keeps working with no internet.
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

  // Translate one chunk via the AaaS gateway (IndicTrans2). In the extension,
  // a direct fetch the page's CSP blocks is retried through the background
  // worker; direct reachability is cached so a strict-CSP page pays at most
  // one failed probe, then goes straight to the bridge.
  // Cache-first at both the in-memory and cross-reload (IndexedDB) layers.
  //
  // null = not yet probed; true/false = last known direct reachability.
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

    // Direct fetch first. A plain <script> embed has no other path, so it
    // always tries directly and surfaces the error.
    if (_gatewayTranslateReachable !== false || !EXT_BRIDGE) {
      try {
        const out = store(
          await gatewayTranslate(text, srcLang, tgtLang, { signal, timeoutMs }),
        );
        _gatewayTranslateReachable = true;
        return out;
      } catch (err) {
        if (!EXT_BRIDGE) {
          throw err instanceof TranslateError ? err : new TranslateError(text, tgtLang, err);
        }
        if (signal && signal.aborted) throw new TranslateError(text, tgtLang, err);
        // Direct fetch blocked (page CSP) or failed — remember it so we don't
        // retry on every chunk, and use the bridge for this and later calls.
        _gatewayTranslateReachable = false;
        console.warn(
          "[AaaS] direct gateway translate failed, using extension bridge:",
          err?.message || err,
        );
      }
    }

    // Extension only: the same gateway, reached from the background worker.
    try {
      const out = await gatewayTranslateViaBridge(text, srcLang, tgtLang, timeoutMs);
      if (typeof out === "string" && out.trim()) return store(out);
      throw new Error("empty translation");
    } catch (err) {
      if (err instanceof TranslateError) throw err;
      throw new TranslateError(text, tgtLang, err);
    }
  }

  // Easy Read: rule-based simplification via the translate service's
  // /simplify route (reached through the gateway's /translate catch-all).
  // Cache-first like translateChunk, reusing the "translate" IndexedDB
  // store under a distinct key prefix so no schema bump is needed.
  // Unlike translate there is no extension-bridge retry — a failed fetch
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
  // gateway's OCR endpoint. Cache-first by URL (government documents
  // at a URL are immutable in practice), reusing the "translate"
  // IndexedDB store under an ocr§ prefix — re-reading the same notice
  // is instant instead of re-downloading + re-OCR'ing. Mock-engine
  // results are never cached so installing tesseract later isn't
  // poisoned by canned text. Throws with a readable message on any
  // failure; the caller shows it in the modal.
  async function ocrFetchAndRecognize(url, lang, { timeoutMs = 60000 } = {}) {
    // v2 prefix: responses now carry page preview images — don't serve
    // stale image-less results from before that change.
    const k = "ocr2§" + (lang || "auto") + ":" + url;
    const hit = translateCache.get(k);
    if (hit !== undefined) return hit;
    const stored = await persistentCache.get("translate", k);
    if (stored !== undefined) {
      translateCache.set(k, stored);
      return stored;
    }
    const t = withTimeout(timeoutMs);
    try {
      let blob;
      try {
        const srcResp = await fetch(url, { signal: t.signal });
        if (!srcResp.ok) {
          throw new Error(`could not fetch the document (HTTP ${srcResp.status})`);
        }
        blob = await srcResp.blob();
      } catch (err) {
        // Government sites often serve documents from a CDN on another
        // domain without CORS headers, so the page can't read them. The
        // extension's background worker can.
        if (!EXT_BRIDGE || (t.signal && t.signal.aborted)) throw err;
        console.warn("[AaaS] direct document fetch failed, using extension bridge:", err?.message || err);
        blob = await fetchDocViaBridge(url, timeoutMs);
      }
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
      const json = await response.json();
      if (json && json.engine !== "mock") {
        translateCache.set(k, json);
        persistentCache.put("translate", k, json);
      }
      return json;
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
  // Strict page CSPs (india.gov.in: `default-src 'self'`) stop <audio> from
  // playing blob: URLs, so read-aloud would be silent. Web Audio isn't
  // governed by media-src, so once a blob is refused we play through it
  // instead for the rest of the page's life.
  let _mediaBlocked = false;
  let _playCtx = null;
  function playbackCtx() {
    _playCtx = _playCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (_playCtx.state === "suspended") _playCtx.resume().catch(() => {});
    return _playCtx;
  }
  function isMediaBlockedError(err) {
    return !!err && (err.name === "NotSupportedError" || err.name === "SecurityError");
  }
  // Plays one blob via Web Audio. Resolves when it ends or handle.stop() is
  // called; handle.stop is set once playback has started.
  async function playBlobViaWebAudio(blob, handle) {
    const ctx = playbackCtx();
    const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
    if (handle.cancelled) return;
    const node = ctx.createBufferSource();
    node.buffer = buf;
    node.connect(ctx.destination);
    await new Promise((resolve) => {
      node.onended = () => resolve();
      handle.stop = () => {
        try { node.stop(); } catch {}
        resolve();
      };
      node.start();
    });
  }

  class Player {
    constructor() {
      this.audio = new Audio();
      this._web = null; // active Web Audio handle when _mediaBlocked
      this.queue = [];
      this.playing = false;
      this.stopped = false;
      this.feedDone = false;
      this._resume = null;
      // Past blobs in play order — the rewind trail for ← / ⏮. Each
      // replayPrevious() pops the cursor back one section, so repeated
      // clicks walk all the way to the beginning of the session.
      this.past = [];
      this.pastMax = 100;
      this._currentBlob = null;
      this._replayRequested = false;
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
      this.past = [];
      this._currentBlob = null;
      this._replayRequested = false;
      this._skipRequested = false;
    }
    _wake() {
      if (this._resume) {
        const r = this._resume;
        this._resume = null;
        r();
      }
    }
    _stopWeb() {
      if (!this._web) return;
      this._web.cancelled = true;
      if (this._web.stop) this._web.stop();
      if (_playCtx && _playCtx.state === "suspended") _playCtx.resume().catch(() => {});
    }
    stop() {
      this.stopped = true;
      this.feedDone = true;
      this.queue = [];
      this._stopWeb();
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
      if (this._web) {
        _playCtx && _playCtx.suspend().catch(() => {});
        return true;
      }
      try { this.audio.pause(); } catch {}
      return true;
    }
    resume() {
      if (this._web) {
        _playCtx && _playCtx.resume().catch(() => {});
        return true;
      }
      if (!this.audio.src) return false;
      try { this.audio.play(); } catch {}
      return true;
    }
    isPaused() {
      if (this._web) return this.playing && !!_playCtx && _playCtx.state === "suspended";
      return this.playing && this.audio.paused;
    }
    // Stop the current blob mid-play and advance to the next enqueued
    // blob. Does NOT empty the queue — used for → shortcut.
    skipCurrent() {
      if (!this.playing) return false;
      this._skipRequested = true;
      this._stopWeb();
      try { this.audio.pause(); } catch {}
      // The onended/onerror-style promise resolves via the audio's
      // "pause" event fallback below.
      if (this._onAdvance) this._onAdvance();
      return true;
    }
    // Step the playback cursor back one section. Pops the rewind
    // trail (so repeated presses keep going further back) and
    // re-queues the interrupted current section, restoring the
    // natural order: previous -> current -> rest.
    replayPrevious() {
      if (!this.past.length) return false;
      const prev = this.past.pop();
      if (this._currentBlob) this.queue.unshift(this._currentBlob);
      this.queue.unshift(prev);
      // The interrupted section was re-queued, not finished — drain's
      // finally must NOT append it to the rewind trail.
      this._replayRequested = true;
      this._skipRequested = true;
      this._stopWeb();
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
          this._currentBlob = blob;
          const url = URL.createObjectURL(blob);
          this._currentUrl = url;
          this.audio.src = url;
          this._skipRequested = false;
          if (this.onAdvance) {
            // The blob is passed so callers can map playback position
            // back to page elements (the reading highlight) — identity
            // survives skip and replay, unlike a counter.
            try { this.onAdvance(blob); } catch {}
          }
          try {
            let viaElement = !_mediaBlocked;
            if (viaElement) {
              try {
                await this.audio.play();
              } catch (err) {
                if (!isMediaBlockedError(err)) throw err;
                _mediaBlocked = true;
                viaElement = false;
                console.warn("[AaaS] page blocks <audio> blobs, using Web Audio");
              }
            }
            if (viaElement) {
              const failed = await new Promise((resolve) => {
                this._onAdvance = () => resolve(false);
                this.audio.onended = () => resolve(false);
                this.audio.onerror = () => resolve(true);
              });
              // A CSP block usually surfaces here, as a load error with
              // MEDIA_ERR_SRC_NOT_SUPPORTED, rather than as a play() rejection.
              if (failed && !this._skipRequested && !this.stopped &&
                  this.audio.error && this.audio.error.code === 4) {
                _mediaBlocked = true;
                viaElement = false;
                console.warn("[AaaS] page blocks <audio> blobs, using Web Audio");
              }
            }
            if (!viaElement) {
              const web = (this._web = { cancelled: false, stop: null });
              await new Promise((resolve) => {
                this._onAdvance = resolve;
                playBlobViaWebAudio(blob, web).then(resolve, resolve);
              });
              if (this._web === web) this._web = null;
            }
          } finally {
            this._onAdvance = null;
            URL.revokeObjectURL(url);
            if (this._currentUrl === url) this._currentUrl = null;
            if (this._replayRequested) {
              // Rewind interrupt: this section was re-queued and will
              // play again — keeping it out of the trail is what makes
              // repeated ⏮ presses walk backward instead of
              // ping-ponging with the section they cancelled.
              this._replayRequested = false;
            } else if (!this.stopped) {
              this.past.push(blob);
              while (this.past.length > this.pastMax) this.past.shift();
            }
            if (this._currentBlob === blob) this._currentBlob = null;
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
      this._web = null;
    }
    cancel() {
      if (this._abort) {
        try { this._abort.abort(); } catch {}
      }
      this._abort = null;
      if (this._web) {
        this._web.cancelled = true;
        if (this._web.stop) this._web.stop();
        this._web = null;
      }
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
      try {
        const blob = await synthesise(spoken, lang, { signal: ac.signal });
        if (ac.signal.aborted) return;
        if (_mediaBlocked) {
          const web = (this._web = { cancelled: false, stop: null });
          await playBlobViaWebAudio(blob, web).catch(() => {});
          return;
        }
        const url = URL.createObjectURL(blob);
        this.audio.src = url;
        this.audio.onended = () => URL.revokeObjectURL(url);
        this.audio.onerror = () => {
          URL.revokeObjectURL(url);
          // CSP-blocked blob (MEDIA_ERR_SRC_NOT_SUPPORTED): replay via Web Audio.
          if (this.audio.error && this.audio.error.code === 4 && !ac.signal.aborted) {
            _mediaBlocked = true;
            const web = (this._web = { cancelled: false, stop: null });
            playBlobViaWebAudio(blob, web).catch(() => {});
          }
        };
        await this.audio.play().catch(async (e) => {
          if (isMediaBlockedError(e)) {
            _mediaBlocked = true;
            URL.revokeObjectURL(url);
            const web = (this._web = { cancelled: false, stop: null });
            await playBlobViaWebAudio(blob, web).catch(() => {});
            return;
          }
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
      font-family: 'OpenDyslexic';
      font-style: normal;
      font-weight: 400;
      font-display: swap;
      src: url(data:font/woff;base64,${OPENDYSLEXIC_WOFF_BASE64}) format('woff');
      unicode-range: ${LATIN_UNICODE_RANGE};
    }
    @font-face {
      font-family: 'OpenDyslexic';
      font-style: normal;
      font-weight: 700;
      font-display: swap;
      src: url(data:font/woff;base64,${OPENDYSLEXIC_BOLD_WOFF_BASE64}) format('woff');
      unicode-range: ${LATIN_UNICODE_RANGE};
    }
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
    html[data-aaas-dyslexia="true"] body *:not([data-aaas-widget]) {
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
    html[data-aaas-dyslexia="true"][data-aaas-dyslexia-latin="true"] body *:not([data-aaas-widget]) {
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
    /* The widget host <div> is excluded from the body * rules above
       via :not([data-aaas-widget]) — font/line-height/word-spacing are
       INHERITED properties, so styling the host would leak through the
       shadow boundary and reflow the panel (labels wrapped, sections
       grew). Page selectors can't reach the shadow content itself. */
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

  /* ---------- reading highlight ----------
   * While read-aloud speaks, the block being spoken gets an amber
   * outline and the page scrolls to keep it in view — so a listener
   * always knows WHERE on the page the voice is. Injected into the
   * host page (outside the shadow root) like the other host styles.
   */
  let _readingHlEl = null;

  function highlightReadingElement(el) {
    if (el === _readingHlEl) return;
    if (_readingHlEl) {
      try { _readingHlEl.removeAttribute("data-aaas-reading"); } catch {}
      _readingHlEl = null;
    }
    if (!el || !el.isConnected || el === document.body) return;
    if (!document.getElementById("__aaas_readhl__")) {
      const st = document.createElement("style");
      st.id = "__aaas_readhl__";
      st.textContent =
        "[data-aaas-reading] {" +
        " background: rgba(255, 207, 51, 0.24) !important;" +
        " outline: 2px solid rgba(255, 207, 51, 0.75) !important;" +
        " outline-offset: 2px;" +
        " border-radius: 3px;" +
        " scroll-margin: 130px;" +
        "}";
      (document.head || document.documentElement).appendChild(st);
    }
    el.setAttribute("data-aaas-reading", "");
    _readingHlEl = el;
    try {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    } catch {}
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
      <div class="whead">
        <p class="title">ସହାୟତା · Help</p>
        <select id="aaas-lang" class="lang" aria-label="Language">
          <option value="auto"${CONFIG.defaultLang === "auto" ? " selected" : ""}>Auto (${pageLang})</option>
          <option value="or"${CONFIG.defaultLang === "or" ? " selected" : ""}>ଓଡ଼ିଆ</option>
          <option value="hi"${CONFIG.defaultLang === "hi" ? " selected" : ""}>हिन्दी</option>
          <option value="en"${CONFIG.defaultLang === "en" ? " selected" : ""}>English</option>
        </select>
      </div>

      <div class="agrid">
        <div class="read-row">
          <button class="action read" type="button">
            <span class="ic" aria-hidden="true">🔊</span>
            <span class="or" lang="or">ପଢ଼ି ଶୁଣାଅ</span>
            <span class="en">Read aloud</span>
          </button>
          <button class="pause" type="button" aria-label="Pause or resume" title="Pause (Space)">⏸</button>
        </div>

        <div class="tile-wrap translate-wrap">
          <button class="action translate" type="button">
            <span class="ic" aria-hidden="true">🌐</span>
            <span class="or" lang="or">ଅନୁବାଦ</span>
            <span class="en translate-label">Translate</span>
          </button>
          <button class="undo undo-translate" type="button" aria-label="Undo translation — show the original text" title="Undo translation">↺</button>
        </div>

        <div class="tile-wrap easyread-wrap">
          <button class="action easyread" type="button">
            <span class="ic" aria-hidden="true">📖</span>
            <span class="or" lang="or">ସହଜ ପଢ଼ା</span>
            <span class="en easyread-label">Easy Read</span>
          </button>
          <button class="undo undo-easyread" type="button" aria-label="Undo Easy Read" title="Undo Easy Read">↺</button>
        </div>

        <button class="action ocr" type="button">
          <span class="ic" aria-hidden="true">📄</span>
          <span class="or" lang="or">ଦଲିଲ ପଢ଼</span>
          <span class="en">Read document</span>
        </button>

        <button class="action mic" type="button">
          <span class="ic" aria-hidden="true">🎙️</span>
          <span class="or" lang="or">କହି ଲେଖ</span>
          <span class="en">Speak to fill</span>
        </button>

        <button class="action voice" type="button">
          <span class="ic" aria-hidden="true">🧭</span>
          <span class="or" lang="or">କହି ଚଲାଅ</span>
          <span class="en">Voice command</span>
        </button>
      </div>

      <div class="comfort">
        <button class="comfort-head" type="button" aria-expanded="false">
          <span aria-hidden="true">⚙️</span>
          <span><span lang="or">ପଢ଼ିବା ଆରାମ</span> · Reading comfort</span>
          <span class="chev" aria-hidden="true">▾</span>
        </button>
        <div class="comfort-body">
          <label class="toggle">
            <input type="checkbox" id="aaas-dyslexia" />
            <span class="toggle-text"><span lang="or">ଆରାମ ଅକ୍ଷର</span> · Comfortable letters</span>
            <span class="toggle-hint">Dyslexia-friendly font and spacing</span>
          </label>

          <label class="toggle">
            <input type="checkbox" id="aaas-ruler" />
            <span class="toggle-text"><span lang="or">ପଢ଼ା ରେଖା</span> · Reading ruler</span>
            <span class="toggle-hint">Focus band that follows your pointer</span>
          </label>

          <label class="toggle">
            <input type="checkbox" id="aaas-hover" />
            <span class="toggle-text"><span lang="or">ଛୁଇଁଲେ କୁହେ</span> · Hover to speak</span>
            <span class="toggle-hint">Speaks what you point at — or select</span>
          </label>

          <button class="shortcuts-link" type="button">⌨️ Keyboard shortcuts</button>
        </div>
      </div>

      <div class="transcript" role="status" aria-live="polite"></div>
      <div class="voice-choices"></div>
      <div class="status" role="status" aria-live="polite">Ready</div>
      <div class="meta"></div>

      <div class="playctl">
        <button class="skipback" type="button" aria-label="Replay previous section" title="Replay previous (←)">⏮</button>
        <button class="skipfwd" type="button" aria-label="Skip to next section" title="Skip (→)">⏭</button>
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

    // Reading-comfort section: collapsed by default so first-time
    // users see six actions, not nine controls. Opens automatically
    // if any comfort setting is already on from a previous visit.
    const comfortBox = panel.querySelector(".comfort");
    const comfortHead = panel.querySelector(".comfort-head");
    comfortHead.addEventListener("click", () => {
      const open = comfortBox.classList.toggle("open");
      comfortHead.setAttribute("aria-expanded", open ? "true" : "false");
    });
    if (dyslexiaToggle.checked || rulerToggle.checked || hoverToggle.checked) {
      comfortBox.classList.add("open");
      comfortHead.setAttribute("aria-expanded", "true");
    }

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
      panel.setAttribute("data-reading", on ? "true" : "false");
      readBtn.classList.toggle("stop", on);
      readBtn.querySelector("span:last-child").textContent = on ? "Stop" : "Read aloud";
      pauseBtn.textContent = "⏸";
      pauseBtn.title = "Pause (Space)";
      if (label !== undefined) setStatus(label, on ? "ok" : "");
    }

    panel.querySelector(".skipfwd").addEventListener("click", () => {
      if (isReading) player.skipCurrent();
    });
    panel.querySelector(".skipback").addEventListener("click", () => {
      if (isReading) player.replayPrevious();
    });

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
        highlightReadingElement(null);
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
            element: atom.element || null,
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
              element: unit.element,
            });
            continue;
          }
          if (looksLikeTargetScript(unit.text, tgt)) {
            translated.push({
              text: unit.prefix + unit.text,
              lang: tgt,
              role: unit.role,
              element: unit.element,
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
                element: unit.element,
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
            synthesized.push({ blob, text: item.text, lang: item.lang, element: item.element });
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
      // judges see motion even on cold chunks, and the blob→element map
      // drives the on-page reading highlight (WeakMap keyed by blob
      // identity, so skip → and replay ← stay correctly aligned).
      let played = 0;
      const blobElements = new WeakMap();
      player.onAdvance = (blob) => {
        played += 1;
        if (!stopRequested) {
          setStatus(`Playing ${played}/${units.length}…`, "ok");
          highlightReadingElement(blob ? blobElements.get(blob) || null : null);
        }
      };
      const runPlay = async () => {
        const drainPromise = player.drain();
        while (true) {
          if (stopRequested || abortSignal.aborted) break;
          const item = await synthesized.next();
          if (!item) break;
          if (item.element) blobElements.set(item.blob, item.element);
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
        highlightReadingElement(null);
        setReadingUI(false);
      }
    }

    readBtn.addEventListener("click", startReadPage);

    // In-place full-page visual translation. Walks the DOM for text nodes,
    // translates each through translateChunk (the gateway, via the
    // background worker on strict-CSP pages), and replaces node values in place
    // so the user watches the page flip to Odia (or the picker's choice)
    // without a new tab or URL change. Source is the detected page language;
    // we cap concurrency and progress-report as each batch lands.
    const translateBtn = panel.querySelector(".translate");
    const translateLabel = translateBtn.querySelector(".translate-label");
    const LANG_DISPLAY = { or: "Odia", hi: "Hindi", en: "English" };
    const HAS_SCRIPT_CHAR = /[A-Za-zऀ-ॿ଀-୿]/;
    const HAS_WORD = /[A-Za-zऀ-ॿ଀-୿]{2}/;
    const SCRIPT_CHARS = { or: /[଀-୿]/g, hi: /[ऀ-ॿ]/g, en: /[A-Za-z]/g };
    function scriptCount(text, lang) {
      const re = SCRIPT_CHARS[lang];
      return re ? (text.match(re) || []).length : 0;
    }
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
        tgt === "en" ? "Translate" : `Translate → ${LANG_DISPLAY[tgt] || tgt}`;
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
            // UI glyph labels like "A-", "A+", "×" have no real word in
            // them; the translator turns them into nonsense ("ଏ. ଆଇ.").
            if (!HAS_WORD.test(v)) return NodeFilter.FILTER_REJECT;
            // Honour the standard opt-outs sites already use for Google
            // Translate — but only on page parts. Gov portals (Jajpur) put
            // translate="no" on <html> just to silence Chrome's own
            // translate bar; the reader chose us, so that one doesn't count.
            const optOut = p.closest('[translate="no"], .notranslate');
            if (
              optOut &&
              optOut !== document.documentElement &&
              optOut !== document.body
            ) {
              return NodeFilter.FILTER_REJECT;
            }
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
      // The model trims its output, but the spaces around a text node are
      // what separate it from the next link or bold word — keep them, or
      // "Konark Sun Temple is a" comes back as "...ମନ୍ଦିରଏହା".
      const lead = text.match(/^\s*/)[0];
      const trail = text.match(/\s*$/)[0];
      const core = text.trim();
      if (!core) return text;
      const out = await translateChunk(core, pageLang, tgt, { timeoutMs: 20000 });
      return out ? lead + out.trim() + trail : out;
    }

    /* ----- Undo for the in-place rewrites -----
     * Translate and Easy Read both mutate the same text nodes, so undo
     * is a LAYER STACK: each action snapshots node values before
     * touching them. Undoing a layer restores from the top down to
     * that layer (unwinding anything stacked on top) and rewinds
     * pageLang / easyReadDone to what they were before it ran — so
     * "undo translate" after translate→EasyRead restores the true
     * original, while "undo Easy Read" alone returns to the translated
     * page.
     */
    const undoLayers = []; // {kind, values: Map(node→text), prevPageLang, prevEasyReadDone}
    const translateWrap = panel.querySelector(".translate-wrap");
    const easyreadWrap = panel.querySelector(".easyread-wrap");

    function snapshotNodes(nodes) {
      const m = new Map();
      for (const node of nodes) m.set(node, node.nodeValue);
      return m;
    }

    function refreshUndoUI() {
      translateWrap.setAttribute(
        "data-undoable",
        undoLayers.some((l) => l.kind === "translate") ? "true" : "false",
      );
      easyreadWrap.setAttribute(
        "data-undoable",
        undoLayers.some((l) => l.kind === "easyread") ? "true" : "false",
      );
    }

    function undoRewrite(kind) {
      if (translateInFlight || easyReadInFlight) return;
      const idx = undoLayers.map((l) => l.kind).lastIndexOf(kind);
      if (idx === -1) return;
      // Restore top-down: each layer holds the values from before ITS
      // action, so finishing with layer idx leaves its (earliest) text.
      for (let i = undoLayers.length - 1; i >= idx; i--) {
        for (const [node, text] of undoLayers[i].values) {
          if (node.isConnected) node.nodeValue = text;
        }
      }
      const layer = undoLayers[idx];
      pageLang = layer.prevPageLang;
      easyReadDone = layer.prevEasyReadDone;
      undoLayers.length = idx;
      refreshUndoUI();
      updateTranslateLabel();
      setStatus(
        kind === "translate" ? "Original text restored" : "Easy Read undone",
        "ok",
      );
    }
    panel.querySelector(".undo-translate").addEventListener("click", () => undoRewrite("translate"));
    panel.querySelector(".undo-easyread").addEventListener("click", () => undoRewrite("easyread"));

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
        const hint = undoLayers.length ? " — ↺ on the tile restores the original" : "";
        setStatus(`Page is already in ${LANG_DISPLAY[tgt] || tgt}${hint}`, "notice");
        return;
      }
      translateInFlight = true;
      translateBtn.disabled = true;
      let layer = null;
      try {
        // Bilingual pages already carry target-language lines (an Odia
        // subtitle under an English heading). Feeding those through an
        // en→or model returns dots and dashes, so leave them as they are.
        const nodes = collectTranslatableNodes().filter(
          (n) => scriptCount(n.nodeValue, tgt) <= scriptCount(n.nodeValue, pageLang),
        );
        if (!nodes.length) {
          statusEl.textContent = "Nothing to translate on this page";
          return;
        }
        layer = {
          kind: "translate",
          values: snapshotNodes(nodes),
          prevPageLang: pageLang,
          prevEasyReadDone: easyReadDone,
        };
        undoLayers.push(layer);
        statusEl.textContent =
          `Translating 0 / ${nodes.length} → ${LANG_DISPLAY[tgt] || tgt}…`;
        const BATCH = 16; // the server batches concurrent translations
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
          `Page translated → ${LANG_DISPLAY[tgt] || tgt} (↺ on the tile restores the original)`;
        // The DOM is now in the target language; let read-aloud,
        // Easy Read, voice nav and repeat clicks act on that fact.
        // Guarded so a total failure (gateway down, every node left
        // untouched) doesn't mislabel an untranslated page.
        if (changed) {
          pageLang = tgt;
        } else if (layer) {
          // Nothing was rewritten — drop the useless undo layer.
          undoLayers.pop();
          layer = null;
        }
      } finally {
        translateBtn.disabled = false;
        translateInFlight = false;
        refreshUndoUI();
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
    async function simplifyOne(text, lang) {
      if (text.length <= 1800) return simplifyChunk(text, lang);
      const pieces = splitIntoSentences(text, 1500);
      const out = [];
      for (const piece of pieces) {
        out.push(await simplifyChunk(piece, lang));
      }
      return out.join(" ");
    }

    async function easyReadPageInPlace() {
      if (easyReadInFlight || translateInFlight) return;
      if (easyReadDone) {
        setStatus("Page is already in Easy Read — ↺ on the tile undoes it", "notice");
        return;
      }
      easyReadInFlight = true;
      easyreadBtn.disabled = true;
      // Easy Read simplifies in the page's CURRENT language — an
      // English page stays English, a translated-to-Odia page gets
      // the Odia rules. Changing language is the Translate tile's
      // job; the two compose (translate first, then Easy Read).
      const lang = pageLang;
      let layer = null;
      try {
        const nodes = collectTranslatableNodes();
        if (!nodes.length) {
          setStatus("Nothing to simplify on this page");
          return;
        }
        layer = {
          kind: "easyread",
          values: snapshotNodes(nodes),
          prevPageLang: pageLang,
          prevEasyReadDone: easyReadDone,
        };
        undoLayers.push(layer);
        setStatus(`Simplifying 0 / ${nodes.length}…`);
        const BATCH = 5;
        let done = 0;
        let succeeded = 0;
        for (let i = 0; i < nodes.length; i += BATCH) {
          const slice = nodes.slice(i, i + BATCH);
          await Promise.all(
            slice.map(async (node) => {
              try {
                const out = await simplifyOne(node.nodeValue, lang);
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
            undoLayers.pop(); // nothing was rewritten
            layer = null;
            setStatus("Easy Read unavailable — check that services are running", "error");
            return;
          }
          done += slice.length;
          setStatus(`Simplifying ${done} / ${nodes.length}…`);
        }
        easyReadDone = true;
        setStatus("Page in Easy Read (↺ on the tile undoes it)", "ok");
      } finally {
        easyreadBtn.disabled = false;
        easyReadInFlight = false;
        refreshUndoUI();
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

    // `selectionchange` fires many times per drag; debounce so we only
    // speak once the selection settles. With "Hover to speak" on, the
    // WHOLE selection is read — sentence by sentence through the
    // announcer, translated like everything else — so a citizen can
    // select a paragraph of a notice and hear all of it. The sequence
    // stops when the user selects something new, clicks away
    // (collapsing the selection), hovers another element, presses Esc,
    // or starts the page reader.
    const SELECTION_MAX_CHARS = 2000;
    let selectionReadToken = 0;

    const selectionHandler = debounce(async () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) {
        // Clicking away clears the selection — stop a running readout.
        selectionReadToken++;
        return;
      }
      if (!hoverToggle.checked) return;
      if (isReading) return; // never talk over the page reader
      const text = sel.toString().trim();
      if (!text) return;
      // Skip selections that start inside the widget itself.
      const anchor = sel.anchorNode instanceof Element
        ? sel.anchorNode
        : sel.anchorNode?.parentElement;
      if (inWidget(anchor)) return;
      // Cap so Ctrl+A on a huge page can't DoS translate + TTS.
      const capped = text.slice(0, SELECTION_MAX_CHARS);
      const chunks = splitIntoSentences(capped, CONFIG.maxChars);
      const token = ++selectionReadToken;
      for (const chunk of chunks) {
        if (token !== selectionReadToken || !hoverToggle.checked || isReading) return;
        await announcer.announce({ text: chunk, prefix: "", role: "selection", element: null });
        if (token !== selectionReadToken) return;
        // Wait for this chunk's audio to finish before the next one.
        // cancel() pauses the element, so an external interrupt also
        // unblocks the wait.
        const claimed = announcer._abort;
        await new Promise((resolve) => {
          const a = announcer.audio;
          if (!a.src || a.ended) { resolve(); return; }
          const done = () => {
            a.removeEventListener("ended", done);
            a.removeEventListener("pause", done);
            a.removeEventListener("error", done);
            resolve();
          };
          a.addEventListener("ended", done);
          a.addEventListener("pause", done);
          a.addEventListener("error", done);
        });
        // Another announcement (hover, focus, Esc, page read) claimed
        // the voice mid-sequence — don't fight it for the next chunk.
        if (!claimed || claimed.signal.aborted) return;
      }
    }, 500);

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
        if (guidedActive) {
          cancelGuided("Guided fill stopped.");
          e.preventDefault();
          return;
        }
        if (shortcutsOverlay.getAttribute("data-open") === "true") {
          toggleShortcuts(false);
          e.preventDefault();
          return;
        }
        const docOv = shadow.querySelector(".docmodal");
        if (docOv && docOv.getAttribute("data-open") === "true") {
          docOv.querySelector(".docmodal-close").click();
          e.preventDefault();
          return;
        }
        if (isReading) {
          stopRequested = true;
          if (currentAbort) { try { currentAbort.abort(); } catch {} }
          player.stop();
          highlightReadingElement(null);
          setReadingUI(false, "Stopped.");
          e.preventDefault();
          return;
        }
        announcer.cancel();
        clearVoiceChoices();
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
      micBtn.querySelector("span:last-child").textContent = "Speak to fill";
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

        // Transliterate, never translate: form values must be the SAME
        // words in Latin letters ("ପୂର୍ଣ୍ଣଚନ୍ଦ୍ର" -> "Purnnachandra"),
        // because meaning-translation turns names into nonsense ("full
        // moon") and raw Odia is rejected by most real forms.
        let fillText = toWesternDigits(result.text || "");
        if (result.text && src === "or") {
          fillText = romanizeOdia(result.text);
        }
        if (fillText && lastEditableEl && lastEditableEl.tagName === "INPUT") {
          fillText = normalizeSpokenValue(
            (lastEditableEl.type || "text").toLowerCase(),
            fillText,
          );
        }

        // Auto-fill the last editable field the user touched. Cooperating
        // demo sites also get the CustomEvent below for custom handling.
        let filled = false;
        if (fillText && lastEditableEl) {
          filled = writeToField(lastEditableEl, fillText);
        }
        const arrow = src === "or" ? " → romanized" : "";
        if (filled) {
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
              // kept for event-shape compat; the fill path romanizes
              // instead of translating, so this can no longer fail
              translateFailed: false,
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

    /* ----- Guided voice form fill -----
     * With no field focused, "Speak to fill" walks every field on the
     * page: highlight + speak the label, listen, clean the answer to
     * the field type, write it, advance. Esc or tapping the tile again
     * cancels. It NEVER submits the form. The "aaas-guided-input"
     * CustomEvent feeds an answer without a mic (testing, kiosks with
     * keyboards, rehearsals).
     */
    let guidedActive = false;
    let guidedResolve = null;
    let guidedPendingInput = null;

    document.addEventListener("aaas-guided-input", (ev) => {
      const text = ((ev.detail && ev.detail.text) || "").toString();
      if (guidedResolve) {
        const r = guidedResolve;
        guidedResolve = null;
        try { if (recorder.isRecording()) recorder.stop().catch(() => {}); } catch {}
        r(text);
      } else if (guidedActive) {
        // Arrived while the label prompt was still speaking — hold it
        // for the capture that's about to start.
        guidedPendingInput = text;
      }
    });

    // One spoken answer: resolves with the transcript from the mic
    // (auto-stop or tile tap) or from an injected event; "" on failure.
    function captureVoiceText() {
      if (guidedPendingInput !== null) {
        const t = guidedPendingInput;
        guidedPendingInput = null;
        return Promise.resolve(t);
      }
      return new Promise((resolve) => {
        let settled = false;
        const finish = (v) => {
          if (settled) return;
          settled = true;
          if (guidedResolve) guidedResolve = null;
          resolve(v);
        };
        guidedResolve = finish;
        // Safety: a stray recording from an interrupted capture must
        // not collide with this one.
        try { if (recorder.isRecording()) recorder.stop().catch(() => {}); } catch {}
        const handleBlob = async (blob) => {
          try {
            const r = await transcribe(blob, resolvedLang());
            transcriptEl.textContent = r.text || "";
            finish(r.text || "");
          } catch (err) {
            console.warn("[AaaS] guided transcribe failed:", err);
            finish("");
          }
        };
        recorder.start({ onAutoStop: handleBlob }).catch(() => {
          // Mic unavailable — stay open for injected input only.
          setStatus("Mic unavailable — waiting for typed input", "error");
        });
        guidedStopBlob = handleBlob;
      });
    }
    let guidedStopBlob = null;

    // Speak a short prompt and wait for the audio to finish so the
    // TTS voice doesn't bleed into the recording.
    async function speakPrompt(text) {
      try {
        await announcer.announce({ text, prefix: "", role: "prompt", element: null });
        await new Promise((resolve) => {
          const a = announcer.audio;
          if (!a.src || a.ended) { resolve(); return; }
          const done = () => {
            a.removeEventListener("ended", done);
            a.removeEventListener("pause", done);
            a.removeEventListener("error", done);
            resolve();
          };
          a.addEventListener("ended", done);
          a.addEventListener("pause", done);
          a.addEventListener("error", done);
        });
      } catch {}
    }

    function cancelGuided(message) {
      guidedActive = false;
      guidedPendingInput = null;
      if (guidedResolve) {
        const r = guidedResolve;
        guidedResolve = null;
        r("");
      }
      try { if (recorder.isRecording()) recorder.stop().catch(() => {}); } catch {}
      micBtn.classList.remove("recording");
      micBtn.querySelector("span:last-child").textContent = "Speak to fill";
      if (message) setStatus(message);
    }

    // A short high tone that means "speak NOW" — the audible cue
    // between the label prompt ending and the mic opening.
    let _beepCtx = null;
    function readyBeep() {
      try {
        _beepCtx = _beepCtx || new (window.AudioContext || window.webkitAudioContext)();
        const osc = _beepCtx.createOscillator();
        const gain = _beepCtx.createGain();
        osc.frequency.value = 880;
        gain.gain.value = 0.08;
        osc.connect(gain);
        gain.connect(_beepCtx.destination);
        osc.start();
        osc.stop(_beepCtx.currentTime + 0.15);
      } catch {}
    }

    async function guidedFormFill(fields) {
      if (isReading) {
        setStatus("Stop the page reader first (Esc)", "error");
        return;
      }
      guidedActive = true;
      micBtn.classList.add("recording");
      micBtn.querySelector("span:last-child").textContent = "Guided fill — Esc stops";
      ensureVoiceTargetStyle();
      // Only ask for EMPTY fields — re-running the guided fill after a
      // miss asks just for the blanks instead of everything again.
      const empty = fields.filter((f) => !(f.value || "").trim());
      const prefilled = fields.length - empty.length;
      const total = empty.length;
      let filled = 0;
      let lastForm = null;
      try {
        if (!total) {
          setStatus("Every field already has an answer — check them and press Submit", "notice");
          return;
        }
        for (let idx = 0; idx < empty.length; idx++) {
          const field = empty[idx];
          if (!guidedActive) return;
          lastForm = field.form || lastForm;
          const label = getAccessibleName(field) || field.name || "this field";
          const type = field.tagName === "INPUT" ? (field.type || "text").toLowerCase() : "textarea";
          try { field.scrollIntoView({ block: "center", behavior: "smooth" }); } catch {}
          try { field.focus(); } catch {}
          // Highlight stays for the field's WHOLE turn (the shared
          // helper auto-clears after 1.6s — too short for a listen).
          field.setAttribute("data-aaas-voice-target", "");
          let value = "";
          // Numbers get one automatic retry — mishearing a phone digit
          // is common and re-asking beats leaving a blank.
          const attempts = type === "tel" || type === "number" ? 2 : 1;
          for (let attempt = 0; attempt < attempts; attempt++) {
            if (!guidedActive) return;
            setStatus(`🎙️ ${label} (${idx + 1}/${total})`);
            await speakPrompt(attempt === 0 ? label : `${label}. ପୁଣି କୁହନ୍ତୁ`);
            if (!guidedActive) return;
            readyBeep();
            setStatus(`👂 ${label} (${idx + 1}/${total}) — listening…`);
            const raw = await captureVoiceText();
            if (!guidedActive) return;
            if (!raw.trim()) continue;
            if (type === "tel" || type === "number") {
              // Parse the RAW transcript (spoken-number words live
              // there); romanization would only blur them.
              value = normalizeSpokenValue(type, raw);
              if (value) break;
            } else {
              // Transliterate, never translate: same words, Latin
              // letters — meaning-translation turns names into
              // nonsense and raw Odia is rejected by most forms.
              value = dominantScript(raw) === "or" ? romanizeOdia(raw) : raw;
              value = normalizeSpokenValue(type, value);
              // Datalist snap: when the field offers options
              // (<input list> — department/district pickers), land the
              // spoken answer on the best-matching option so the form
              // gets "Cardiology", not a romanized "Kardiolaji".
              if (value && field.list && field.list.options) {
                let bestOpt = null;
                let bestScore = 0.55;
                for (const opt of Array.from(field.list.options)) {
                  const sc = Math.max(
                    scoreVoiceTarget(value, opt.value),
                    scoreVoiceTarget(raw, opt.value),
                  );
                  if (sc > bestScore) {
                    bestOpt = opt.value;
                    bestScore = sc;
                  }
                }
                if (bestOpt) value = bestOpt;
              }
              break;
            }
          }
          field.removeAttribute("data-aaas-voice-target");
          if (!value) {
            setStatus(`Left empty: ${label} — tap Speak to fill again to retry the blanks`, "error");
            continue;
          }
          if (writeToField(field, value)) {
            filled++;
            setStatus(`✓ ${label}: ${value}`, "ok");
            await new Promise((r) => setTimeout(r, 450)); // let the ✓ register
          }
        }
        const note = prefilled ? ` · ${prefilled} already filled` : "";
        setStatus(
          `Form filled (${filled}/${total})${note} — check the answers and press Submit yourself`,
          "ok",
        );
        speakPrompt("Done. Please check the answers.");
        // Park focus on the submit control so pressing Enter submits
        // when — and only when — the USER decides.
        try {
          const submit =
            lastForm &&
            (lastForm.querySelector('button[type="submit"], input[type="submit"]') ||
              lastForm.querySelector("button"));
          if (submit) submit.focus();
        } catch {}
      } finally {
        guidedActive = false;
        document.querySelectorAll("[data-aaas-voice-target]").forEach((el) => {
          el.removeAttribute("data-aaas-voice-target");
        });
        micBtn.classList.remove("recording");
        micBtn.querySelector("span:last-child").textContent = "Speak to fill";
      }
    }

    // Snapshot what's focused BEFORE the tile steals focus: this — not
    // a stale "last focused field ever" — decides single-field vs
    // guided mode. (The old check made guided mode unreachable once
    // any field had ever been focused on the page.)
    let micFieldWasFocused = false;
    micBtn.addEventListener("pointerdown", () => {
      micFieldWasFocused = isEditableTarget(document.activeElement);
    });

    micBtn.addEventListener("click", async () => {
      if (guidedActive) {
        // Second tap during guided fill: if we're recording an answer,
        // finish it now; otherwise cancel the walk.
        if (recorder.isRecording() && guidedStopBlob) {
          try {
            const blob = await recorder.stop();
            guidedStopBlob(blob);
          } catch {}
          return;
        }
        cancelGuided("Guided fill stopped.");
        return;
      }
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
      // No field focused right now -> guided mode over the page's
      // form fields. (Alt+M keeps the field focused through the
      // keydown, so the live activeElement check covers keyboard use;
      // pointerdown covers mouse/touch before focus moves.)
      const fieldNow = micFieldWasFocused || isEditableTarget(document.activeElement);
      micFieldWasFocused = false;
      if (!fieldNow) {
        let fields = collectFormFields();
        // Pages often carry several forms (a search box, a results
        // lookup, the application). Fill the FORM the walk starts in,
        // not the whole page — a second tap continues with the next
        // form once this one has answers.
        const firstEmpty = fields.find((f) => !(f.value || "").trim()) || fields[0];
        if (firstEmpty && firstEmpty.form) {
          fields = fields.filter((f) => f.form === firstEmpty.form);
        }
        if (fields.length >= 2) {
          guidedFormFill(fields);
          return;
        }
      }
      transcriptEl.textContent = "";
      try {
        await recorder.start({ onAutoStop: handleRecorded });
        micBtn.classList.add("recording");
        micBtn.querySelector("span:last-child").textContent = "Recording… tap to stop";
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

    function ensureVoiceTargetStyle() {
      if (document.getElementById("__aaas_voicenav__")) return;
      const st = document.createElement("style");
      st.id = "__aaas_voicenav__";
      st.textContent =
        "[data-aaas-voice-target] { outline: 3px solid #ffcf33 !important; outline-offset: 2px !important; }";
      (document.head || document.documentElement).appendChild(st);
    }

    function highlightVoiceTarget(el) {
      ensureVoiceTargetStyle();
      el.setAttribute("data-aaas-voice-target", "");
      setTimeout(() => el.removeAttribute("data-aaas-voice-target"), 1600);
    }

    const voiceChoicesEl = panel.querySelector(".voice-choices");

    function clearVoiceChoices() {
      voiceChoicesEl.textContent = "";
    }

    function actOnVoiceTarget(best) {
      try { best.element.scrollIntoView({ block: "center", behavior: "smooth" }); } catch {}
      try { best.element.focus(); } catch {}
      highlightVoiceTarget(best.element);
      setStatus(`Opening "${best.name}"…`, "ok");
      // A visible beat between highlight and click so the user sees
      // what was chosen before any navigation happens.
      setTimeout(() => { try { best.element.click(); } catch {} }, 600);
    }

    function showVoiceChoices(ranked) {
      clearVoiceChoices();
      const hint = document.createElement("span");
      hint.className = "vc-hint";
      hint.textContent = "ଗୋଟିଏ ବାଛନ୍ତୁ · Not sure — tap the one you meant:";
      voiceChoicesEl.append(hint);
      // Same name twice (header + footer copies, ticker truncations)
      // or the same destination worded differently would render as
      // near-identical buttons — offer each intent once.
      const kept = [];
      for (const r of ranked) {
        if (!kept.some((k) => sameVoiceTarget(k, r))) kept.push(r);
      }
      kept.slice(0, 3).forEach((r) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = r.name;
        b.addEventListener("click", () => {
          clearVoiceChoices();
          actOnVoiceTarget(r);
        });
        voiceChoicesEl.append(b);
      });
    }

    async function executeVoiceCommand(rawText, langHint) {
      clearVoiceChoices();
      const norm = normalizeCommandText(rawText || "");
      if (!norm) {
        setStatus("No speech detected", "error");
        return;
      }
      const lang =
        dominantScript(rawText) ||
        (langHint || "").toLowerCase().split("-")[0] ||
        "en";

      // Odia STT writes English speech phonetically in Odia script
      // ("କଣ୍ଟାକ୍ଟ" for "contact") — the romanized form is often the
      // best clue we have, for global commands and link names alike.
      const romanized = lang === "or" ? romanizeOdia(rawText) : "";

      let action = matchGlobalCommand(norm, lang);
      if (!action && romanized) action = matchGlobalCommand(romanized, "en");
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
      if (romanized && romanized !== rawText) {
        candidates.push(romanized);
        understood.push(romanized);
      }
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

      // Weak matches (junk that barely cleared the rank floor) must
      // not be offered as buttons — "Pause / Instagram" for "pension"
      // is worse than admitting no match. 0.55: short-name skeleton
      // coincidences ("Scroll" for "scholarship") land 0.45-0.52,
      // genuine fuzzy matches land 0.57+.
      const plausible = ranked.filter((r) => r.score >= 0.55);
      if (shouldActOnVoiceMatch(ranked)) {
        actOnVoiceTarget(ranked[0]);
      } else if (plausible.length) {
        // Not confident enough to click — offer the top candidates as
        // BUTTONS so the user finishes with one tap instead of
        // re-speaking into an error message.
        showVoiceChoices(plausible);
        setStatus("Not sure which one you meant — tap below", "notice");
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
      voiceBtn.querySelector("span:last-child").textContent = "Voice command";
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
        voiceBtn.querySelector("span:last-child").textContent = "Listening…";
        setStatus("Say a command or a link name…");
      } catch (err) {
        setStatus(`Mic unavailable: ${err.message}`, "error");
      }
    });

    /* ----- Document reader ("Read a document to me") -----
     * Built for non-technical users: the widget FINDS the documents
     * (document-sized images + PDF links) instead of making the user
     * hunt. One document -> it just goes. Several -> a big centered
     * chooser (hovering a row highlights the document on the page).
     * None -> plain-language message with a point-at-it fallback.
     * All progress lives in the same big modal in friendly steps, and
     * the result is large-print text that starts reading aloud
     * automatically — that IS what the user asked for.
     */
    const ocrBtn = panel.querySelector(".ocr");

    // The modal lives on the shadow ROOT, not in the panel: the panel
    // animates with a transform, which would re-anchor position:fixed.
    const docModal = document.createElement("div");
    docModal.className = "docmodal";
    docModal.setAttribute("data-open", "false");
    docModal.setAttribute("role", "dialog");
    docModal.setAttribute("aria-label", "Read a document");
    docModal.innerHTML = `
      <div class="docmodal-box">
        <button class="docmodal-max" type="button" aria-label="Maximize" title="Maximize">⛶</button>
        <button class="docmodal-close" type="button" aria-label="Close">×</button>
        <h4 class="docmodal-title"></h4>
        <div class="docmodal-body" role="status" aria-live="polite"></div>
        <div class="docmodal-actions"></div>
      </div>
    `;
    shadow.append(docModal);
    const docTitle = docModal.querySelector(".docmodal-title");
    const docBody = docModal.querySelector(".docmodal-body");
    const docActions = docModal.querySelector(".docmodal-actions");
    const docCloseBtn = docModal.querySelector(".docmodal-close");

    let docReading = false;
    let docResultText = "";

    function stopDocReading() {
      if (docReading) {
        docReading = false;
        player.stop();
      }
    }

    // Session token: closing the modal (or starting a new run)
    // invalidates every in-flight pipeline. Without this, OCR/simplify/
    // translate kept running after close and auto-started SPEAKING into
    // the closed modal when they finished — a ghost voice that looked
    // like "the previous session resumed".
    let docSession = 0;

    function closeDocModal() {
      docSession++;
      stopDocReading();
      docModal.setAttribute("data-open", "false");
      document.querySelectorAll("[data-aaas-ocr-hover]").forEach((el) => {
        el.removeAttribute("data-aaas-ocr-hover");
      });
      ocrBtn.disabled = false; // a cancelled run must not leave the tile stuck
      try { ocrBtn.focus(); } catch {}
    }
    docCloseBtn.addEventListener("click", closeDocModal);
    docModal.addEventListener("click", (ev) => {
      if (ev.target === docModal) closeDocModal();
    });

    // Maximize / restore. The choice sticks for the session so a user
    // who prefers the big view isn't re-shrunk on every document.
    const docMaxBtn = docModal.querySelector(".docmodal-max");
    docMaxBtn.addEventListener("click", () => {
      const box = docModal.querySelector(".docmodal-box");
      const on = box.classList.toggle("maximized");
      docMaxBtn.textContent = on ? "🗗" : "⛶";
      docMaxBtn.title = on ? "Restore smaller view" : "Maximize";
      docMaxBtn.setAttribute("aria-label", docMaxBtn.title);
    });

    function openDocModal(title) {
      docTitle.textContent = title;
      docBody.textContent = "";
      docActions.textContent = "";
      docModal.setAttribute("data-open", "true");
      // Move focus INTO the dialog so keyboard and screen-reader users
      // land where the action is; callers that render rows/buttons
      // afterwards re-focus their first control.
      setTimeout(() => {
        if (docModal.getAttribute("data-open") !== "true") return;
        const target =
          docModal.querySelector(".doc-row, .doc-primary, button:not(.docmodal-close):not(.docmodal-max)") ||
          docModal.querySelector(".docmodal-close");
        try { target.focus(); } catch {}
      }, 150);
    }

    function docButton(label, className, onClick) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = className;
      b.textContent = label;
      b.addEventListener("click", onClick);
      docActions.append(b);
      return b;
    }

    function showDocProgress(step, substep) {
      docBody.innerHTML =
        '<div class="doc-progress"><div class="doc-spin" aria-hidden="true"></div>' +
        '<div class="doc-step"></div><div class="doc-substep"></div></div>';
      docBody.querySelector(".doc-step").textContent = step;
      docBody.querySelector(".doc-substep").textContent = substep || "";
      docActions.textContent = "";
      docButton("Cancel", "doc-secondary", closeDocModal);
    }

    function updateDocProgress(step, substep) {
      const stepEl = docBody.querySelector(".doc-step");
      if (!stepEl) return showDocProgress(step, substep);
      stepEl.textContent = step;
      docBody.querySelector(".doc-substep").textContent = substep || "";
    }

    function showDocError(message) {
      docTitle.textContent = "Sorry, that didn't work";
      docBody.innerHTML = '<div class="doc-error"></div>';
      docBody.querySelector(".doc-error").textContent = message;
      docActions.textContent = "";
      docButton("Try another document", "doc-primary", openDocFlow);
      docButton("Close", "doc-secondary", closeDocModal);
    }

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
    function ensureOcrHighlightStyle() {
      if (document.getElementById("__aaas_ocrpick__")) return;
      const st = document.createElement("style");
      st.id = "__aaas_ocrpick__";
      st.textContent =
        "[data-aaas-ocr-hover] { outline: 3px dashed #ffcf33 !important; outline-offset: 3px !important; cursor: crosshair !important; }";
      (document.head || document.documentElement).appendChild(st);
    }

    function clearOcrHighlights() {
      document.querySelectorAll("[data-aaas-ocr-hover]").forEach((el) => {
        el.removeAttribute("data-aaas-ocr-hover");
      });
    }

    // Entry point: find the documents FOR the user and ALWAYS ask
    // which one to read — even when there's only one. (An earlier
    // one-candidate fast path jumped straight to the cached result
    // with auto-play, which read as "it reopened my previous
    // session". Predictability beats saving one tap.)
    function openDocFlow() {
      docSession++; // abandon anything from a previous open
      stopDocReading();
      const candidates = collectOcrCandidates();
      if (!candidates.length) {
        openDocModal("Read a document to me");
        docBody.innerHTML = '<div class="doc-error"></div>';
        docBody.querySelector(".doc-error").textContent =
          "I couldn't find any documents on this page. " +
          "If you can see one, I can read it if you point at it.";
        docButton("Let me point at it", "doc-primary", () => {
          closeDocModal();
          enterOcrPick();
        });
        docButton("Close", "doc-secondary", closeDocModal);
        return;
      }
      showDocChooser(candidates);
    }
    ocrBtn.addEventListener("click", openDocFlow);

    function showDocChooser(candidates) {
      openDocModal(
        candidates.length === 1
          ? "I found one document — tap it to hear it"
          : "Which document should I read?",
      );
      ensureOcrHighlightStyle();
      const MAX_ROWS = 20;
      candidates.slice(0, MAX_ROWS).forEach((c) => {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "doc-row";
        // A real thumbnail tells "banner 3" from "banner 2" at a glance;
        // the page already loaded the image, so it comes from cache.
        const ico = document.createElement("span");
        ico.className = "doc-ico";
        ico.setAttribute("aria-hidden", "true");
        ico.textContent = c.kind === "pdf" ? "📄" : "🖼️";
        if (c.kind === "image" && c.url) {
          const thumb = document.createElement("img");
          thumb.alt = "";
          thumb.decoding = "async";
          thumb.onload = () => ico.replaceChildren(thumb);
          thumb.src = c.url;
        }
        const name = document.createElement("span");
        name.textContent = c.name;
        const kind = document.createElement("span");
        kind.className = "doc-kind";
        kind.textContent = c.kind === "pdf" ? "PDF" : "Image";
        row.append(ico, name, kind);
        // Hovering a row shows WHICH document it is on the page.
        row.addEventListener("mouseenter", () => {
          clearOcrHighlights();
          if (c.element && c.element.isConnected) {
            c.element.setAttribute("data-aaas-ocr-hover", "");
            try { c.element.scrollIntoView({ block: "nearest", behavior: "smooth" }); } catch {}
          }
        });
        row.addEventListener("mouseleave", clearOcrHighlights);
        row.addEventListener("click", () => {
          clearOcrHighlights();
          runOcrPipeline(c);
        });
        docBody.append(row);
      });
      if (candidates.length > MAX_ROWS) {
        const more = document.createElement("div");
        more.className = "doc-error";
        more.textContent = `…and ${candidates.length - MAX_ROWS} more. If yours isn't listed, point at it on the page.`;
        docBody.append(more);
      }
      docButton("Point at it on the page", "doc-secondary", () => {
        closeDocModal();
        enterOcrPick();
      });
      docButton("Close", "doc-secondary", closeDocModal);
    }

    function friendlyDocError(err) {
      const m = (err && err.message) || "";
      if (/too large/i.test(m)) {
        return "This document is too big for me to read — the limit is 15 MB.";
      }
      if (/could not fetch|failed to fetch|networkerror/i.test(m)) {
        return "I couldn't open this document. The website may be blocking it, or it may be unavailable right now.";
      }
      if (/abort/i.test(m)) {
        return "This took too long and I gave up. Please try again.";
      }
      return "Something went wrong while reading this document. Please try again.";
    }

    async function runOcrPipeline(desc) {
      // New run claims the session; closing the modal (or another run)
      // bumps it, and every await below re-checks — an abandoned
      // pipeline finishes its network call and then vanishes silently
      // instead of filling a closed modal and speaking into it.
      const session = ++docSession;
      const live = () => session === docSession;
      ocrBtn.disabled = true;
      openDocModal("One moment…");
      showDocProgress("Reading the document…", desc.name || "");
      try {
        const result = await ocrFetchAndRecognize(desc.url, ocrLangHint(pageLang));
        if (!live()) return;
        // Keep pages SEPARATE through the pipeline so the result view
        // can pair each page's image with its text and highlight the
        // page being spoken.
        let docPages = (result.pages || [])
          .map((p) => ({ text: (p.text || "").trim(), image: p.image || null }))
          .filter((p) => p.text);
        if (!docPages.length && (result.text || "").trim()) {
          docPages = [{ text: result.text.trim(), image: null }];
        }
        if (!docPages.length) {
          showDocError("I couldn't find any readable text in this document. It may be a photo or a very poor scan.");
          return;
        }
        const srcLang = dominantScript(docPages.map((p) => p.text).join(" ")) || "en";
        const tgt = resolvedLang() || srcLang;
        // Simplify (rule-based, offline). Not fatal on failure — the
        // raw OCR text is already the accessibility win.
        try {
          updateDocProgress("Making it easier to read…", "");
          for (const p of docPages) {
            const pieces = splitIntoSentences(p.text, 1500);
            const simplified = [];
            for (const piece of pieces) {
              simplified.push(await simplifyChunk(piece, srcLang));
              if (!live()) return;
            }
            p.text = simplified.join(" ");
          }
        } catch (err) {
          if (!live()) return;
          console.warn("[AaaS] OCR simplify failed:", err);
        }
        // Short pieces: the CPU model's time grows steeply with length
        // (800-char pieces took ~20 s and hit the timeout, silently
        // leaving the English), and long inputs also garble details.
        const DOC_PIECE_CHARS = 300;
        let untranslated = 0;
        const label = LANG_DISPLAY[tgt] || tgt;
        if (tgt !== srcLang) {
          const pagePieces = docPages.map((p) => splitIntoSentences(p.text, DOC_PIECE_CHARS));
          const totalParts = pagePieces.reduce((n, pieces) => n + pieces.length, 0);
          let part = 0;
          const progress = () =>
            updateDocProgress(
              `Turning it into ${label}…`,
              totalParts > 1 ? `part ${part} of ${totalParts}` : "",
            );
          progress();
          // All pieces go out together so the server can translate them as
          // one batch. One slow or failed piece keeps its original text; the
          // rest still translate.
          const translatedPages = await Promise.all(
            pagePieces.map((pieces) =>
              Promise.all(
                pieces.map(async (piece) => {
                  let out = piece;
                  try {
                    out = stripPassthroughAnnotation(
                      await translateChunk(piece, srcLang, tgt, { timeoutMs: 45000 }),
                    );
                  } catch (err) {
                    console.warn("[AaaS] OCR translate failed:", err);
                    untranslated++;
                  }
                  part++;
                  if (live()) progress();
                  return out;
                }),
              ),
            ),
          );
          if (!live()) return;
          docPages.forEach((p, i) => {
            p.text = translatedPages[i].join(" ");
          });
        }
        if (!live()) return;
        showDocResult(docPages, result.engine === "mock", desc);
        if (untranslated) {
          const note = document.createElement("div");
          note.className = "doc-error";
          note.setAttribute("role", "status");
          note.textContent = `Some parts couldn't be turned into ${label} and are shown as written.`;
          docBody.prepend(note);
        }
      } catch (err) {
        if (!live()) return;
        console.warn("[AaaS] OCR pipeline failed:", err);
        showDocError(friendlyDocError(err));
      } finally {
        // Only the CURRENT session may re-enable the tile — a stale
        // one racing a fresh run must not flip it mid-flight.
        if (live()) ocrBtn.disabled = false;
      }
    }

    let docPagesCurrent = [];

    function showDocResult(pages, wasMock, desc) {
      docPagesCurrent = pages;
      docResultText = pages.map((p) => p.text).join("\n\n");
      docTitle.textContent = "Here's your document";
      // Preview images: PDF pages come from the server render; a
      // picked image IS its own preview.
      if (desc && desc.kind === "image" && pages.length && !pages[0].image) {
        pages[0].image = desc.url;
      }
      const hasPreview = pages.some((p) => p.image);
      docModal.querySelector(".docmodal-box").classList.toggle("with-preview", hasPreview);
      docBody.textContent = "";
      const textPane = document.createElement("div");
      textPane.className = "doc-text";
      pages.forEach((p, i) => {
        const section = document.createElement("div");
        section.className = "doc-ptext";
        section.setAttribute("data-doc-page", i);
        if (pages.length > 1) {
          const chip = document.createElement("span");
          chip.className = "doc-chip";
          chip.textContent = `Page ${i + 1}`;
          section.append(chip);
        }
        section.append(document.createTextNode(p.text));
        textPane.append(section);
      });
      if (hasPreview) {
        const split = document.createElement("div");
        split.className = "doc-split";
        const preview = document.createElement("div");
        preview.className = "doc-preview";
        pages.forEach((p, i) => {
          if (!p.image) return;
          if (pages.length > 1) {
            const label = document.createElement("div");
            label.className = "doc-pagelabel";
            label.textContent = `Page ${i + 1} of ${pages.length}`;
            preview.append(label);
          }
          const img = document.createElement("img");
          img.className = "doc-page";
          img.setAttribute("data-doc-page", i);
          img.alt = `Document page ${i + 1}`;
          img.src = p.image;
          preview.append(img);
        });
        split.append(preview, textPane);
        docBody.append(split);
      } else {
        docBody.append(textPane);
      }
      docActions.textContent = "";
      const listenBtn = docButton("🔊 Listen", "doc-primary", () => {
        if (docReading) stopDocReading();
        else startDocReading(listenBtn);
      });
      docButton("Copy", "doc-secondary", async () => {
        try {
          await navigator.clipboard.writeText(docResultText);
          setStatus("Copied to clipboard", "ok");
        } catch {
          setStatus("Copy failed — select the text manually", "error");
        }
      });
      docButton("Close", "doc-secondary", closeDocModal);
      if (wasMock) {
        setStatus("Shown with mock OCR — install tesseract for real scans", "error");
      }
      // The user asked us to READ the document — start speaking
      // without demanding another tap (unless the page reader is
      // already talking, or the modal has been closed meanwhile:
      // never speak into a closed window).
      if (!isReading && docModal.getAttribute("data-open") === "true") {
        startDocReading(listenBtn);
      }
    }

    // Amber-mark the page (image + text section) currently being
    // spoken, and keep it scrolled into view in both panes.
    function highlightDocPage(idx) {
      docModal.querySelectorAll(".doc-page.speaking, .doc-ptext.speaking").forEach((el) => {
        el.classList.remove("speaking");
      });
      if (idx === null || idx === undefined) return;
      docModal.querySelectorAll(`[data-doc-page="${idx}"]`).forEach((el) => {
        el.classList.add("speaking");
        try { el.scrollIntoView({ block: "nearest", behavior: "smooth" }); } catch {}
      });
    }

    async function startDocReading(listenBtn) {
      if (docReading) return;
      if (isReading) {
        setStatus("Already reading the page — press Esc to stop that first", "error");
        return;
      }
      const pages = docPagesCurrent.filter((p) => (p.text || "").trim());
      if (!pages.length) return;
      docReading = true;
      listenBtn.textContent = "⏹ Stop reading";
      listenBtn.classList.add("speaking");
      const lang = dominantScript(docResultText) || resolvedLang() || "en";
      const blobPage = new WeakMap();
      player.onAdvance = (blob) => {
        if (blob && blobPage.has(blob)) highlightDocPage(blobPage.get(blob));
      };
      try {
        player.reset();
        const draining = player.drain();
        let enqueued = 0;
        for (let i = 0; i < pages.length; i++) {
          const chunks = splitIntoSentences(pages[i].text, CONFIG.maxChars);
          for (const chunk of chunks) {
            if (!docReading) break;
            try {
              const blob = await synthesise(chunk, lang);
              if (!docReading) break;
              blobPage.set(blob, i);
              player.enqueue(blob);
              enqueued++;
            } catch (err) {
              console.warn("[AaaS] OCR TTS chunk failed:", err);
            }
          }
          if (!docReading) break;
        }
        player.finish();
        await draining;
        if (!enqueued) setStatus("Voice unavailable — check that services are running", "error");
      } finally {
        docReading = false;
        player.onAdvance = null;
        highlightDocPage(null);
        listenBtn.textContent = "🔊 Listen again";
        listenBtn.classList.remove("speaking");
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
