"""Meta NLLB-200 (distilled 600M) translation backend.

Default engine for the AaaS translate service. Handles 200 languages
↔ 200 languages including Odia (``ory_Orya``), Hindi (``hin_Deva``),
and English (``eng_Latn``) on CPU in ~1-2 s per short sentence.

Chosen over AI4Bharat IndicTrans2 because the IndicTrans2 HF repos
are gated (require `huggingface-cli login` + manually accepting terms
on the HF site), which would block the one-shot "clone and run" path
a judge-laptop bundle needs. NLLB-200 distilled-600M is published on
HF without any access barrier.

License: CC-BY-NC-4.0 (non-commercial). Same constraint as Meta
MMS-TTS, so the project's existing licence posture is unchanged —
the "swap to a commercially-licensed model before pilot" note in
``docs/bundle-build.md`` already covers both.

Model card: https://huggingface.co/facebook/nllb-200-distilled-600M
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import structlog

from app.engine.base import Translation, TranslateEngine

logger = structlog.get_logger(__name__)


# NLLB uses Flores-200 codes: ISO-639-3 language + ISO-15924 script.
_ISO_TO_FLORES: dict[str, str] = {
    "or": "ory_Orya",
    "hi": "hin_Deva",
    "en": "eng_Latn",
    "bn": "ben_Beng",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "ml": "mal_Mlym",
    "kn": "kan_Knda",
    "gu": "guj_Gujr",
    "mr": "mar_Deva",
    "pa": "pan_Guru",
    "as": "asm_Beng",
    "ur": "urd_Arab",
    "ne": "npi_Deva",
    "si": "sin_Sinh",
}

_MODEL_ID = "facebook/nllb-200-distilled-600M"


class NllbEngine(TranslateEngine):
    name = "nllb"

    def __init__(self, cache_dir: str | Path = "./models"):
        self._cache_dir = Path(cache_dir)
        self._model = None
        self._tokenizer = None

    async def load(self) -> None:
        try:
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Install transformers + torch: pip install -e .[indic]"
            ) from exc

        def _blocking_load() -> tuple[object, object]:
            tok = AutoTokenizer.from_pretrained(
                _MODEL_ID, cache_dir=str(self._cache_dir)
            )
            mod = AutoModelForSeq2SeqLM.from_pretrained(
                _MODEL_ID, cache_dir=str(self._cache_dir)
            )
            mod.eval()
            return tok, mod

        logger.info("translate.nllb.load_start", model=_MODEL_ID)
        self._tokenizer, self._model = await asyncio.to_thread(_blocking_load)
        logger.info("translate.nllb.load_ok", model=_MODEL_ID)

    async def translate(
        self, text: str, *, src_lang: str, tgt_lang: str
    ) -> Translation:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("engine not loaded; call load() during lifespan")

        src = src_lang.lower().split("-")[0]
        tgt = tgt_lang.lower().split("-")[0]
        if src == tgt:
            return Translation(text=text, src_lang=src, tgt_lang=tgt, engine=self.name)

        src_code = _ISO_TO_FLORES.get(src)
        tgt_code = _ISO_TO_FLORES.get(tgt)
        if src_code is None or tgt_code is None:
            raise ValueError(f"Unsupported language pair {src}->{tgt}")

        def _blocking_infer() -> str:
            import torch  # type: ignore[import-not-found]

            self._tokenizer.src_lang = src_code
            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            )
            # NLLB picks the target language via the forced BOS token.
            # ``convert_tokens_to_ids`` is the transformers-4.46+ API;
            # older ``lang_code_to_id`` was removed.
            forced_bos = self._tokenizer.convert_tokens_to_ids(tgt_code)
            with torch.no_grad():
                out = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                )
            return self._tokenizer.batch_decode(out, skip_special_tokens=True)[0]

        result = await asyncio.to_thread(_blocking_infer)
        return Translation(text=result, src_lang=src, tgt_lang=tgt, engine=self.name)
