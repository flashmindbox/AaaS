/**
 * AaaS Companion — background service worker.
 *
 * Two jobs:
 *
 *   1. Seed sensible defaults on first install so the popup opens to a
 *      usable state, and open the options page on install.
 *
 *   2. Act as the translation proxy. The widget runs in the page's MAIN
 *      world and therefore cannot reach a cross-origin API (page CSP +
 *      CORS both block it, and in MV3 content scripts have no cross-origin
 *      privilege either). The background service worker is the *only*
 *      context that can: with host_permissions it reads cross-origin
 *      responses regardless of the page's CSP or whether Google sends
 *      CORS headers. So the isolated-world bridge (inject-config.js)
 *      forwards translate requests here, we call Google Translate's free
 *      endpoint, and hand the text back. This is what lets read-aloud and
 *      "Translate this page" work on any English website with no local
 *      AaaS gateway running.
 */
const DEFAULTS = {
  gateway: "http://127.0.0.1:8000",
  apiKey: "aaas_live_00000000000000000000000000000000",
  defaultLang: "or",
  enabled: true,
  // On-device mode runs TTS + STT entirely in the browser via transformers.js
  // + ONNX WASM. Defaults ON so read-aloud and speech work on any site with
  // no backend running and regardless of the page's CSP — the gateway path is
  // blocked by strict-CSP sites (e.g. Wikipedia). Translation is handled by
  // Google Translate via this service worker, so the whole feature set works
  // standalone. Users can switch back to the gateway path from the popup.
  onDevice: true,
};

chrome.runtime.onInstalled.addListener(async (details) => {
  const current = await chrome.storage.sync.get(DEFAULTS);
  const patch = {};
  for (const [k, v] of Object.entries(DEFAULTS)) {
    if (current[k] === undefined || current[k] === null) patch[k] = v;
  }
  if (Object.keys(patch).length) await chrome.storage.sync.set(patch);

  if (details.reason === "install") {
    chrome.runtime.openOptionsPage?.();
  }
});

/* ---------------- Google Translate proxy ---------------- */

// Our internal language codes map 1:1 to Google's (or = Odia/Oriya, hi =
// Hindi, en = English). Anything unknown becomes "auto" so Google detects the
// source itself — this keeps translation correct even when the page's language
// was guessed wrong.
function googleCode(code) {
  return ["or", "hi", "en"].includes(code) ? code : "auto";
}

// Small session cache so re-translating the same string (repeated headings,
// re-reads, hover then read) doesn't hit the network twice. The service
// worker can be torn down between bursts, so this is best-effort only.
const trCache = new Map();
const TR_CACHE_MAX = 1000;

// Translate one chunk via Google's free "gtx" endpoint. The response shape is
// [ [ [translated, original, ...], [translated2, original2, ...] ], ... ]; we
// concatenate every translated segment back into one string. One retry on a
// rate-limit / transient 5xx, then we give up (the widget falls back to the
// gateway, or leaves the text as-is).
async function googleTranslateOne(text, src, tgt) {
  const sl = googleCode(src);
  const tl = googleCode(tgt);
  const key = `${sl}|${tl}|${text}`;
  if (trCache.has(key)) return trCache.get(key);

  const url =
    "https://translate.googleapis.com/translate_a/single" +
    `?client=gtx&sl=${encodeURIComponent(sl)}&tl=${encodeURIComponent(tl)}` +
    `&dt=t&q=${encodeURIComponent(text)}`;

  let lastErr;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) {
        lastErr = new Error("google HTTP " + r.status);
        // Only retry transient failures.
        if (r.status === 429 || r.status >= 500) {
          await new Promise((res) => setTimeout(res, 400));
          continue;
        }
        throw lastErr;
      }
      const data = await r.json();
      if (!Array.isArray(data) || !Array.isArray(data[0])) {
        throw new Error("google: unexpected response shape");
      }
      const out = data[0].map((seg) => (seg && seg[0]) || "").join("");
      if (trCache.size >= TR_CACHE_MAX) {
        trCache.delete(trCache.keys().next().value);
      }
      trCache.set(key, out);
      return out;
    } catch (err) {
      lastErr = err;
      // Network blip — one short backoff before giving up.
      if (attempt === 0) {
        await new Promise((res) => setTimeout(res, 400));
        continue;
      }
    }
  }
  throw lastErr || new Error("google translate failed");
}

// Google's GET endpoint chokes on very long inputs (URL length). Split long
// text on whitespace into ~1500-char windows, translate each, and rejoin.
// Most nodes are far shorter than this and take the fast single-request path.
async function googleTranslate(text, src, tgt) {
  const input = (text || "").toString();
  if (!input.trim()) return input;
  const MAX = 1500;
  if (input.length <= MAX) return googleTranslateOne(input, src, tgt);

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
    parts.map((p) => googleTranslateOne(p, src, tgt)),
  );
  return translated.join("");
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.type !== "aaasTranslate") return false;
  googleTranslate(msg.text, msg.src, msg.tgt)
    .then((text) => sendResponse({ ok: true, text }))
    .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
  // Returning true keeps the message channel open for the async sendResponse.
  return true;
});
