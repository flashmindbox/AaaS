"""Verify + auto-heal the AaaS portable install.

Called as the final step of ``SETUP-FRIEND.bat`` and re-runnable via
``ENSURE-READY.bat``. For each expected HuggingFace model:

  * If the cache is complete, skip.
  * If missing / partial and the model is not gated (MMS-TTS),
    download it with ``huggingface_hub.snapshot_download``.
  * If gated (ai4bharat/indicwav2vec-odia, ai4bharat/indictrans2-*)
    and HF_TOKEN is set, same.
  * If gated and no HF_TOKEN, write the service's graceful-fallback
    engine into its .env (STT -> mock, translate -> google) so the
    demo still boots.

Exit code 0 means "the demo will boot cleanly" — either with real
engines or with mock fallbacks that we've explicitly wired up. Exit
code 1 means something unrecoverable (e.g. widget.js is missing and
can't be re-created from nothing).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each entry: HF repo id, local cache dir, required filenames inside
# the snapshot, and whether the repo is gated (affects retry behaviour).
MODELS = [
    {
        "id": "facebook/mms-tts-ory",
        "cache": ROOT / "services" / "tts" / "models",
        "files": ["config.json", "tokenizer_config.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": False,
        "label": "MMS-TTS Odia",
    },
    {
        "id": "facebook/mms-tts-hin",
        "cache": ROOT / "services" / "tts" / "models",
        "files": ["config.json", "tokenizer_config.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": False,
        "label": "MMS-TTS Hindi",
    },
    {
        "id": "facebook/mms-tts-eng",
        "cache": ROOT / "services" / "tts" / "models",
        "files": ["config.json", "tokenizer_config.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": False,
        "label": "MMS-TTS English",
    },
    {
        "id": "ai4bharat/indictrans2-en-indic-dist-200M",
        "cache": ROOT / "services" / "translate" / "models",
        "files": ["config.json", "dict.SRC.json", "dict.TGT.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": True,  # "auto"-gated: any logged-in HF account may download
        "label": "IndicTrans2 en->indic (200M)",
        "fallback_env": ("translate", "AAAS_TRANSLATE_ENGINE=google"),
        "fallback_note": (
            "Translate configured for the google engine (free web endpoint,\n"
            "         needs internet; offline it serves the curated mock corpus).\n"
            "         For offline IndicTrans2: set HF_TOKEN to any huggingface.co\n"
            "         token, re-run ENSURE-READY.bat, then restore\n"
            "         AAAS_TRANSLATE_ENGINE=indictrans2 in services\\translate\\.env."
        ),
    },
    {
        "id": "ai4bharat/indictrans2-indic-en-dist-200M",
        "cache": ROOT / "services" / "translate" / "models",
        "files": ["config.json", "dict.SRC.json", "dict.TGT.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": True,
        "label": "IndicTrans2 indic->en (200M)",
        "fallback_env": ("translate", "AAAS_TRANSLATE_ENGINE=google"),
        "fallback_note": (
            "Translate configured for the google engine (see note above)."
        ),
    },
    {
        "id": "ai4bharat/indicwav2vec-odia",
        "cache": ROOT / "services" / "stt" / "models",
        "files": ["config.json", "preprocessor_config.json"],
        "weight_files": ["model.safetensors", "pytorch_model.bin"],
        "gated": True,
        "label": "IndicWav2Vec Odia",
        "fallback_env": ("stt", "AAAS_STT_ENGINE=mock"),
        "fallback_note": (
            "STT configured for mock engine.\n"
            "         Real Odia transcription requires: (1) huggingface.co account,\n"
            "         (2) access grant at huggingface.co/ai4bharat/indicwav2vec-odia,\n"
            "         (3) HF_TOKEN env var set to your token, then re-run ENSURE-READY.bat."
        ),
    },
]

WIDGET_FILES = [
    ROOT / "apps" / "widget" / "dist" / "widget.js",
    ROOT / "apps" / "extension" / "widget.js",
]


def _find_snapshot(cache_dir: Path, repo_id: str) -> Path | None:
    """Return the canonical snapshot dir for ``repo_id``.

    Prefers the commit that ``refs/main`` points at — that's the one
    transformers actually loads. Falls back to the newest snapshot
    directory if refs/main is absent or stale.
    """
    org, name = repo_id.split("/", 1)
    hub_dir = cache_dir / f"models--{org}--{name}"
    snapshots_dir = hub_dir / "snapshots"
    if not snapshots_dir.is_dir():
        return None
    # Preferred: follow refs/main (file containing the commit hash).
    ref_main = hub_dir / "refs" / "main"
    if ref_main.is_file():
        commit = ref_main.read_text(encoding="utf-8").strip()
        candidate = snapshots_dir / commit
        if candidate.is_dir():
            return candidate
    snaps = [p for p in snapshots_dir.iterdir() if p.is_dir()]
    if not snaps:
        return None
    return max(snaps, key=lambda p: p.stat().st_mtime)


def _resolve(p: Path) -> Path:
    """Follow a symlink one level; HF cache uses symlinks on Unix/macOS."""
    try:
        if p.is_symlink():
            return p.resolve()
    except OSError:
        pass
    return p


def check_model(model: dict) -> tuple[bool, str]:
    """Return (ok, reason). Fast: existence + non-zero size on key files."""
    snap = _find_snapshot(model["cache"], model["id"])
    if snap is None:
        return False, "cache directory / snapshot missing"
    for name in model["files"]:
        f = _resolve(snap / name)
        if not f.is_file() or f.stat().st_size < 10:
            return False, f"missing or truncated: {name}"
    # At least one weight file must be present.
    weight_ok = False
    for name in model["weight_files"]:
        f = _resolve(snap / name)
        if f.is_file() and f.stat().st_size > 1_000_000:  # >1 MB; weights are huge
            weight_ok = True
            break
    if not weight_ok:
        return False, "no usable weight file"
    return True, "ok"


def download_model(model: dict, token: str | None) -> tuple[bool, str]:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return False, "huggingface_hub not installed — run SETUP-FRIEND.bat first"
    kwargs = {
        "repo_id": model["id"],
        "cache_dir": str(model["cache"]),
    }
    if model["gated"] and token:
        kwargs["token"] = token
    try:
        snapshot_download(**kwargs)
        return True, "downloaded"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def apply_fallback(model: dict) -> None:
    """Point the owning service at its graceful-fallback engine."""
    service, line = model["fallback_env"]
    write_env_line(ROOT / "services" / service / ".env", line)


def write_env_line(env_path: Path, line: str) -> None:
    """Append-or-replace an ``AAAS_X=value`` line in the .env file."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    key = line.split("=", 1)[0]
    existing: list[str] = []
    if env_path.is_file():
        existing = env_path.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in existing if not ln.startswith(f"{key}=")]
    kept.append(line)
    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main() -> int:
    print("=" * 58)
    print(" AaaS readiness check")
    print("=" * 58)
    t0 = time.time()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        print(f"[info] HF_TOKEN detected (...{token[-6:]}).")
    else:
        print(
            "[info] HF_TOKEN not set — gated models (IndicWav2Vec, IndicTrans2)"
            " use graceful fallbacks if their bundled weights are missing."
        )
    print()

    healed: list[str] = []
    fallbacks: list[str] = []
    critical_missing: list[str] = []

    # Models
    for model in MODELS:
        ok, reason = check_model(model)
        if ok:
            print(f"  [OK]   {model['label']}")
            continue

        print(f"  [MISS] {model['label']} — {reason}")
        if model["gated"] and not token:
            # Skip download attempt; fall straight through to the
            # service's graceful-fallback engine.
            apply_fallback(model)
            print(f"         No HF_TOKEN set — {model['fallback_note']}")
            fallbacks.append(model["label"])
            continue

        print(f"         Attempting download (this may take a few minutes)...")
        ok, msg = download_model(model, token=token)
        if ok:
            print(f"  [HEAL] {model['label']} downloaded OK")
            healed.append(model["label"])
        elif model["gated"]:
            # Gated and token didn't work (no access grant, revoked, etc.)
            apply_fallback(model)
            print(
                f"  [FALLBACK] {model['label']} unavailable: {msg}\n"
                f"         {model['fallback_note']}\n"
                f"         Ensure you've clicked 'Agree and access repository' at\n"
                f"         huggingface.co/{model['id']} then re-run ENSURE-READY.bat."
            )
            fallbacks.append(model["label"])
        else:
            print(
                f"  [FAIL] {model['label']} could not be downloaded: {msg}\n"
                f"         Check your internet connection and re-run ENSURE-READY.bat."
            )
            critical_missing.append(model["label"])

    # Widget.js — can't self-heal, but we can surface the problem.
    print()
    for wp in WIDGET_FILES:
        if wp.is_file() and wp.stat().st_size > 100_000:
            print(f"  [OK]   {wp.relative_to(ROOT).as_posix()}")
        else:
            print(f"  [FAIL] {wp.relative_to(ROOT).as_posix()} missing or truncated")
            print("         Re-extract the AaaS update zip — widget.js is a static file.")
            critical_missing.append(wp.relative_to(ROOT).as_posix())

    # Summary
    print()
    print("-" * 58)
    elapsed = int(time.time() - t0)
    if critical_missing:
        print(f" FAILED — {len(critical_missing)} unrecoverable issue(s) in {elapsed}s.")
        print(f"   Do not run RUN-DEMO.bat until these are resolved:")
        for m in critical_missing:
            print(f"     * {m}")
        return 1
    if healed:
        print(f" {len(healed)} model(s) auto-downloaded in {elapsed}s.")
    if fallbacks:
        print(f" {len(fallbacks)} model(s) using mock fallback (demo still works).")
    print(f" READY — safe to run RUN-DEMO.bat.")
    print("-" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
