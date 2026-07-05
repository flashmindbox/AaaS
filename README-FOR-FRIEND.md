# AaaS Portable Demo — Friend's Quickstart

This is a portable copy of the **Accessibility as a Service (AaaS)** hackathon
project. Everything you need to run it on a fresh Windows laptop is inside this
folder — including the pre-downloaded AI models.

---

## ⚡ Quick start (the easy way)

1. Install **Python 3.12 or 3.13** (tick **"Add Python to PATH"**) and **Node 20+** — details in §1 below.
2. Double-click **`START-HERE.bat`**.

That's the whole thing. The first run installs everything (5–10 minutes, needs
internet once) and then launches the demo automatically. Every run after that
just opens the demo straight away — no extra steps.

> Run `START-HERE.bat` from **inside this folder** (the one that also contains the
> `services` and `apps` folders). If anything looks wrong, double-click
> **`DIAGNOSE.bat`** and send the `diagnose-report.txt` it creates.

The sections below explain the same steps in detail and cover troubleshooting.

---

## 1. Prerequisites (install once, globally)

| Tool     | Version      | Where                                               |
|----------|--------------|-----------------------------------------------------|
| Python   | **3.12 or 3.13** (64-bit) | https://www.python.org/downloads/ — tick **"Add Python to PATH"** during install |
| Node.js  | **20 LTS or newer**       | https://nodejs.org/ (LTS installer is fine)         |
| pnpm     | 10+          | `SETUP-FRIEND.bat` installs it for you via `corepack` — no action needed |
| Git      | any recent   | Optional, only if you want to `git log` the history |

Roughly **3 GB of free disk** on top of the unzipped folder will be used by
the Python virtual environment and the pip cache.

---

## 2. One-time setup

1. Unzip the archive somewhere short and without spaces in the path.
   **Good:** `C:\AaaS\` — **Bad:** `C:\Users\you\Downloads\my stuff\AaaS (copy)\`
2. Double-click **`SETUP-FRIEND.bat`**.
3. First run takes **5–10 minutes** — it's downloading PyTorch (~800 MB),
   transformers, and the other Python deps. Subsequent runs are instant.
4. When it prints `SETUP COMPLETE`, close the window.

If it fails, scroll up in the window. The most common causes:
- Python not on PATH → reinstall Python and tick "Add to PATH"
- Corporate network blocking PyPI → use a personal hotspot
- Path too long (Windows 260-char limit) → move the folder to `C:\AaaS\`

---

## 2b. If something looks off later — re-check & auto-heal

Double-click **`ENSURE-READY.bat`** any time. It verifies every AI
model is present and downloads any that are missing. Safe to re-run;
fast when everything's already in place. Specifically:

- Confirms MMS-TTS (Odia/Hindi/English), NLLB-200, and IndicWav2Vec
  cache directories are complete — not missing, not truncated.
- Auto-downloads any non-gated model that's missing (needs internet,
  one-time per model).
- For the gated AI4Bharat Odia STT model: if `HF_TOKEN` isn't set in
  your environment, writes `AAAS_STT_ENGINE=mock` into
  `services/stt/.env` so the demo still boots with canned phrases.
  To get real Odia transcription later:
  1. Sign in at https://huggingface.co/ai4bharat/indicwav2vec-odia
     and click "Agree and access repository".
  2. Create a read token at https://huggingface.co/settings/tokens
  3. `set HF_TOKEN=hf_your_token_here` in the command prompt, then
     re-run `ENSURE-READY.bat`. It downloads the model (~870 MB) and
     flips STT back to real inference.

`SETUP-FRIEND.bat` also calls this check automatically as its final
step — so a fresh install always lands in a known-working state.

---

## 3. Running the demo

Double-click **`RUN-DEMO.bat`**.

It opens four terminal windows — one per service — and, after 15 seconds,
opens your browser to the Jajpur demo landing page at
<http://127.0.0.1:8000/demo/>.

| Service   | URL                       | Purpose                          |
|-----------|---------------------------|----------------------------------|
| Gateway   | http://127.0.0.1:8000     | Public entrypoint, static UI     |
| TTS       | http://127.0.0.1:8001     | Odia/Hindi/English speech        |
| STT       | http://127.0.0.1:8002     | Speech → text (Odia default)     |
| Translate | http://127.0.0.1:8003     | Indic ↔ English (NLLB-200)       |

To stop, close each of the four terminal windows (or press `Ctrl+C` in them).

---

## 4. What's inside the demo

The demo home page has three buttons leading to realistic Odisha demo sites:

1. **Utkal University admissions form** — with a floating accessibility
   widget (bottom-right). Click it and try the Odia voice, translation,
   reading tools, and dyslexia mode.
2. **Odisha government benefits portal** — same widget, a different tenant.
3. **BSE Odisha exam-board site** — the Board of Secondary Education demo
   tenant (schedules, results, accessibility provisions for PwD candidates),
   with the same widget.

The **browser extension** is also ready to load — see `apps/extension/README.md`
for the "Load unpacked" flow in Chrome/Edge.

---

## 5. Troubleshooting

**"Python is not recognised"**
Reinstall Python 3.12/3.13 and **check the "Add Python to PATH" box** on the
first screen of the installer. Close and reopen your terminal.

**"pnpm install" fails with EACCES or EPERM**
Run as the current user (not admin). If it still fails, delete
`node_modules\` and re-run `SETUP-FRIEND.bat`.

**Port 8000/8001/8002/8003 already in use**
Another process is using the port. Either stop it, or edit `RUN-DEMO.bat`
and change the `--port` numbers.

**TTS/Translate service window dies on startup**
Usually a missing model. Check `services/tts/models/` and
`services/translate/models/` — they should contain
`models--facebook--mms-tts-ory` and `models--facebook--nllb-200-distilled-600M`
respectively. If missing, they'll auto-download on first request as long as
the laptop is online.

**Widget shows "Limited mode" red badge**
The gateway can't reach one of the upstream services. Check that all four
terminal windows are still running. The widget falls back to the browser's
Web Speech API so the demo still works — just not with our Odia voice.

---

## 6. What the project is (90-second version)

**Accessibility as a Service (AaaS)** is a shared accessibility platform for
Indian public institutions — schools, universities, exam boards, government
portals. Rather than each institution building (usually poor) accessibility
separately, AaaS provides plug-and-play APIs:

- Odia / Hindi / English TTS (Meta MMS-TTS)
- Odia STT (AI4Bharat IndicWav2Vec)
- Indic ↔ English translation (Meta NLLB-200)
- WCAG 2.2 AA compliance dashboard

Built for the Smart Odisha Hackathon '25 by Team SUBARNAREKHA.
Apache-2.0 licensed. See `PLAN.md` for the full blueprint and
`hackathon/DEMO_SCRIPT.md` for the demo narrative.
