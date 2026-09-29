/**
 * AaaS Companion — isolated-world config bridge.
 *
 * Runs at document_start in the extension's isolated world. Reads the
 * user's gateway URL and API key from chrome.storage.sync, then writes
 * them onto the <html> element's dataset so the widget (which runs in
 * the page's MAIN world) can read them back.
 *
 * The DOM is the only thing shared between isolated and main worlds, so
 * dataset attributes are the cleanest cross-world bridge — no postMessage
 * dance, no globals, and the page itself can still read them if desired.
 *
 * Also handles the "disabled on this tab" and "disabled globally" cases
 * by setting data-aaas-disabled=1 on <html>, which the widget's mount()
 * guard checks before painting the FAB.
 *
 * Finally, it bridges translation. The widget lives in the page's MAIN
 * world, where the page's CSP can block its fetch to the gateway. This
 * script (isolated world) listens for translate requests the widget posts
 * via window.postMessage, forwards them to the background service worker
 * (which reaches the gateway regardless of the page's CSP), and posts the
 * result back. The DOM/window is the only thing both worlds share.
 */

// Bridge: relay MAIN-world translate requests to the background worker.
// Wired up only on the enabled path below (no point listening when the
// extension is disabled for this tab).
// Widget request kind -> [background message type, response kind, fields].
const BRIDGE_ROUTES = {
  "translate-req": ["aaasTranslate", "translate-res", (d) => ({ text: d.text, src: d.src, tgt: d.tgt })],
  "fetch-doc-req": ["aaasFetchDoc", "fetch-doc-res", (d) => ({ url: d.url })],
};

function installTranslateBridge() {
  window.addEventListener("message", (ev) => {
    // Only trust messages from this same window/frame.
    if (ev.source !== window) return;
    const d = ev.data;
    if (!d || d.source !== "aaas-widget") return;
    const route = BRIDGE_ROUTES[d.kind];
    if (!route) return;
    const [type, resKind, fields] = route;
    const reply = (payload) =>
      window.postMessage({ source: "aaas-bridge", kind: resKind, id: d.id, ...payload }, "*");
    try {
      chrome.runtime.sendMessage({ type, ...fields(d) }, (resp) => {
        const lastErr = chrome.runtime.lastError;
        reply({
          ...(resp || {}),
          ok: !!(resp && resp.ok),
          error: lastErr ? lastErr.message : resp && resp.error,
        });
      });
    } catch (err) {
      reply({ ok: false, error: String((err && err.message) || err) });
    }
  });
}

(async () => {
  try {
    const defaults = {
      gateway: "https://168-144-216-83.sslip.io",
      apiKey: "aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18",
      defaultLang: "or",
      enabled: true,
      onDevice: true,
    };
    const cfg = await chrome.storage.sync.get(defaults);
    const html = document.documentElement;
    if (!html) return;
    if (!cfg.enabled) {
      html.dataset.aaasDisabled = "1";
      return;
    }
    // Tell the widget the extension's translate bridge is available so it
    // can retry translation through the background worker when the page's
    // CSP blocks its direct call to the gateway.
    html.dataset.aaasExt = "1";
    installTranslateBridge();
    html.dataset.aaasGateway = cfg.gateway || defaults.gateway;
    // Used when the hosted gateway is unreachable (offline demo laptop).
    html.dataset.aaasGatewayFallback = "http://127.0.0.1:8000";
    html.dataset.aaasKey = cfg.apiKey || defaults.apiKey;
    if (cfg.defaultLang && cfg.defaultLang !== "auto") {
      html.dataset.aaasLang = cfg.defaultLang;
    }
    if (cfg.onDevice) {
      html.dataset.aaasOnDevice = "1";
      // chrome.runtime.getURL is only callable from the isolated world; stash
      // the extension's root URL on the DOM so the main-world widget can
      // dynamic-import vendor/transformers.min.js and models/... from it.
      html.dataset.aaasExtRoot = chrome.runtime.getURL("");
    }
  } catch (err) {
    // chrome.storage can fail if the extension is being reloaded; the
    // widget will fall back to its built-in defaults, which still works
    // against the hosted gateway (sslip.io URL + seed key).
    console.warn("[AaaS Companion] config bridge failed:", err);
  }
})();
