/**
 * AaaS Companion — on-device (offline) TTS + STT backend (main-thread shim).
 *
 * Dynamically imported by widget.js when "On-device mode" is on. All heavy
 * work (transformers.js + ONNX WASM) runs in a dedicated Worker so the host
 * page's main thread never blocks.
 *
 * Why this is more than `new Worker(...)`:
 *  - A Worker's script must be same-origin as the page, so a
 *    chrome-extension:// URL is refused. We build the worker from an inlined
 *    source string via a blob: URL instead (no separate WAR file needed —
 *    reloads don't reliably re-apply web_accessible_resources list changes).
 *  - A page-spawned Worker also can't load chrome-extension:// resources at
 *    all on strict-CSP sites. So this shim (running as the content script,
 *    which CAN read the extension's web-accessible resources even there)
 *    fetches transformers.js, the ONNX wasm and the model files itself, and
 *    hands the BYTES to the worker, which serves them from memory. Nothing in
 *    the worker is cross-origin.
 *  - transformers.js resolves URLs against import.meta.url; from a blob that's
 *    "blob:…", an invalid base — so we rewrite it to the in-memory sentinel.
 *
 * Stays on the main thread here because a Worker can't: building the WAV Blob
 * and decoding microphone audio (needs an AudioContext).
 *
 * Translation is not on-device — widget.js keeps routing /translate to the
 * gateway even in on-device mode.
 */

const MMS_LANG_REPO = { or: "mms-tts-ory", hi: "mms-tts-hin", en: "mms-tts-eng" };
const WASM_NAME = "ort-wasm-simd-threaded.jsep.wasm";
const TTS_FILES = [
  "config.json",
  "tokenizer.json",
  "tokenizer_config.json",
  "vocab.json",
  "special_tokens_map.json",
  "added_tokens.json",
  "onnx/model_quantized.onnx",
];
const STT_FILES = [
  "config.json",
  "generation_config.json",
  "preprocessor_config.json",
  "tokenizer.json",
  "tokenizer_config.json",
  "vocab.json",
  "special_tokens_map.json",
  "added_tokens.json",
  "onnx/encoder_model_quantized.onnx",
  "onnx/decoder_model_merged_quantized.onnx",
];

// The Worker runs entirely on bytes handed in from here; it never touches
// chrome-extension:// (so any page CSP that allows blob: workers + WASM is
// fine). transformers is imported from a blob: URL (tjsUrl); model + wasm
// requests hit a fetch shim backed by `fileStore`.
const WORKER_SRC = `
const MMS_LANG_REPO = { or: "mms-tts-ory", hi: "mms-tts-hin", en: "mms-tts-eng" };
const STT_MODEL = "whisper-base";
// Whisper's 99 languages do NOT include Odia — never ask it to. Odia
// speech throws up-front in transcribe() so the widget falls back to
// the gateway's IndicWav2Vec (the good Odia engine) instead of getting
// garbage auto-detected text from whisper-base.
const WHISPER_LANG = { hi: "hindi", en: "english" };
const BASE = "https://aaas.local/";
const fileStore = new Map();
const realFetch = self.fetch.bind(self);
self.fetch = (input, init) => {
  const url = typeof input === "string" ? input : (input && input.url) || "";
  if (url.startsWith(BASE)) {
    const key = decodeURIComponent(url.slice(BASE.length).split("?")[0]);
    const buf = fileStore.get(key);
    if (buf) {
      const ct = key.endsWith(".json") ? "application/json"
        : key.endsWith(".wasm") ? "application/wasm"
        : "application/octet-stream";
      return Promise.resolve(new Response(buf, { status: 200, headers: { "Content-Type": ct } }));
    }
    return Promise.resolve(new Response(null, { status: 404 }));
  }
  return realFetch(input, init);
};
let _tjsPromise = null, _tjsUrl = "";
function loadTransformers() {
  if (_tjsPromise) return _tjsPromise;
  _tjsPromise = (async () => {
    const mod = await import(_tjsUrl);
    const env = mod.env;
    env.allowLocalModels = true;
    env.allowRemoteModels = false;
    env.localModelPath = BASE + "models/";
    env.backends.onnx.wasm.wasmPaths = BASE + "vendor/";
    env.backends.onnx.wasm.numThreads = 1;
    return mod;
  })();
  return _tjsPromise;
}
let _tail = Promise.resolve();
function runExclusive(task) {
  const run = _tail.then(task, task);
  _tail = run.then(() => {}, () => {});
  return run;
}
const ttsCache = new Map();
const ttsLoading = new Map();
function getTtsModel(lang) {
  const repo = MMS_LANG_REPO[lang];
  if (!repo) return Promise.reject(new Error("on-device TTS: unsupported language " + lang));
  if (ttsCache.has(repo)) return Promise.resolve(ttsCache.get(repo));
  let p = ttsLoading.get(repo);
  if (!p) {
    p = (async () => {
      const tjs = await loadTransformers();
      const pair = await Promise.all([
        tjs.AutoTokenizer.from_pretrained(repo),
        tjs.AutoModel.from_pretrained(repo, { dtype: "q8" }),
      ]);
      const entry = { tokenizer: pair[0], model: pair[1] };
      ttsCache.set(repo, entry);
      return entry;
    })();
    ttsLoading.set(repo, p);
    p.then(() => {}, () => {}).then(() => { if (ttsLoading.get(repo) === p) ttsLoading.delete(repo); });
  }
  return p;
}
async function speak(text, lang) {
  const m = await getTtsModel(lang || "or");
  const inputs = await m.tokenizer(text);
  const output = await runExclusive(() => m.model(inputs));
  const wf = output && output.waveform;
  if (!wf || !wf.data) throw new Error("on-device TTS: model returned no waveform");
  const samples = wf.data instanceof Float32Array ? wf.data : Float32Array.from(wf.data);
  const sampleRate = (m.model.config && m.model.config.sampling_rate) || 16000;
  return { samples: samples, sampleRate: sampleRate };
}
let _stt = null;
async function getStt() {
  if (_stt) return _stt;
  const tjs = await loadTransformers();
  _stt = await tjs.pipeline("automatic-speech-recognition", STT_MODEL, { dtype: "q8" });
  return _stt;
}
async function transcribe(audio, lang) {
  if (lang === "or") {
    throw new Error("on-device STT has no Odia model - routing to the gateway engine");
  }
  const pipe = await getStt();
  const opts = {};
  if (lang && WHISPER_LANG[lang]) { opts.language = WHISPER_LANG[lang]; opts.task = "transcribe"; }
  let out;
  try {
    out = await runExclusive(() => pipe(audio, opts));
  } catch (err) {
    // Some ONNX conversions ship without the tokenizer's language map
    // and reject ANY named language ('Must be one of: {}') - retry
    // once with auto-detect rather than failing the whole request.
    if (opts.language && /not supported/i.test(String(err && err.message))) {
      out = await runExclusive(() => pipe(audio, {}));
    } else {
      throw err;
    }
  }
  return { text: ((out && out.text) || "").trim(), language: lang || "en", confidence: null, engine: "whisper-base-ondevice" };
}
self.onmessage = async (ev) => {
  const msg = ev.data || {};
  const id = msg.id, type = msg.type;
  try {
    if (type === "init") {
      _tjsUrl = msg.tjsUrl;
      if (msg.wasm && msg.wasmName) fileStore.set("vendor/" + msg.wasmName, msg.wasm);
      self.postMessage({ id: id, ok: true });
    } else if (type === "loadFiles") {
      const files = msg.files || {};
      for (const name of Object.keys(files)) fileStore.set(msg.prefix + name, files[name]);
      self.postMessage({ id: id, ok: true });
    } else if (type === "speak") {
      const r = await speak(msg.text, msg.lang);
      self.postMessage({ id: id, ok: true, samples: r.samples, sampleRate: r.sampleRate }, [r.samples.buffer]);
    } else if (type === "transcribe") {
      const result = await transcribe(new Float32Array(msg.audio), msg.lang);
      self.postMessage({ id: id, ok: true, result: result });
    } else {
      throw new Error("on-device worker: unknown message type " + type);
    }
  } catch (e) {
    self.postMessage({ id: id, ok: false, error: String((e && e.stack) || e) });
  }
};
`;

// Float32Array (-1..1) at sampleRate -> audio/wav Blob (PCM16 mono).
function float32ToWavBlob(samples, sampleRate) {
  const numSamples = samples.length;
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + numSamples * bytesPerSample);
  const view = new DataView(buffer);
  const writeAscii = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeAscii(0, "RIFF");
  view.setUint32(4, 36 + numSamples * bytesPerSample, true);
  writeAscii(8, "WAVE");
  writeAscii(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeAscii(36, "data");
  view.setUint32(40, numSamples * bytesPerSample, true);
  let off = 44;
  for (let i = 0; i < numSamples; i++) {
    let s = samples[i];
    if (s > 1) s = 1;
    else if (s < -1) s = -1;
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

// Mic blob (webm/opus @48k) -> Float32Array @16k mono. Main thread only —
// a Worker has no AudioContext / OfflineAudioContext.
async function decodeToMono16k(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const decodeAc = new AudioCtx();
  let decoded;
  try {
    decoded = await decodeAc.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    try {
      decodeAc.close();
    } catch {}
  }
  const duration = decoded.duration;
  const samplesOut = Math.max(1, Math.floor(16000 * duration));
  const offline = new OfflineAudioContext(1, samplesOut, 16000);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start();
  const rendered = await offline.startRendering();
  return rendered.getChannelData(0);
}

export async function createOnDeviceBackend({ extRoot } = {}) {
  if (!extRoot || typeof extRoot !== "string") {
    throw new Error("createOnDeviceBackend: extRoot is required");
  }
  if (!extRoot.endsWith("/")) extRoot += "/";

  // Fetch transformers.js + the ONNX wasm (web-accessible resources the
  // content script can read on any page). The worker source is inlined above.
  const [tjsSrc, wasmBuf] = await Promise.all([
    fetch(extRoot + "vendor/transformers.min.js").then((r) => r.text()),
    fetch(extRoot + "vendor/" + WASM_NAME).then((r) => r.arrayBuffer()),
  ]);
  // transformers resolves internal URLs against import.meta.url, which is the
  // blob: URL here and an invalid base for new URL(). Point it at the sentinel
  // the worker's fetch shim understands.
  const tjsPatched = tjsSrc.replaceAll(
    "import.meta.url",
    JSON.stringify("https://aaas.local/vendor/transformers.min.js"),
  );
  const tjsUrl = URL.createObjectURL(
    new Blob([tjsPatched], { type: "text/javascript" }),
  );
  const workerUrl = URL.createObjectURL(
    new Blob([WORKER_SRC], { type: "text/javascript" }),
  );
  const worker = new Worker(workerUrl, { type: "module" });

  let seq = 0;
  const pending = new Map();
  worker.addEventListener("message", (ev) => {
    const { id, ok, error } = ev.data || {};
    const p = pending.get(id);
    if (!p) return;
    pending.delete(id);
    if (ok) p.resolve(ev.data);
    else p.reject(new Error(error || "on-device worker error"));
  });
  worker.addEventListener("error", (e) => {
    const err = new Error(
      "on-device worker crashed: " + ((e && e.message) || "unknown"),
    );
    for (const p of pending.values()) p.reject(err);
    pending.clear();
  });
  function call(type, payload, transfer) {
    return new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, type, ...payload }, transfer || []);
    });
  }

  await call("init", { tjsUrl, wasm: wasmBuf, wasmName: WASM_NAME }, [wasmBuf]);

  const loaded = new Map();
  function ensureFiles(repo, names) {
    let p = loaded.get(repo);
    if (p) return p;
    p = (async () => {
      const files = {};
      const transfers = [];
      await Promise.all(
        names.map(async (n) => {
          try {
            const r = await fetch(`${extRoot}models/${repo}/${n}`);
            if (r.ok) {
              const b = await r.arrayBuffer();
              files[n] = b;
              transfers.push(b);
            }
          } catch {}
        }),
      );
      await call("loadFiles", { prefix: `models/${repo}/`, files }, transfers);
    })();
    loaded.set(repo, p);
    return p;
  }

  async function speak(text, lang) {
    lang = lang || "or";
    const repo = MMS_LANG_REPO[lang];
    if (!repo) throw new Error("on-device TTS: unsupported language " + lang);
    await ensureFiles(repo, TTS_FILES);
    const { samples, sampleRate } = await call("speak", { text, lang });
    return float32ToWavBlob(samples, sampleRate);
  }

  async function transcribe(blob, languageHint) {
    await ensureFiles("whisper-base", STT_FILES);
    const audio = await decodeToMono16k(blob);
    const { result } = await call(
      "transcribe",
      { audio: audio.buffer, lang: languageHint },
      [audio.buffer],
    );
    return result;
  }

  return { speak, transcribe };
}
