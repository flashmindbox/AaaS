/**
 * AaaS Companion — background service worker.
 *
 * Two jobs:
 *
 *   1. Seed sensible defaults on first install so the popup opens to a
 *      usable state, and open the options page on install.
 *
 *   2. Act as the translation proxy. The widget runs in the page's MAIN
 *      world, so its own fetch to the gateway is subject to the page's CSP
 *      (strict sites such as Wikipedia block it). The background service
 *      worker is not: with host_permissions it can reach the gateway from
 *      any page. So when the widget's direct call fails, the isolated-world
 *      bridge (inject-config.js) forwards the translate request here, we
 *      call the AaaS gateway (IndicTrans2), and hand the text back.
 */
const DEFAULTS = {
  gateway: "https://168-144-216-83.sslip.io",
  // Belongs to the ordinary "aaas-companion" tenant, not the operator — it
  // ships inside the extension, so anyone can read it.
  apiKey: "aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18",
  defaultLang: "or",
  enabled: true,
  // On-device mode runs TTS + STT entirely in the browser via transformers.js
  // + ONNX WASM. Defaults ON so read-aloud and speech work on any site
  // regardless of the page's CSP — the gateway path is blocked by strict-CSP
  // sites (e.g. Wikipedia). Translation always goes to the gateway, via this
  // service worker when the page blocks it. Users can switch TTS/STT back to
  // the gateway from the popup.
  onDevice: true,
};

// Defaults shipped before 0.5.0 (local demo bundle + operator seed key).
const LEGACY_GATEWAY = "http://127.0.0.1:8000";
// The offline demo bundle on this machine, tried when the configured
// gateway can't be reached at all (no internet at the venue).
const LOCAL_GATEWAY = "http://127.0.0.1:8000";
const LEGACY_API_KEY = "aaas_live_00000000000000000000000000000000";

chrome.runtime.onInstalled.addListener(async (details) => {
  const current = await chrome.storage.sync.get(DEFAULTS);
  const patch = {};
  for (const [k, v] of Object.entries(DEFAULTS)) {
    if (current[k] === undefined || current[k] === null) patch[k] = v;
  }
  // 0.5.0 moved the defaults from the local demo bundle to the hosted
  // server. Only users still on the old defaults are migrated — a gateway or
  // key someone typed in themselves is left alone.
  if (details.reason === "update") {
    if (current.gateway === LEGACY_GATEWAY) patch.gateway = DEFAULTS.gateway;
    if (current.apiKey === LEGACY_API_KEY) patch.apiKey = DEFAULTS.apiKey;
  }
  if (Object.keys(patch).length) await chrome.storage.sync.set(patch);

  if (details.reason === "install") {
    chrome.runtime.openOptionsPage?.();
  }
});

/* ---------------- Gateway translate proxy ---------------- */

// Small session cache so re-translating the same string (repeated headings,
// re-reads, hover then read) doesn't hit the network twice. The service
// worker can be torn down between bursts, so this is best-effort only.
const trCache = new Map();
const TR_CACHE_MAX = 1000;

// Translate one chunk via the gateway's /translate/translate (IndicTrans2).
// One retry on a rate-limit / transient 5xx, then we give up (the widget
// leaves the text as-is).
async function gatewayTranslateOne(text, src, tgt, cfg) {
  const key = `${src}|${tgt}|${text}`;
  if (trCache.has(key)) return trCache.get(key);

  let lastErr;
  let base = cfg.gateway;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(`${base}/translate/translate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": cfg.apiKey,
        },
        body: JSON.stringify({ text, src_lang: src, tgt_lang: tgt }),
        cache: "no-store",
      });
      if (!r.ok) {
        lastErr = new Error("gateway HTTP " + r.status);
        // Only retry transient failures.
        if (r.status === 429 || r.status >= 500) {
          await new Promise((res) => setTimeout(res, 400));
          continue;
        }
        throw lastErr;
      }
      const data = await r.json();
      if (typeof data?.text !== "string") {
        throw new Error("gateway: unexpected response shape");
      }
      if (trCache.size >= TR_CACHE_MAX) {
        trCache.delete(trCache.keys().next().value);
      }
      trCache.set(key, data.text);
      return data.text;
    } catch (err) {
      lastErr = err;
      // Unreachable (fetch threw, no HTTP status): retry once against the
      // local offline bundle, otherwise one short backoff before giving up.
      if (attempt === 0) {
        if (err instanceof TypeError && base !== LOCAL_GATEWAY) base = LOCAL_GATEWAY;
        else await new Promise((res) => setTimeout(res, 400));
        continue;
      }
    }
  }
  throw lastErr || new Error("gateway translate failed");
}

// The translate service rejects inputs over 2000 chars. Split long text on
// whitespace into ~1500-char windows, translate each, and rejoin. Most nodes
// are far shorter than this and take the fast single-request path.
async function gatewayTranslate(text, src, tgt) {
  const input = (text || "").toString();
  if (!input.trim()) return input;
  const cfg = await chrome.storage.sync.get(DEFAULTS);
  const MAX = 1500;
  if (input.length <= MAX) return gatewayTranslateOne(input, src, tgt, cfg);

  const parts = [];
  let buf = "";
  for (const word of input.split(/(\s+)/)) {
    if ((buf + word).length > MAX && buf) {
      parts.push(buf);
      buf = word;
    } else {
      buf += word;
    }
  }
  if (buf) parts.push(buf);
  const translated = await Promise.all(
    parts.map((p) => gatewayTranslateOne(p, src, tgt, cfg)),
  );
  return translated.join("");
}

/* ---------------- Document download proxy ---------------- */

// Read document needs the PDF/image bytes, but government sites often serve
// them from a CDN on another domain with no CORS headers, so the page can't
// read them. We can. Any page can ask through the bridge, so this is kept
// narrow: HTTPS only, no cookies (the page can't read anything private to
// the user on other sites), PDFs and images only, 15 MB cap.
const DOC_MAX_BYTES = 15_000_000;

async function fetchDocument(url) {
  const u = new URL(url);
  if (u.protocol !== "https:") throw new Error("only https documents can be fetched");
  const r = await fetch(u.href, { credentials: "omit", cache: "no-store" });
  if (!r.ok) throw new Error(`could not fetch the document (HTTP ${r.status})`);
  const contentType = (r.headers.get("content-type") || "").split(";")[0].trim();
  const buf = new Uint8Array(await r.arrayBuffer());
  const isPdf = contentType === "application/pdf" || (buf[0] === 0x25 && buf[1] === 0x50); // "%P"
  if (!isPdf && !contentType.startsWith("image/")) throw new Error("not a PDF or image");
  if (buf.length > DOC_MAX_BYTES) throw new Error("document too large (15 MB max)");
  // Base64 in chunks — String.fromCharCode(...buf) overflows the stack on big files.
  let bin = "";
  for (let i = 0; i < buf.length; i += 0x8000) {
    bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  }
  return { base64: btoa(bin), contentType: isPdf ? "application/pdf" : contentType };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg) return false;
  let work;
  if (msg.type === "aaasTranslate") {
    work = gatewayTranslate(msg.text, msg.src, msg.tgt).then((text) => ({ text }));
  } else if (msg.type === "aaasFetchDoc") {
    work = fetchDocument(msg.url);
  } else {
    return false;
  }
  work
    .then((res) => sendResponse({ ok: true, ...res }))
    .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
  // Returning true keeps the message channel open for the async sendResponse.
  return true;
});
