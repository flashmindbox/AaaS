"""Build the judge-laptop AaaS demo bundle — single source of truth.

Usage (from the repo root):

    python scripts/build_bundle.py                   # full build + smoke test
    python scripts/build_bundle.py --skip-tts        # reuse services/tts/dist
    python scripts/build_bundle.py --skip-stt        # reuse services/stt/dist
    python scripts/build_bundle.py --skip-translate  # reuse services/translate/dist
    python scripts/build_bundle.py --skip-gw         # reuse services/gateway/dist
    python scripts/build_bundle.py --clean           # wipe caches + prior bundle
    python scripts/build_bundle.py --no-smoke        # skip end-to-end verification

Output:

    <repo>/dist/AaaS-Demo/           -- the USB-ready folder
    <repo>/dist/AaaS-Demo.sha256     -- hashes of all four exes
    stdout                           -- step log + bundle size + next steps

Ships four services: gateway (proxy + static UI), tts (Odia VITS via
Meta MMS), stt (mock speech-to-text), translate (mock Indic↔English
translation, REAL Tesseract OCR + rule-based /simplify).
The STT/Translate mock engines are deterministic and zero-weight, so
the bundle fits on a 2 GB USB. Source builds now default to the real
AI4Bharat engines (see ``services/stt/app/config.py``); the bundle
launchers explicitly override back to mock because torch isn't shipped.
Real engines in the bundle require pre-fetched weights and the
``[indic]`` extras — see ``docs/bundle-build.md``.

OCR ships REAL: the translate build installs the ``[ocr]`` extra,
prefetches ori/hin/eng traineddata, and the bundle carries a minimal
Tesseract runtime (tesseract.exe + DLLs, copied from the build
machine's install) so the widget's "Read document" feature scans
actual notices on the judge laptop instead of returning mock text.
If Tesseract isn't installed on the build machine the bundle still
assembles — OCR then falls back to mock and the build log warns.

The script is intentionally a single file — it runs on a fresh Windows
box without a pnpm install or Node at all. The only prerequisite is a
Python 3.12+ interpreter on PATH.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]
TTS_DIR = REPO / "services" / "tts"
STT_DIR = REPO / "services" / "stt"
TR_DIR = REPO / "services" / "translate"
GW_DIR = REPO / "services" / "gateway"
EXT_DIR = REPO / "apps" / "extension"
BUNDLE_ASSETS = REPO / "scripts" / "bundle_assets"
DIST_ROOT = REPO / "dist"
BUNDLE_OUT = DIST_ROOT / "AaaS-Demo"

SEED_API_KEY = "aaas_live_00000000000000000000000000000000"

# --------------------------------------------------------------------------
# Pretty console
# --------------------------------------------------------------------------

_STEP = 0


def step(msg: str) -> None:
    global _STEP
    _STEP += 1
    print(f"\n[{_STEP:02d}] {msg}", flush=True)


def info(msg: str) -> None:
    print(f"     {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"\nERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# --------------------------------------------------------------------------
# Subprocess helpers
# --------------------------------------------------------------------------


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    info("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), env=env)
    if proc.returncode != 0:
        die(f"command failed ({proc.returncode}): {' '.join(cmd)}")


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def ensure_venv(service_dir: Path, clean: bool) -> Path:
    venv = service_dir / ".venv"
    if clean and venv.exists():
        info(f"removing stale venv at {venv}")
        shutil.rmtree(venv, ignore_errors=True)
    py = venv_python(venv)
    if not py.exists():
        info(f"creating venv at {venv}")
        run([sys.executable, "-m", "venv", str(venv)], cwd=service_dir)
    # Always bump pip so wheel downloads don't break on a cold box.
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel"], cwd=service_dir)
    return py


def pip_install_editable(py: Path, service_dir: Path, extras: list[str]) -> None:
    spec = f".[{','.join(extras)}]" if extras else "."
    run([str(py), "-m", "pip", "install", "-e", spec], cwd=service_dir)


# --------------------------------------------------------------------------
# HTTP smoke-test helpers (stdlib only — no extra deps in the orchestrator)
# --------------------------------------------------------------------------


def http_get(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b""
    except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout):
        return 0, b""


def http_post_json(
    url: str,
    payload: dict[str, str],
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes, str]:
    import json

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return exc.code, body, exc.headers.get("Content-Type", "") if exc.headers else ""


def wait_until_200(
    url: str,
    deadline_sec: float,
    label: str,
    proc: subprocess.Popen | None = None,
) -> None:
    t0 = time.time()
    while time.time() - t0 < deadline_sec:
        if proc is not None and proc.poll() is not None:
            die(f"{label} process exited early (code={proc.returncode}) before {url} returned 200")
        status, _ = http_get(url, timeout=2.0)
        if status == 200:
            info(f"{label} ready after {time.time() - t0:.1f}s")
            return
        time.sleep(0.5)
    die(f"{label} not ready within {deadline_sec:.0f}s ({url})")


@contextmanager
def spawn_exe(exe: Path, env: dict[str, str], label: str):
    # Redirect to a file rather than PIPE so the child never blocks on a
    # full stdout buffer while we're busy polling its HTTP endpoints. On
    # failure the caller can read the log for context.
    log_path = REPO / "dist" / f"smoke-{label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    info(f"spawning {label}: {exe}  (stdout -> {log_path.name})")
    log_fh = open(log_path, "wb")
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
    )
    try:
        yield proc
    finally:
        info(f"stopping {label} (pid={proc.pid})")
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait(timeout=5)
        log_fh.close()
        # If the child died early, surface the tail of its log — otherwise
        # debugging "not ready within 120s" is impossible from CI output.
        if proc.returncode not in (0, None) and log_path.exists():
            tail = log_path.read_bytes()[-2000:].decode("utf-8", errors="replace")
            info(f"--- tail of {log_path.name} (exit={proc.returncode}) ---")
            for line in tail.splitlines()[-30:]:
                info(line)
            info("--- end tail ---")


# --------------------------------------------------------------------------
# Build steps
# --------------------------------------------------------------------------


def preflight() -> None:
    step("preflight")
    if sys.version_info < (3, 12):
        die(f"Python 3.12+ required, found {sys.version_info.major}.{sys.version_info.minor}")
    for path in (TTS_DIR, STT_DIR, TR_DIR, GW_DIR, BUNDLE_ASSETS):
        if not path.exists():
            die(f"missing required path: {path}")
    for must in (
        "start.bat",
        "README-for-students.txt",
        "LICENSE-THIRD-PARTY.txt",
        "EXTENSION-README.txt",
    ):
        if not (BUNDLE_ASSETS / must).exists():
            die(f"missing bundle asset: {BUNDLE_ASSETS / must}")
    tools = BUNDLE_ASSETS / "tools"
    for must in ("portcheck.ps1", "wait-ready.ps1", "prewarm.ps1", "open-browser.ps1"):
        if not (tools / must).exists():
            die(f"missing bundle asset: {tools / must}")
    free_gb = shutil.disk_usage(REPO).free / (1024**3)
    info(f"Python {sys.version.split()[0]}  |  free disk {free_gb:.1f} GB")
    if free_gb < 3.0:
        die(f"need at least 3 GB free, have {free_gb:.1f} GB")


def build_widget_bundle() -> None:
    # Inline the Noto Sans Oriya woff2 base64 into apps/widget/dist/widget.js
    # so the judge-laptop bundle renders Odia conjuncts correctly even on
    # Windows machines that lack Noto Sans Oriya. Runs before the gateway
    # exe is packaged so PyInstaller picks up the generated file.
    step("build widget (inline Noto Sans Oriya)")
    script = REPO / "scripts" / "build_widget.py"
    if not script.is_file():
        die(f"missing: {script}")
    run([sys.executable, str(script)], cwd=REPO)


def build_extension() -> Path:
    """Refresh apps/extension/ with the latest widget.js + icons, then zip
    it into dist/ as AaaS-Extension.zip. Returns the zip path.

    The extension is a Chromium MV3 sideload that injects the widget into
    any page the user visits, so the AaaS features work on arbitrary
    third-party sites (not just the bundled demo portals).
    """
    step("build browser extension (MV3)")
    if not EXT_DIR.is_dir():
        die(f"missing: {EXT_DIR}")

    # Refresh the widget.js copy inside the extension to match dist/.
    src_widget = REPO / "apps" / "widget" / "dist" / "widget.js"
    if not src_widget.is_file():
        die(f"missing built widget: {src_widget} — run build_widget.py first")
    dst_widget = EXT_DIR / "widget.js"
    shutil.copy2(src_widget, dst_widget)
    info(f"copied widget.js -> {dst_widget} ({dst_widget.stat().st_size:,} bytes)")

    # Regenerate icons (idempotent — tries Pillow + Odia font, falls back
    # to stdlib-only geometric PNGs).
    icons_script = REPO / "scripts" / "build_extension_icons.py"
    if icons_script.is_file():
        run([sys.executable, str(icons_script)], cwd=REPO)
    else:
        info(f"skipping icon regen — {icons_script} not present")

    # Refresh vendored transformers.js + ort-web glue. Hard-fails on
    # network problems because the zip shape depends on these files
    # being present under vendor/ when the on-device toggle is used.
    vendor_script = REPO / "scripts" / "build_extension_vendor.py"
    if vendor_script.is_file():
        run([sys.executable, str(vendor_script)], cwd=REPO)
    else:
        info(f"skipping vendor step — {vendor_script} not present")

    # Refresh ONNX model weights for on-device TTS/STT. Soft-fails:
    # huggingface-hub / optimum / torch may not be installed in the
    # orchestrator's base env, and we still want a shippable extension
    # zip for gateway-only demos. If this step returns non-zero, the
    # popup's On-device toggle will silently fall back to the gateway.
    models_script = REPO / "scripts" / "build_extension_models.py"
    if models_script.is_file():
        info("refreshing on-device ONNX models (first run: 3-10 min)")
        info(f"$ {sys.executable} {models_script}")
        proc = subprocess.run(
            [sys.executable, str(models_script)], cwd=str(REPO)
        )
        if proc.returncode != 0:
            info(
                f"WARNING: models step exited {proc.returncode} — "
                "extension will still ship, but On-device mode will "
                "fall back to gateway until deps are installed "
                "(pip install huggingface-hub optimum[onnxruntime] torch)."
            )
    else:
        info(f"skipping models step — {models_script} not present")

    # Sanity: every file the manifest references must exist.
    # vendor/ and models/ are NOT required here — their absence just
    # means the On-device toggle is non-functional, not that the
    # gateway-path extension is broken.
    for must in (
        "manifest.json",
        "background.js",
        "inject-config.js",
        "widget.js",
        "ondevice.js",
        "popup.html",
        "popup.css",
        "popup.js",
        "icons/icon-16.png",
        "icons/icon-32.png",
        "icons/icon-48.png",
        "icons/icon-128.png",
    ):
        if not (EXT_DIR / must).is_file():
            die(f"extension asset missing: {EXT_DIR / must}")

    # Zip the extension folder for distribution (judges can sideload
    # either the folder or the zip).
    import zipfile

    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_ROOT / "AaaS-Extension.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(EXT_DIR.rglob("*")):
            if p.is_dir():
                continue
            # Skip accidental junk that might exist in a dev tree.
            if any(
                part in _BLOCKLIST_NAMES or part.endswith(".env")
                for part in p.parts
            ):
                continue
            zf.write(p, p.relative_to(EXT_DIR).as_posix())
    info(f"extension zip: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


def _pyinstaller_out(service: Path, name: str) -> tuple[Path, Path]:
    """Return (distpath, workpath) for a given build. We use a per-run
    timestamp in the path so Windows Defender / file-watcher locks from
    a previous build never block a retry. The old dirs linger until the
    OS releases the lock — harmless, gitignored."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dist = service / "dist" / f"{name}-{stamp}"
    work = service / "build" / f"{name}-{stamp}"
    return dist, work


def build_tts(clean: bool) -> Path:
    step("build TTS bundle")
    py = ensure_venv(TTS_DIR, clean)
    pip_install_editable(py, TTS_DIR, extras=["dev", "bundle"])

    prefetch = TTS_DIR / "bundle" / "prefetch_model.py"
    # Always run prefetch — it's idempotent (the HF cache handles
    # re-downloads). Needed because Phase A pulls three checkpoints
    # (Odia + Hindi + English); the old "skip if ANY weights exist"
    # check would wrongly skip Hindi/English once Odia was cached.
    info("running prefetch for or/hi/en (needs network on cold cache, ~450 MB total)")
    run([str(py), str(prefetch)], cwd=TTS_DIR)

    distpath, workpath = _pyinstaller_out(TTS_DIR, "aaas-tts")
    info(f"output: dist={distpath}  work={workpath}")
    run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(distpath),
            "--workpath",
            str(workpath),
            "bundle/aaas_tts.spec",
        ],
        cwd=TTS_DIR,
    )
    exe = distpath / "aaas-tts" / "aaas-tts.exe"
    if not exe.exists():
        die(f"pyinstaller did not produce {exe}")
    info(f"tts exe: {exe}")
    return exe


def build_stt(clean: bool) -> Path:
    step("build STT bundle (mock engine)")
    py = ensure_venv(STT_DIR, clean)
    pip_install_editable(py, STT_DIR, extras=["dev", "bundle"])
    distpath, workpath = _pyinstaller_out(STT_DIR, "aaas-stt")
    info(f"output: dist={distpath}  work={workpath}")
    run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(distpath),
            "--workpath",
            str(workpath),
            "bundle/aaas_stt.spec",
        ],
        cwd=STT_DIR,
    )
    exe = distpath / "aaas-stt" / "aaas-stt.exe"
    if not exe.exists():
        die(f"pyinstaller did not produce {exe}")
    info(f"stt exe: {exe}")
    return exe


def build_translate(clean: bool) -> Path:
    step("build Translate bundle (mock MT engine, real Tesseract OCR)")
    py = ensure_venv(TR_DIR, clean)
    pip_install_editable(py, TR_DIR, extras=["dev", "bundle", "ocr"])

    # Traineddata for ori/hin/eng — idempotent, ~15 MB total. Without
    # this the bundled /ocr silently degrades to the mock engine.
    prefetch = TR_DIR / "bundle" / "prefetch_tessdata.py"
    if prefetch.is_file():
        run([str(py), str(prefetch)], cwd=TR_DIR)
    else:
        info(f"WARNING: {prefetch} missing — bundled OCR will be mock")

    distpath, workpath = _pyinstaller_out(TR_DIR, "aaas-translate")
    info(f"output: dist={distpath}  work={workpath}")
    run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(distpath),
            "--workpath",
            str(workpath),
            "bundle/aaas_translate.spec",
        ],
        cwd=TR_DIR,
    )
    exe = distpath / "aaas-translate" / "aaas-translate.exe"
    if not exe.exists():
        die(f"pyinstaller did not produce {exe}")
    info(f"translate exe: {exe}")
    return exe


def build_gateway(clean: bool) -> Path:
    step("build Gateway bundle")
    py = ensure_venv(GW_DIR, clean)
    pip_install_editable(py, GW_DIR, extras=["dev", "bundle"])
    distpath, workpath = _pyinstaller_out(GW_DIR, "aaas-gateway")
    info(f"output: dist={distpath}  work={workpath}")
    run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(distpath),
            "--workpath",
            str(workpath),
            "bundle/aaas_gateway.spec",
        ],
        cwd=GW_DIR,
    )
    exe = distpath / "aaas-gateway" / "aaas-gateway.exe"
    if not exe.exists():
        die(f"pyinstaller did not produce {exe}")
    info(f"gateway exe: {exe}")
    return exe


def smoke_tts(exe: Path) -> None:
    step("smoke-test TTS exe in isolation")
    env = os.environ.copy()
    env.update({"TTS_HOST": "127.0.0.1", "TTS_PORT": "8011"})
    with spawn_exe(exe, env, "tts-smoke") as tts_proc:
        wait_until_200("http://127.0.0.1:8011/readyz", 120.0, "tts /readyz", tts_proc)
        # Real synthesis round-trip.
        status, body, ctype = http_post_json(
            "http://127.0.0.1:8011/synthesise", {"text": "ନମସ୍କାର"}, timeout=120.0
        )
        if status != 200:
            die(f"tts synth HTTP {status}: {body[:200].decode('utf-8', errors='replace')}")
        if "audio/wav" not in ctype.lower() or len(body) < 10_000:
            die(f"tts synth returned {len(body)} bytes ctype={ctype!r} — expected >=10KB wav")
        info(f"tts synth OK — {len(body)} bytes of audio/wav")


def smoke_stt(exe: Path) -> None:
    step("smoke-test STT exe in isolation")
    env = os.environ.copy()
    env.update({"STT_HOST": "127.0.0.1", "STT_PORT": "8013"})
    with spawn_exe(exe, env, "stt-smoke") as proc:
        wait_until_200("http://127.0.0.1:8013/readyz", 30.0, "stt /readyz", proc)
        # Mock transcribe round-trip — tiny bogus WAV frame is enough;
        # the mock engine hashes bytes to pick a canned phrase.
        import io
        import json
        import urllib.request

        payload = (
            b"--boundary\r\nContent-Disposition: form-data; name=\"audio\"; "
            b"filename=\"x.wav\"\r\nContent-Type: audio/wav\r\n\r\n"
            + b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 16
            + b"\r\n--boundary\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\nor"
            + b"\r\n--boundary--\r\n"
        )
        req = urllib.request.Request(
            "http://127.0.0.1:8013/transcribe",
            data=payload,
            method="POST",
            headers={"Content-Type": "multipart/form-data; boundary=boundary"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                body = resp.read()
                status = resp.status
        except Exception as exc:  # noqa: BLE001
            die(f"stt /transcribe request failed: {exc!s}")
        if status != 200:
            die(f"stt /transcribe HTTP {status}: {body[:200]!r}")
        try:
            obj = json.loads(body)
        except Exception as exc:  # noqa: BLE001
            die(f"stt /transcribe not JSON: {exc!s}")
        if not obj.get("text") or obj.get("engine") != "mock":
            die(f"stt /transcribe unexpected body: {obj!r}")
        info(f"stt /transcribe OK — engine={obj['engine']} lang={obj.get('language')}")


def smoke_translate(exe: Path) -> None:
    step("smoke-test Translate exe in isolation")
    env = os.environ.copy()
    env.update({"TRANSLATE_HOST": "127.0.0.1", "TRANSLATE_PORT": "8014"})
    with spawn_exe(exe, env, "translate-smoke") as proc:
        wait_until_200(
            "http://127.0.0.1:8014/readyz", 30.0, "translate /readyz", proc
        )
        status, body, _ = http_post_json(
            "http://127.0.0.1:8014/translate",
            {"text": "ନମସ୍କାର", "src_lang": "or", "tgt_lang": "en"},
            timeout=10.0,
        )
        if status != 200:
            die(
                f"translate HTTP {status}: {body[:200].decode('utf-8', errors='replace')}"
            )
        import json as _json

        try:
            obj = _json.loads(body)
        except Exception as exc:  # noqa: BLE001
            die(f"translate not JSON: {exc!s}")
        if not obj.get("text") or obj.get("tgt_lang") != "en":
            die(f"translate unexpected body: {obj!r}")
        info(f"translate OK — engine={obj.get('engine')} text={obj['text']!r}")


def smoke_gateway(exe: Path, tts_exe: Path) -> None:
    step("smoke-test Gateway exe (with real TTS upstream)")
    env_tts = os.environ.copy()
    env_tts.update({"TTS_HOST": "127.0.0.1", "TTS_PORT": "8012"})
    env_gw = os.environ.copy()
    env_gw.update(
        {
            "GATEWAY_HOST": "127.0.0.1",
            "GATEWAY_PORT": "8010",
            "UPSTREAM_TTS_URL": "http://127.0.0.1:8012",
        }
    )
    with spawn_exe(tts_exe, env_tts, "tts-for-gw") as tts_proc:
        wait_until_200("http://127.0.0.1:8012/readyz", 120.0, "tts /readyz", tts_proc)
        with spawn_exe(exe, env_gw, "gateway-smoke") as gw_proc:
            wait_until_200("http://127.0.0.1:8010/healthz", 30.0, "gateway /healthz", gw_proc)

            status, body = http_get("http://127.0.0.1:8010/widget.js", timeout=5.0)
            if status != 200 or b"aaas" not in body.lower():
                die(f"gateway /widget.js broken: HTTP {status}, {len(body)} bytes")
            info(f"gateway /widget.js OK — {len(body)} bytes")

            status, body = http_get(
                "http://127.0.0.1:8010/demo/jajpur-collectorate/", timeout=5.0
            )
            if status != 200:
                die(f"gateway demo page HTTP {status}")
            if b"Jajpur" not in body and b"jajpur" not in body.lower():
                die("gateway demo page body missing the word Jajpur")
            info(f"gateway demo page OK — {len(body)} bytes")

            status, body, ctype = http_post_json(
                "http://127.0.0.1:8010/tts/synthesise",
                {"text": "ନମସ୍କାର"},
                headers={"X-API-Key": SEED_API_KEY},
                timeout=120.0,
            )
            if status != 200:
                die(
                    f"gateway synth HTTP {status}: "
                    f"{body[:300].decode('utf-8', errors='replace')}"
                )
            if "audio/wav" not in ctype.lower() or len(body) < 10_000:
                die(f"gateway synth returned {len(body)} bytes ctype={ctype!r}")
            info(f"gateway synth round-trip OK — {len(body)} bytes")


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

_BLOCKLIST_NAMES = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".git",
    ".DS_Store",
    "out-through-gateway.wav",
}


def _ignore(src: str, names: list[str]) -> list[str]:
    return [n for n in names if n in _BLOCKLIST_NAMES or n.endswith(".env")]


def _empty_directory(path: Path, attempts: int = 8) -> None:
    # Delete everything INSIDE `path` but leave the directory itself in place.
    # Windows frequently keeps a handle on a recently-emptied directory
    # (Defender real-time scan, a prior process's cwd handle, Explorer
    # thumbnails) for several seconds, so rmtree/rmdir on the parent fails
    # with WinError 32 even when the directory is otherwise free. Working
    # IN-PLACE sidesteps that entirely — we never need to delete the parent.
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            for i in range(attempts):
                try:
                    shutil.rmtree(child)
                    break
                except PermissionError as exc:
                    if i == attempts - 1:
                        raise
                    info(
                        f"rmtree {child.name} retry {i + 1}/{attempts} "
                        f"after PermissionError: {exc.winerror}"
                    )
                    time.sleep(1.0 + i * 0.5)
                except FileNotFoundError:
                    break
        else:
            for i in range(attempts):
                try:
                    child.unlink()
                    break
                except PermissionError as exc:
                    if i == attempts - 1:
                        raise
                    info(
                        f"unlink {child.name} retry {i + 1}/{attempts} "
                        f"after PermissionError: {exc.winerror}"
                    )
                    time.sleep(1.0 + i * 0.5)
                except FileNotFoundError:
                    break


def assemble(
    tts_exe: Path, stt_exe: Path, translate_exe: Path, gw_exe: Path
) -> None:
    step("assemble dist/AaaS-Demo/")
    if BUNDLE_OUT.exists():
        info(f"emptying previous bundle at {BUNDLE_OUT}")
        _empty_directory(BUNDLE_OUT)
    else:
        BUNDLE_OUT.mkdir(parents=True)
    (BUNDLE_OUT / "logs").mkdir()
    (BUNDLE_OUT / "services").mkdir()

    src_and_dst = [
        (tts_exe.parent, BUNDLE_OUT / "services" / "aaas-tts"),
        (stt_exe.parent, BUNDLE_OUT / "services" / "aaas-stt"),
        (translate_exe.parent, BUNDLE_OUT / "services" / "aaas-translate"),
        (gw_exe.parent, BUNDLE_OUT / "services" / "aaas-gateway"),
    ]
    for src, dst in src_and_dst:
        info(f"copy {src}  ->  {dst}")
        shutil.copytree(src, dst, ignore=_ignore)

    # Top-level static assets.
    for fname in ("start.bat", "README-for-students.txt", "LICENSE-THIRD-PARTY.txt"):
        shutil.copy2(BUNDLE_ASSETS / fname, BUNDLE_OUT / fname)
    shutil.copytree(BUNDLE_ASSETS / "tools", BUNDLE_OUT / "tools")

    # Real OCR on the judge laptop: ship the ori/hin/eng traineddata
    # next to the translate exe, plus a minimal Tesseract runtime
    # (tesseract.exe + DLLs — no training tools or docs). Both start.bat
    # and the bundle smoke point AAAS_TRANSLATE_* env vars at these.
    tessdata_src = TR_DIR / "models" / "tessdata"
    if tessdata_src.is_dir():
        tessdata_dst = BUNDLE_OUT / "services" / "aaas-translate" / "models" / "tessdata"
        info(f"copy {tessdata_src}  ->  {tessdata_dst}")
        shutil.copytree(tessdata_src, tessdata_dst)
    else:
        info("WARNING: no tessdata prefetched — bundled OCR will be mock")

    tess_src = Path(r"C:\Program Files\Tesseract-OCR")
    if (tess_src / "tesseract.exe").is_file():
        tess_dst = BUNDLE_OUT / "services" / "tesseract"
        tess_dst.mkdir(parents=True)
        copied = 0
        for item in tess_src.iterdir():
            if item.name == "tesseract.exe" or item.suffix.lower() == ".dll":
                shutil.copy2(item, tess_dst / item.name)
                copied += 1
        info(f"copy tesseract runtime -> {tess_dst} ({copied} files)")
    else:
        info(
            "WARNING: Tesseract not installed on this machine — bundled "
            "OCR will run as MOCK. Install UB-Mannheim Tesseract and rebuild."
        )

    # Copy the browser extension as an unpacked folder so judges can sideload
    # it directly (chrome://extensions → Load unpacked → extension/). The
    # zipped copy at dist/AaaS-Extension.zip is the shareable artefact.
    ext_dst = BUNDLE_OUT / "extension"
    info(f"copy {EXT_DIR}  ->  {ext_dst}")
    shutil.copytree(EXT_DIR, ext_dst, ignore=_ignore)
    ext_readme = BUNDLE_ASSETS / "EXTENSION-README.txt"
    if ext_readme.is_file():
        shutil.copy2(ext_readme, BUNDLE_OUT / "EXTENSION-README.txt")

    # Tripwire: nothing from the blocklist should have slipped in.
    leaked: list[Path] = []
    for root, dirs, files in os.walk(BUNDLE_OUT):
        for d in list(dirs):
            if d in _BLOCKLIST_NAMES:
                leaked.append(Path(root) / d)
        for f in files:
            if f in _BLOCKLIST_NAMES or f.endswith(".env"):
                leaked.append(Path(root) / f)
    if leaked:
        for p in leaked:
            info(f"leaked: {p}")
        die("blocklisted files inside the assembled bundle — aborting")
    info("bundle assembled cleanly")


# --------------------------------------------------------------------------
# Bundle-level smoke test (launch via the real start.bat)
# --------------------------------------------------------------------------


def _portcheck_via_ps() -> tuple[int, int, int, int]:
    """Ask the bundle's own portcheck.ps1 which ports to use."""
    script = BUNDLE_OUT / "tools" / "portcheck.ps1"
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "8020",
            "8021",
            "8022",
            "8023",
        ],
        capture_output=True,
        text=True,
    )
    gw = tts = stt = tr = 0
    for line in (proc.stdout or "").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            key = k.strip()
            val = v.strip()
            if key == "GATEWAY_PORT":
                gw = int(val)
            elif key == "TTS_PORT":
                tts = int(val)
            elif key == "STT_PORT":
                stt = int(val)
            elif key == "TRANSLATE_PORT":
                tr = int(val)
            elif key == "ERROR":
                die(f"portcheck.ps1 said: {val}")
    if not gw or not tts or not stt or not tr:
        die(f"portcheck.ps1 produced incomplete ports: stdout={proc.stdout!r}")
    return gw, tts, stt, tr


def smoke_bundle() -> None:
    step("end-to-end smoke test against the assembled bundle")
    gw_port, tts_port, stt_port, tr_port = _portcheck_via_ps()
    info(
        f"chose ports  gateway={gw_port}  tts={tts_port}  "
        f"stt={stt_port}  translate={tr_port}"
    )

    tts_exe = BUNDLE_OUT / "services" / "aaas-tts" / "aaas-tts.exe"
    stt_exe = BUNDLE_OUT / "services" / "aaas-stt" / "aaas-stt.exe"
    tr_exe = BUNDLE_OUT / "services" / "aaas-translate" / "aaas-translate.exe"
    gw_exe = BUNDLE_OUT / "services" / "aaas-gateway" / "aaas-gateway.exe"

    env_tts = os.environ.copy()
    env_tts.update({"TTS_HOST": "127.0.0.1", "TTS_PORT": str(tts_port)})
    env_stt = os.environ.copy()
    env_stt.update({"STT_HOST": "127.0.0.1", "STT_PORT": str(stt_port)})
    env_tr = os.environ.copy()
    env_tr.update({"TRANSLATE_HOST": "127.0.0.1", "TRANSLATE_PORT": str(tr_port)})
    # Point OCR at the bundled Tesseract runtime + traineddata, exactly
    # as start.bat does on the judge laptop.
    bundled_tess = BUNDLE_OUT / "services" / "tesseract" / "tesseract.exe"
    bundled_tessdata = (
        BUNDLE_OUT / "services" / "aaas-translate" / "models" / "tessdata"
    )
    if bundled_tess.is_file():
        env_tr["AAAS_TRANSLATE_TESSERACT_CMD"] = str(bundled_tess)
    if bundled_tessdata.is_dir():
        env_tr["AAAS_TRANSLATE_TESSDATA_DIR"] = str(bundled_tessdata)
    env_gw = os.environ.copy()
    env_gw.update(
        {
            "GATEWAY_HOST": "127.0.0.1",
            "GATEWAY_PORT": str(gw_port),
            "UPSTREAM_TTS_URL": f"http://127.0.0.1:{tts_port}",
            "UPSTREAM_STT_URL": f"http://127.0.0.1:{stt_port}",
            "UPSTREAM_TRANSLATE_URL": f"http://127.0.0.1:{tr_port}",
        }
    )

    with spawn_exe(tts_exe, env_tts, "bundle-tts") as tts_proc:
        wait_until_200(
            f"http://127.0.0.1:{tts_port}/readyz", 120.0, "tts /readyz", tts_proc
        )
        with spawn_exe(stt_exe, env_stt, "bundle-stt") as stt_proc:
            wait_until_200(
                f"http://127.0.0.1:{stt_port}/readyz", 30.0, "stt /readyz", stt_proc
            )
            with spawn_exe(tr_exe, env_tr, "bundle-translate") as tr_proc:
                wait_until_200(
                    f"http://127.0.0.1:{tr_port}/readyz",
                    30.0,
                    "translate /readyz",
                    tr_proc,
                )
                with spawn_exe(gw_exe, env_gw, "bundle-gw") as gw_proc:
                    wait_until_200(
                        f"http://127.0.0.1:{gw_port}/healthz",
                        30.0,
                        "gateway /healthz",
                        gw_proc,
                    )

                    status, body = http_get(
                        f"http://127.0.0.1:{gw_port}/demo/jajpur-collectorate/",
                        timeout=5.0,
                    )
                    if status != 200:
                        die(f"bundle demo page HTTP {status}")

                    status, body, ctype = http_post_json(
                        f"http://127.0.0.1:{gw_port}/tts/synthesise",
                        {"text": "ନମସ୍କାର"},
                        headers={"X-API-Key": SEED_API_KEY},
                        timeout=120.0,
                    )
                    if status != 200 or len(body) < 10_000:
                        die(
                            f"bundle synth HTTP {status} len={len(body)} ctype={ctype!r} "
                            f"body={body[:200].decode('utf-8', errors='replace')}"
                        )
                    info(f"bundle synth OK — {len(body)} bytes")

                    # Translate through the gateway.
                    status, body, _ = http_post_json(
                        f"http://127.0.0.1:{gw_port}/translate/translate",
                        {"text": "ନମସ୍କାର", "src_lang": "or", "tgt_lang": "en"},
                        headers={"X-API-Key": SEED_API_KEY},
                        timeout=10.0,
                    )
                    if status != 200:
                        info(
                            f"WARNING: /translate/translate HTTP {status} "
                            f"— gateway may not proxy this path yet."
                        )
                    else:
                        info("bundle translate round-trip OK")

                    # OCR through the gateway with a real scan — the whole
                    # point of shipping Tesseract. Expect engine=tesseract
                    # when the runtime was bundled; warn (don't fail) when
                    # the build machine had no Tesseract install.
                    scan = (
                        REPO / "apps" / "demo-sites" / "jajpur-collectorate"
                        / "assets" / "notice-scan.png"
                    )
                    if scan.is_file():
                        import json as _json2

                        boundary = b"aaasocr"
                        payload = (
                            b"--" + boundary + b"\r\n"
                            b'Content-Disposition: form-data; name="file"; '
                            b'filename="notice-scan.png"\r\n'
                            b"Content-Type: image/png\r\n\r\n"
                            + scan.read_bytes()
                            + b"\r\n--" + boundary + b"\r\n"
                            b'Content-Disposition: form-data; name="lang"\r\n\r\nen'
                            b"\r\n--" + boundary + b"--\r\n"
                        )
                        req = urllib.request.Request(
                            f"http://127.0.0.1:{gw_port}/translate/ocr",
                            data=payload,
                            method="POST",
                            headers={
                                "Content-Type": (
                                    "multipart/form-data; boundary=aaasocr"
                                ),
                                "X-API-Key": SEED_API_KEY,
                            },
                        )
                        try:
                            with urllib.request.urlopen(req, timeout=120.0) as resp:
                                ocr_body = resp.read()
                                ocr_status = resp.status
                        except urllib.error.HTTPError as exc:
                            ocr_body = exc.read() if exc.fp else b""
                            ocr_status = exc.code
                        if ocr_status != 200:
                            die(f"bundle OCR HTTP {ocr_status}: {ocr_body[:200]!r}")
                        ocr_obj = _json2.loads(ocr_body)
                        if ocr_obj.get("engine") == "tesseract":
                            if "hereby" not in (ocr_obj.get("text") or "").lower():
                                die(
                                    "bundle OCR ran tesseract but text missed "
                                    f"'hereby': {ocr_obj.get('text', '')[:120]!r}"
                                )
                            info("bundle OCR round-trip OK — engine=tesseract")
                        else:
                            info(
                                "WARNING: bundle OCR is running the MOCK engine "
                                "— Read document will return canned text on the "
                                "judge laptop."
                            )
                    else:
                        info(f"skipping OCR smoke — {scan} not found")

                    # Negative path: English text against the default Odia
                    # model must 4xx cleanly (the MMS Odia tokeniser drops
                    # Latin input), so the widget shows a TTS error rather
                    # than playing 0 bytes of "audio".
                    status, body, _ = http_post_json(
                        f"http://127.0.0.1:{gw_port}/tts/synthesise",
                        {"text": "Hello"},
                        headers={"X-API-Key": SEED_API_KEY},
                        timeout=30.0,
                    )
                    if 200 <= status < 300:
                        info(
                            "WARNING: English text returned 2xx against the default Odia "
                            "model — the tokeniser guard is not firing."
                        )
                    else:
                        info(
                            f"negative path OK — English text returned HTTP {status} as expected"
                        )


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += (Path(root) / f).stat().st_size
    return total


def report() -> None:
    step("bundle ready")
    size_bytes = _tree_size(BUNDLE_OUT)
    size_gb = size_bytes / (1024**3)
    exes = [
        ("aaas-tts", BUNDLE_OUT / "services" / "aaas-tts" / "aaas-tts.exe"),
        ("aaas-stt", BUNDLE_OUT / "services" / "aaas-stt" / "aaas-stt.exe"),
        (
            "aaas-translate",
            BUNDLE_OUT / "services" / "aaas-translate" / "aaas-translate.exe",
        ),
        ("aaas-gateway", BUNDLE_OUT / "services" / "aaas-gateway" / "aaas-gateway.exe"),
    ]
    hashes = [(name, _sha256(path), path) for name, path in exes]
    sha_file = DIST_ROOT / "AaaS-Demo.sha256"
    sha_file.write_text(
        "".join(
            f"{digest}  services/{name}/{path.name}\n"
            for name, digest, path in hashes
        ),
        encoding="utf-8",
    )
    info(f"bundle path : {BUNDLE_OUT}")
    info(f"bundle size : {size_gb:.2f} GB  ({size_bytes:,} bytes)")
    for name, digest, _ in hashes:
        info(f"{name:15s}: sha256 {digest}")
    info(f"hashes      : {sha_file}")
    ext_zip = DIST_ROOT / "AaaS-Extension.zip"
    if ext_zip.exists():
        info(f"extension   : {ext_zip} ({ext_zip.stat().st_size:,} bytes)")
    print()
    print("Next steps:")
    print("  1. Double-click  dist\\AaaS-Demo\\start.bat  on this machine to verify.")
    print("  2. Sideload the browser extension:")
    print("       chrome://extensions  ->  Developer mode ON  ->  Load unpacked")
    print("       select  dist\\AaaS-Demo\\extension\\")
    print("  3. Visit any website — click the ଅ button for read-aloud / dictation.")
    print("  4. Copy the AaaS-Demo folder onto the USB stick (not a zip).")
    print("  5. Rehearse on a clean Windows laptop before the judging window.")


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------


def main() -> int:
    # Windows default stdout encoding (cp1252) can't handle Odia / Devanagari
    # text that lands in our smoke-test log lines. Force UTF-8 with replacement
    # fallback so the build never crashes on its own success logging.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--clean", action="store_true", help="rebuild venvs and dist from scratch")
    ap.add_argument("--skip-tts", action="store_true", help="reuse existing services/tts/dist")
    ap.add_argument(
        "--skip-stt", action="store_true", help="reuse existing services/stt/dist"
    )
    ap.add_argument(
        "--skip-translate",
        action="store_true",
        help="reuse existing services/translate/dist",
    )
    ap.add_argument("--skip-gw", action="store_true", help="reuse existing services/gateway/dist")
    ap.add_argument("--no-smoke", action="store_true", help="skip post-build smoke tests")
    ap.add_argument(
        "--no-bundle-smoke",
        action="store_true",
        help="skip the final end-to-end run of the assembled bundle",
    )
    args = ap.parse_args()

    preflight()
    build_widget_bundle()
    build_extension()

    def _latest_exe(service: Path, name: str) -> Path | None:
        # Prefer a stamped build (dist/<name>-YYYYMMDD-HHMMSS/<name>/<name>.exe),
        # fall back to the legacy unstamped layout (dist/<name>/<name>.exe).
        candidates = sorted(
            (service / "dist").glob(f"{name}-*/{name}/{name}.exe"), reverse=True
        )
        if candidates:
            return candidates[0]
        legacy = service / "dist" / name / f"{name}.exe"
        return legacy if legacy.exists() else None

    if args.skip_tts:
        step("skip-tts: reusing existing TTS build")
        tts_exe = _latest_exe(TTS_DIR, "aaas-tts")
        if tts_exe is None:
            die("--skip-tts requested but no existing tts exe was found under services/tts/dist/")
        info(f"reusing {tts_exe}")
    else:
        tts_exe = build_tts(args.clean)
        if not args.no_smoke:
            smoke_tts(tts_exe)

    if args.skip_stt:
        step("skip-stt: reusing existing STT build")
        stt_exe = _latest_exe(STT_DIR, "aaas-stt")
        if stt_exe is None:
            die("--skip-stt requested but no existing stt exe was found under services/stt/dist/")
        info(f"reusing {stt_exe}")
    else:
        stt_exe = build_stt(args.clean)
        if not args.no_smoke:
            smoke_stt(stt_exe)

    if args.skip_translate:
        step("skip-translate: reusing existing Translate build")
        translate_exe = _latest_exe(TR_DIR, "aaas-translate")
        if translate_exe is None:
            die(
                "--skip-translate requested but no existing translate exe was "
                "found under services/translate/dist/"
            )
        info(f"reusing {translate_exe}")
    else:
        translate_exe = build_translate(args.clean)
        if not args.no_smoke:
            smoke_translate(translate_exe)

    if args.skip_gw:
        step("skip-gw: reusing existing Gateway build")
        gw_exe = _latest_exe(GW_DIR, "aaas-gateway")
        if gw_exe is None:
            die("--skip-gw requested but no existing gateway exe was found under services/gateway/dist/")
        info(f"reusing {gw_exe}")
    else:
        gw_exe = build_gateway(args.clean)
        if not args.no_smoke:
            smoke_gateway(gw_exe, tts_exe)

    assemble(tts_exe, stt_exe, translate_exe, gw_exe)

    if not args.no_bundle_smoke:
        smoke_bundle()
    else:
        step("skipping end-to-end bundle smoke (--no-bundle-smoke)")
        info("BUNDLE UNVERIFIED — do not ship without running start.bat manually.")

    report()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        sys.exit(130)
