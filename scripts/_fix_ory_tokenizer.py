"""One-off fixup for apps/extension/models/mms-tts-ory/.

optimum's ONNX export for facebook/mms-tts-ory emits vocab.json +
tokenizer_config.json but not the fast-tokenizer tokenizer.json that
transformers.js requires. onnxruntime.quantization.quantize_dynamic
also fails on the VITS duration-predictor graph, so the int8 model
never gets written.

This script:
  1. Synthesises tokenizer.json from vocab.json + tokenizer_config.json
     using the structure that Xenova's Hindi / English pre-conversions
     follow.
  2. Renames onnx/model.onnx to onnx/model_quantized.onnx so the
     extension's `dtype: "q8"` pipeline call resolves it (the file is
     fp32, the filename lies — ~110 MB instead of ~35 MB int8, but
     transformers.js loads it cleanly).

Idempotent: skips either step if its output already exists. Safe to
re-run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = (
    Path(__file__).resolve().parent.parent
    / "apps" / "extension" / "models" / "mms-tts-ory"
)


def log(msg: str) -> None:
    print(f"[fix-ory] {msg}", flush=True)


def build_tokenizer_json() -> None:
    tok_path = BASE / "tokenizer.json"
    if tok_path.exists():
        log(f"tokenizer.json already present ({tok_path.stat().st_size} bytes) — skip")
        return
    vocab = json.loads((BASE / "vocab.json").read_text(encoding="utf-8"))
    tcfg = json.loads((BASE / "tokenizer_config.json").read_text(encoding="utf-8"))
    pad_token = tcfg.get("pad_token") or next(k for k, v in vocab.items() if v == 0)
    unk_id = max(vocab.values()) + 1

    def esc(c: str) -> str:
        # Inside a [...] char class the Rust regex engine used by
        # transformers.js treats only these as special.
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
                # Insert the pad token before every char and at string end —
                # VITS MMS-TTS needs this (tokenizer_config add_blank=True).
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
        json.dumps(tok, ensure_ascii=False, indent=4), encoding="utf-8"
    )
    log(f"wrote {tok_path} ({tok_path.stat().st_size} bytes)")


def rename_fp32_as_quantized() -> None:
    src = BASE / "onnx" / "model.onnx"
    dst = BASE / "onnx" / "model_quantized.onnx"
    if dst.exists():
        log(f"{dst.name} already exists ({dst.stat().st_size:,} B) — skip")
        return
    if not src.exists():
        log(f"neither model.onnx nor model_quantized.onnx found under {BASE/'onnx'}")
        sys.exit(1)
    src.rename(dst)
    log(f"{src.name} -> {dst.name} ({dst.stat().st_size:,} B)")


if __name__ == "__main__":
    if not BASE.is_dir():
        sys.exit(f"no such dir: {BASE}  (run build_extension_models.py first)")
    build_tokenizer_json()
    rename_fp32_as_quantized()
    log("done")
