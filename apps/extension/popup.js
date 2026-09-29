/**
 * AaaS Companion — popup controller.
 *
 * Loads current settings from chrome.storage.sync, lets the user edit
 * them, probes the gateway /healthz on demand, and saves on click.
 */
const DEFAULTS = {
  gateway: "https://168-144-216-83.sslip.io",
  apiKey: "aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18",
  defaultLang: "or",
  enabled: true,
  onDevice: true,
};

const $ = (id) => document.getElementById(id);

function applyOnDeviceUi(on) {
  // Gateway fields are still usable (translation still hits the gateway in
  // on-device mode) but de-emphasise them so users aren't confused about
  // whether the gateway URL matters for TTS/STT.
  $("gwSection")?.classList.toggle("dimmed", !!on);
  const testBtn = $("test");
  if (testBtn) testBtn.disabled = false; // still probe-able
}

async function load() {
  const cfg = await chrome.storage.sync.get(DEFAULTS);
  $("enabled").checked = cfg.enabled !== false;
  $("onDevice").checked = cfg.onDevice === true;
  $("gateway").value = cfg.gateway || DEFAULTS.gateway;
  $("apiKey").value = cfg.apiKey || DEFAULTS.apiKey;
  $("defaultLang").value = cfg.defaultLang || DEFAULTS.defaultLang;
  applyOnDeviceUi($("onDevice").checked);
}

function setStatus(text, kind) {
  const el = $("status");
  el.textContent = text;
  el.className = "status" + (kind ? " " + kind : "");
}

function sanitizeGateway(raw) {
  const trimmed = (raw || "").trim().replace(/\/+$/, "");
  if (!trimmed) return DEFAULTS.gateway;
  try {
    const u = new URL(trimmed);
    if (!/^https?:$/.test(u.protocol)) throw new Error("bad protocol");
    return u.origin;
  } catch {
    return null;
  }
}

async function save() {
  const gateway = sanitizeGateway($("gateway").value);
  if (!gateway) {
    setStatus("Gateway URL must be http(s)://host[:port]", "error");
    return;
  }
  const apiKey = ($("apiKey").value || "").trim() || DEFAULTS.apiKey;
  const defaultLang = $("defaultLang").value || DEFAULTS.defaultLang;
  const enabled = !!$("enabled").checked;
  const onDevice = !!$("onDevice").checked;
  await chrome.storage.sync.set({
    gateway,
    apiKey,
    defaultLang,
    enabled,
    onDevice,
  });
  setStatus("Saved. Reload the page to apply.", "ok");
  $("gateway").value = gateway;
}

async function test() {
  const gateway = sanitizeGateway($("gateway").value);
  if (!gateway) {
    setStatus("Gateway URL must be http(s)://host[:port]", "error");
    return;
  }
  setStatus("Probing " + gateway + "/healthz…");
  try {
    const r = await fetch(gateway + "/healthz", { cache: "no-store" });
    if (r.ok) {
      setStatus("Gateway reachable (HTTP " + r.status + ")", "ok");
    } else {
      setStatus("Gateway answered HTTP " + r.status, "error");
    }
  } catch (err) {
    setStatus("Gateway unreachable: " + (err.message || err), "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  $("save").addEventListener("click", save);
  $("test").addEventListener("click", test);
  $("onDevice").addEventListener("change", (e) =>
    applyOnDeviceUi(e.target.checked),
  );
  // Save on Enter in any text field.
  document.querySelectorAll("input[type=url], input[type=text]").forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") save();
    });
  });
});
