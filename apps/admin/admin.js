/* ---------------------------------------------------------------
   AaaS Operator Console
   ---------------------------------------------------------------
   Vanilla JS, no build step, no CDN — must work on the offline
   judge bundle. Talks to the gateway's in-process /admin/api/*
   routes plus the same proxy endpoints the widget uses, so every
   number and every playground response on this page is REAL.

   The operator seed key is embedded: this console is a local demo
   surface served from the same trusted gateway, not an internet-
   facing product page.
---------------------------------------------------------------- */

const KEY = "aaas_live_00000000000000000000000000000000";
const HDRS = { "X-API-Key": KEY };
const JSON_HDRS = { ...HDRS, "Content-Type": "application/json" };

const $ = (sel) => document.querySelector(sel);

/* ---------- clock ---------- */
setInterval(() => {
  $("#clock").textContent = new Date().toLocaleTimeString();
}, 1000);

/* ---------- service health (every 10 s) ---------- */
const HEALTH_TARGETS = [
  { svc: "gateway", url: "/healthz", auth: false },
  { svc: "tts", url: "/tts/readyz", auth: true },
  { svc: "stt", url: "/stt/readyz", auth: true },
  { svc: "translate", url: "/translate/readyz", auth: true },
];

async function checkHealth() {
  for (const t of HEALTH_TARGETS) {
    const el = document.querySelector(`.svc[data-svc="${t.svc}"] .state`);
    const t0 = performance.now();
    try {
      const r = await fetch(t.url, { headers: t.auth ? HDRS : {}, cache: "no-store" });
      const ms = Math.round(performance.now() - t0);
      if (r.ok) {
        el.textContent = `healthy · ${ms} ms`;
        el.className = "state chip ok";
      } else {
        el.textContent = `HTTP ${r.status}`;
        el.className = "state chip bad";
      }
    } catch {
      el.textContent = "unreachable";
      el.className = "state chip bad";
    }
  }
  const gwOk = document.querySelector('.svc[data-svc="gateway"] .state').classList.contains("ok");
  const chip = $("#gw-chip");
  chip.textContent = gwOk ? "gateway online" : "gateway offline";
  chip.className = "chip " + (gwOk ? "ok" : "bad");
}

/* ---------- usage (every 5 s) ---------- */
let lastTotal = -1;
let usageByTenant = {};

async function refreshUsage() {
  try {
    const r = await fetch("/admin/api/usage", { headers: HDRS, cache: "no-store" });
    if (!r.ok) return;
    const u = await r.json();

    const kReq = $("#k-req");
    kReq.textContent = u.total_requests.toLocaleString();
    if (lastTotal >= 0 && u.total_requests > lastTotal) {
      kReq.classList.add("bump");
      setTimeout(() => kReq.classList.remove("bump"), 900);
    }
    lastTotal = u.total_requests;
    $("#k-err").textContent = u.total_errors.toLocaleString();
    $("#k-tenants").textContent = Object.keys(u.by_tenant || {}).length;
    const buckets = u.buckets || [];
    const latest = buckets[buckets.length - 1];
    $("#k-p95").textContent = latest ? `${latest.p95_latency_ms} ms` : "—";

    usageByTenant = u.by_tenant || {};
    renderEndpoints(u.by_endpoint || {});
    renderBuckets(buckets.slice(-6).reverse());
    renderTenantCounts();
  } catch {
    /* gateway briefly away — chips already show it */
  }
}

function renderEndpoints(byEndpoint) {
  const entries = Object.entries(byEndpoint).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = entries.length ? entries[0][1] : 1;
  const box = $("#endpoints");
  box.textContent = "";
  for (const [name, n] of entries) {
    const row = document.createElement("div");
    row.className = "bar";
    row.innerHTML =
      `<span class="label">/${name}</span>` +
      `<span class="track"><span class="fill" style="width:${Math.max(2, (n / max) * 100)}%"></span></span>` +
      `<span class="n">${n.toLocaleString()}</span>`;
    box.append(row);
  }
  if (!entries.length) box.innerHTML = '<p class="muted">no traffic yet — open a demo site</p>';
}

function renderBuckets(buckets) {
  const tb = $("#buckets tbody");
  tb.textContent = "";
  for (const b of buckets) {
    const tr = document.createElement("tr");
    const hh = b.hour.slice(11, 16);
    tr.innerHTML =
      `<td>${hh}</td><td class="num">${b.requests}</td>` +
      `<td class="num">${b.errors}</td><td class="num">${b.p50_latency_ms}</td>` +
      `<td class="num">${b.p95_latency_ms}</td>`;
    tb.append(tr);
  }
  if (!buckets.length) tb.innerHTML = '<tr><td colspan="5" class="muted">no traffic yet</td></tr>';
}

/* ---------- tenants ---------- */
let tenantsLoaded = false;

async function loadTenants() {
  try {
    const r = await fetch("/admin/api/tenants", { headers: HDRS, cache: "no-store" });
    if (!r.ok) return;
    const tenants = await r.json();
    // Real key prefixes come from the per-tenant detail endpoint.
    const details = await Promise.all(
      tenants.map((t) =>
        fetch(`/admin/api/tenants/${t.slug}`, { headers: HDRS, cache: "no-store" })
          .then((res) => (res.ok ? res.json() : null))
          .catch(() => null),
      ),
    );
    const tb = $("#tenants tbody");
    tb.textContent = "";
    tenants.forEach((t, i) => {
      const keys = (details[i] && details[i].keys) || [];
      const prefix = keys.length ? `${keys[0].prefix}…` : "—";
      const tr = document.createElement("tr");
      tr.dataset.slug = t.slug;
      tr.innerHTML =
        `<td><strong>${t.display_name}</strong><br /><span class="muted">${t.slug}</span></td>` +
        `<td><span class="cat">${t.category}</span></td>` +
        `<td>${t.region || "—"}</td>` +
        `<td class="num tenant-count">0</td>` +
        `<td class="keycode">${prefix}</td>` +
        `<td><button class="mini" data-mint="${t.slug}">Mint key</button></td>`;
      tb.append(tr);
    });
    tenantsLoaded = true;
    renderTenantCounts();
    tb.addEventListener("click", async (ev) => {
      const slug = ev.target && ev.target.dataset ? ev.target.dataset.mint : null;
      if (!slug) return;
      ev.target.disabled = true;
      try {
        const resp = await fetch(`/admin/api/tenants/${slug}/keys`, {
          method: "POST",
          headers: JSON_HDRS,
          body: JSON.stringify({ name: "judge-demo" }),
        });
        const body = await resp.json();
        const minted = $("#minted");
        minted.hidden = false;
        if (resp.ok) {
          minted.textContent =
            `New key for ${slug} (shown once, live immediately): ${body.raw}` +
            ` — the integration snippet below now uses it.`;
          setSnippet(body.raw, `${slug} · ${body.raw.slice(0, 14)}…`);
        } else {
          minted.textContent = `Mint failed: HTTP ${resp.status}`;
        }
      } finally {
        ev.target.disabled = false;
      }
    });
  } catch {
    /* retried by the caller's interval */
  }
}

function renderTenantCounts() {
  if (!tenantsLoaded) return;
  document.querySelectorAll("#tenants tbody tr").forEach((tr) => {
    const n = usageByTenant[tr.dataset.slug] || 0;
    const cell = tr.querySelector(".tenant-count");
    if (cell) cell.textContent = n.toLocaleString();
  });
}

/* ---------- playground ---------- */
function showResp(el, obj, ms) {
  el.hidden = false;
  el.innerHTML =
    `<span class="lat">HTTP 200 · ${ms} ms</span>\n` +
    (typeof obj === "string" ? obj : JSON.stringify(obj, null, 2));
}

function showErr(el, status, text, ms) {
  el.hidden = false;
  el.innerHTML = `<span class="lat">HTTP ${status} · ${ms} ms</span>\n${text}`;
}

function curlFor(path, payload) {
  return (
    `curl -X POST http://127.0.0.1:8000${path} \\\n` +
    `  -H "X-API-Key: ${KEY}" \\\n` +
    `  -H "Content-Type: application/json" \\\n` +
    `  -d '${JSON.stringify(payload)}'`
  );
}

async function playJson(btn, path, payload, outEl, curlEl, render) {
  btn.disabled = true;
  const t0 = performance.now();
  try {
    const r = await fetch(path, { method: "POST", headers: JSON_HDRS, body: JSON.stringify(payload) });
    const ms = Math.round(performance.now() - t0);
    curlEl.hidden = false;
    curlEl.textContent = curlFor(path, payload);
    if (r.ok) {
      const body = await r.json();
      showResp(outEl, render ? render(body) : body, ms);
    } else {
      showErr(outEl, r.status, (await r.text()).slice(0, 400), ms);
    }
  } catch (err) {
    outEl.hidden = false;
    outEl.textContent = "request failed: " + err.message;
  } finally {
    btn.disabled = false;
  }
}

$("#tr-go").addEventListener("click", () => {
  playJson(
    $("#tr-go"),
    "/translate/translate",
    { text: $("#tr-in").value, src_lang: $("#tr-src").value, tgt_lang: $("#tr-tgt").value },
    $("#tr-out"),
    $("#tr-curl"),
  );
});

$("#si-go").addEventListener("click", () => {
  playJson(
    $("#si-go"),
    "/translate/simplify",
    { text: $("#si-in").value, lang: "en" },
    $("#si-out"),
    $("#si-curl"),
  );
});

$("#ts-go").addEventListener("click", async () => {
  const btn = $("#ts-go");
  const outEl = $("#ts-out");
  const payload = { text: $("#ts-in").value };
  btn.disabled = true;
  const t0 = performance.now();
  try {
    const r = await fetch("/tts/synthesise", {
      method: "POST",
      headers: JSON_HDRS,
      body: JSON.stringify(payload),
    });
    const ms = Math.round(performance.now() - t0);
    const curlEl = $("#ts-curl");
    curlEl.hidden = false;
    curlEl.textContent = curlFor("/tts/synthesise", payload) + " \\\n  --output speech.wav";
    if (r.ok) {
      const blob = await r.blob();
      const audio = $("#ts-audio");
      audio.src = URL.createObjectURL(blob);
      audio.hidden = false;
      audio.play().catch(() => {});
      showResp(outEl, `Content-Type: ${r.headers.get("Content-Type")}\naudio bytes: ${blob.size.toLocaleString()}`, ms);
    } else {
      showErr(outEl, r.status, (await r.text()).slice(0, 400), ms);
    }
  } catch (err) {
    outEl.hidden = false;
    outEl.textContent = "request failed: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

/* ---------- onboarding: create tenant + integration snippet ---------- */
function setSnippet(key, label) {
  const origin = location.origin;
  $("#snippet").textContent =
    `<script\n` +
    `  src="${origin}/widget.js"\n` +
    `  data-key="${key}"\n` +
    `  defer\n` +
    `></script>`;
  $("#snippet-key-label").textContent = label || key.slice(0, 14) + "…";
}
setSnippet(KEY, "operator seed key");

$("#copy-snippet").addEventListener("click", async () => {
  const text = $("#snippet").textContent;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // Clipboard API can be denied — fall back to a selection copy.
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.append(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  const ok = $("#copy-ok");
  ok.hidden = false;
  setTimeout(() => { ok.hidden = true; }, 1800);
});

$("#ob-go").addEventListener("click", async () => {
  const btn = $("#ob-go");
  const out = $("#ob-out");
  const name = $("#ob-name").value.trim();
  if (!name) {
    out.hidden = false;
    out.textContent = "Give the website a name first.";
    return;
  }
  btn.disabled = true;
  const t0 = performance.now();
  const payload = {
    display_name: name,
    category: $("#ob-cat").value,
    region: $("#ob-region").value.trim() || null,
  };
  try {
    const r = await fetch("/admin/api/tenants", {
      method: "POST",
      headers: JSON_HDRS,
      body: JSON.stringify(payload),
    });
    const ms = Math.round(performance.now() - t0);
    if (r.ok) {
      const body = await r.json();
      showResp(out, {
        tenant: body.tenant.slug,
        category: body.tenant.category,
        api_key: body.raw + "   (shown once — live immediately)",
      }, ms);
      setSnippet(body.raw, `${body.tenant.slug} · ${body.raw.slice(0, 14)}…`);
      tenantsLoaded = false;
      loadTenants(); // the new row appears in the table above
    } else {
      showErr(out, r.status, (await r.text()).slice(0, 300), ms);
    }
  } catch (err) {
    out.hidden = false;
    out.textContent = "request failed: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

/* ---------- boot ---------- */
checkHealth();
loadTenants();
refreshUsage();
setInterval(checkHealth, 10_000);
setInterval(refreshUsage, 5_000);
setInterval(() => { if (!tenantsLoaded) loadTenants(); }, 7_000);
