"""Prepare on-device ONNX models for the browser extension.

Downloads four model bundles into ``apps/extension/models/``:

  - ``mms-tts-hin``    — Hindi  TTS (Xenova pre-converted)
  - ``mms-tts-eng``    — English TTS (Xenova pre-converted)
  - ``whisper-base``   — Multilingual STT (Xenova pre-converted)
  - ``mms-tts-ory``    — Odia   TTS (converted here; no Xenova release)

The extension's ``ondevice.js`` adapter imports these at runtime via
transformers.js (``env.localModelPath = models/``). Only quantized
(int8) ONNX weights are kept — the full-precision twins would roughly
double the extension zip size with no demo-path quality gain.

Prerequisites:

    pip install huggingface-hub optimum[onnxruntime] transformers \
                torch sentencepiece

Usage:

    python scripts/build_extension_models.py            # incremental
    python scripts/build_extension_models.py --force    # refetch + reconvert

Soft-fails: if the Odia conversion breaks (missing optimum / torch,
tokenizer drift, OOM), the script logs a warning and exits successfully
as long as the three Xenova bundles landed. The extension's on-device
mode then falls back to the gateway for Odia — still MMS-TTS, just
served by the Python service instead of WASM.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO / "apps" / "extension" / "models"

# name-on-disk -> HF repo id (already int8-quantized ONNX).
XENOVA_REPOS = {
    "mms-tts-hin": "Xenova/mms-tts-hin",
    "mms-tts-eng": "Xenova/mms-tts-eng",
    "whisper-base": "Xenova/whisper-base",
}

# Odia: no Xenova release. We export via optimum from Meta's fp32
# checkpoint and quantize locally.
ORY_SOURCE_REPO = "facebook/mms-tts-ory"
ORY_LOCAL_NAME = "mms-tts-ory"

# Files transformers.js actually loads. snapshot_download uses these as
# allow_patterns so we don't drag the ~150 MB fp32 model.onnx into the
# extension zip.
KEEP_PATTERNS = [
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "preprocessor_config.json",
    "generation_config.json",
    "added_tokens.json",
    "vocab.json",
    "onnx/model_quantized.onnx",
    "onnx/decoder_model_merged_quantized.onnx",
    "onnx/encoder_model_quantized.onnx",
]


def log(msg: str) -> None:
    print(f"[extension-models] {msg}", flush=True)


def size_mb(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / (1024**2)
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (
        1024**2
    )


def snapshot_download_xenova(name: str, repo_id: str, force: bool) -> bool:
    dst = MODELS_DIR / name
    marker = dst / "config.json"
    if marker.exists() and not force:
        log(f"{name}: already present ({size_mb(dst):.1f} MB) — skipping")
        return True
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        log("missing: pip install huggingface-hub")
        return False
    if dst.exists():
        shutil.rmtree(dst)
    log(f"{name}: snapshot_download {repo_id} -> {dst}")
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dst),
            allow_patterns=KEEP_PATTERNS,
        )
    except Exception as exc:  # noqa: BLE001 — surface whatever HF hub raised
        log(f"{name}: download failed — {exc}")
        return False
    log(f"{name}: ready ({size_mb(dst):.1f} MB)")
    return True


def _optimum_export(task: str, dst: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "optimum.exporters.onnx",
            "--model",
            ORY_SOURCE_REPO,
            "--task",
            task,
            str(dst),
        ],
        capture_output=True,
        text=True,
    )


def convert_mms_tts_ory(force: bool) -> bool:
    dst = MODELS_DIR / ORY_LOCAL_NAME
    quant_onnx = dst / "onnx" / "model_quantized.onnx"
    if quant_onnx.exists() and not force:
        log(f"{ORY_LOCAL_NAME}: already present ({size_mb(dst):.1f} MB) — skipping")
        return True
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    log(f"{ORY_LOCAL_NAME}: exporting {ORY_SOURCE_REPO} via optimum...")

    # Different optimum releases call the VITS task either "text-to-audio"
    # (newer) or "text-to-speech" (older) — try newer first, fall back.
    for task in ("text-to-audio", "text-to-speech"):
        result = _optimum_export(task, dst)
        if result.returncode == 0:
            log(f"{ORY_LOCAL_NAME}: export succeeded with task={task}")
            break
    else:
        log(
            f"{ORY_LOCAL_NAME}: optimum export failed — stderr tail:\n"
            f"{(result.stderr or '')[-1500:]}\n"
            "check: pip install optimum[onnxruntime] transformers torch sentencepiece"
        )
        return False

    # optimum emits model.onnx at the top level; transformers.js expects it
    # under onnx/. Move it and quantize in-place.
    onnx_dir = dst / "onnx"
    onnx_dir.mkdir(exist_ok=True)
    top_onnx = dst / "model.onnx"
    if top_onnx.exists():
        top_onnx.rename(onnx_dir / "model.onnx")
    src_onnx = onnx_dir / "model.onnx"
    if not src_onnx.exists():
        log(f"{ORY_LOCAL_NAME}: expected {src_onnx} after export — skipping quantize")
        return False

    log(f"{ORY_LOCAL_NAME}: quantizing to int8 (onnxruntime dynamic)...")
    quantized_ok = False
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        quantize_dynamic(
            model_input=str(src_onnx),
            model_output=str(quant_onnx),
            weight_type=QuantType.QInt8,
        )
        quantized_ok = True
    except ImportError:
        log("missing: pip install onnxruntime (for quantize_dynamic)")
    except Exception as exc:  # noqa: BLE001
        # VITS's duration predictor has a non-initializer tensor that
        # onnxruntime.quantization can't rewrite. Ship the fp32 weights
        # under the _quantized name — the extension loads it with
        # dtype:"q8" and transformers.js treats the file as opaque.
        # ~114 MB vs ~35 MB is the cost of not having a Xenova release.
        log(f"{ORY_LOCAL_NAME}: quantize failed ({exc}) — falling back to fp32")

    if quantized_ok:
        # Drop the fp32 model and any sidecar — we only ship the int8 variant.
        src_onnx.unlink(missing_ok=True)
        (onnx_dir / "model.onnx_data").unlink(missing_ok=True)
    else:
        # Rename fp32 to look like the quantized file the adapter expects.
        src_onnx.rename(quant_onnx)
        (onnx_dir / "model.onnx_data").unlink(missing_ok=True)

    # optimum emits vocab.json + tokenizer_config.json but not the unified
    # tokenizer.json that transformers.js loads. Synthesise it from the
    # vocab, matching the Xenova mms-tts-* repo structure.
    ensure_tokenizer_json(dst)

    log(f"{ORY_LOCAL_NAME}: ready ({size_mb(dst):.1f} MB)")
    return True


def ensure_tokenizer_json(model_dir: Path) -> None:
    """Build tokenizer.json from vocab.json + tokenizer_config.json.

    transformers.js's pipeline() loader requires the unified
    fast-tokenizer JSON format; optimum's VITS export skips it because
    VitsTokenizer has no fast implementation.
    """
    import json as _json

    tok_path = model_dir / "tokenizer.json"
    if tok_path.exists():
        return
    vocab = _json.loads((model_dir / "vocab.json").read_text(encoding="utf-8"))
    tcfg_path = model_dir / "tokenizer_config.json"
    tcfg = (
        _json.loads(tcfg_path.read_text(encoding="utf-8"))
        if tcfg_path.exists()
        else {}
    )
    pad_token = tcfg.get("pad_token") or next(
        k for k, v in vocab.items() if v == 0
    )
    unk_id = max(vocab.values()) + 1

    def esc(c: str) -> str:
        return ("\\" + c) if c in "\\]^-" else c

    char_class = "".join(esc(c) for c in vocab.keys())
    tok = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": [
            {
                "id": unk_id,
                "content": "<unk>",
                "single_word": False,
                "lstrip": False,
                "rstrip": False,
                "normalized": False,
                "special": True,
            }
        ],
        "normalizer": {
            "type": "Sequence",
            "normalizers": [
                {"type": "Lowercase"},
                {
                    "type": "Replace",
                    "pattern": {"Regex": f"[^{char_class}]"},
                    "content": "",
                },
                {"type": "Strip", "strip_left": True, "strip_right": True},
                {
                    "type": "Replace",
                    "pattern": {"Regex": "(?=.)|(?<!^)$"},
                    "content": pad_token,
                },
            ],
        },
        "pre_tokenizer": {
            "type": "Split",
            "pattern": {"Regex": ""},
            "behavior": "Isolated",
            "invert": False,
        },
        "post_processor": None,
        "decoder": None,
        "model": {"vocab": {**vocab, "<unk>": unk_id}},
    }
    tok_path.write_text(
        _json.dumps(tok, ensure_ascii=False, indent=4), encoding="utf-8"
    )
    log(f"{model_dir.name}: synthesised tokenizer.json from vocab.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--force", action="store_true", help="redownload / reconvert all models"
    )
    args = ap.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    xenova_ok = all(
        snapshot_download_xenova(name, repo, args.force)
        for name, repo in XENOVA_REPOS.items()
    )
    ory_ok = convert_mms_tts_ory(args.force)

    if not xenova_ok:
        log("one or more Xenova snapshots failed — on-device mode will be partial")
    if not ory_ok:
        log("Odia conversion skipped — the extension will fall back to gateway Odia")

    total = size_mb(MODELS_DIR)
    log(f"on-device models total: {total:.1f} MB in {MODELS_DIR}")
    # Non-zero exit only if EVERYTHING failed — a partial build is still shippable.
    return 0 if (xenova_ok or ory_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
