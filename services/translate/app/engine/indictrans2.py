"""AI4Bharat IndicTrans2 (distilled 200M) backend.

Optional — enabled with ``AAAS_TRANSLATE_ENGINE=indictrans2`` and
``pip install -e .[indic]``. Handles 22 Indic languages ↔ English on
CPU in ~2 s per short sentence. License: MIT.

Model card: https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import structlog

from app.engine.base import Translation, TranslateEngine

logger = structlog.get_logger(__name__)


# IndicTrans2 expects ISO-639-1 + script suffix, e.g. ``ory_Orya``, ``eng_Latn``.
_ISO_TO_INDICTRANS: dict[str, str] = {
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
}

# We use the two distilled models: one Indic->English, one English->Indic.
# Indic↔Indic is done as Indic->English->Indic if ever needed.
_INDIC_TO_EN = "ai4bharat/indictrans2-indic-en-dist-200M"
_EN_TO_INDIC = "ai4bharat/indictrans2-en-indic-dist-200M"


class IndicTrans2Engine(TranslateEngine):
    name = "indictrans2"

    def __init__(self, cache_dir: str | Path = "./models"):
        self._cache_dir = Path(cache_dir)
        self._indic_en = None
        self._en_indic = None
        self._tok_indic_en = None
        self._tok_en_indic = None

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

        def _blocking_load() -> tuple[object, object, object, object]:
            tok_ie = AutoTokenizer.from_pretrained(
                _INDIC_TO_EN, trust_remote_code=True, cache_dir=str(self._cache_dir)
            )
            mod_ie = AutoModelForSeq2SeqLM.from_pretrained(
                _INDIC_TO_EN, trust_remote_code=True, cache_dir=str(self._cache_dir)
            )
            mod_ie.eval()
            tok_ei = AutoTokenizer.from_pretrained(
                _EN_TO_INDIC, trust_remote_code=True, cache_dir=str(self._cache_dir)
            )
            mod_ei = AutoModelForSeq2SeqLM.from_pretrained(
                _EN_TO_INDIC, trust_remote_code=True, cache_dir=str(self._cache_dir)
            )
            mod_ei.eval()
            return tok_ie, mod_ie, tok_ei, mod_ei

        logger.info("translate.indictrans2.load_start")
        (
            self._tok_indic_en,
            self._indic_en,
            self._tok_en_indic,
            self._en_indic,
        ) = await asyncio.to_thread(_blocking_load)
        logger.info("translate.indictrans2.load_ok")

    async def translate(
        self, text: str, *, src_lang: str, tgt_lang: str
    ) -> Translation:
        if self._indic_en is None:
            raise RuntimeError("engine not loaded; call load() during lifespan")

        src = src_lang.lower().split("-")[0]
        tgt = tgt_lang.lower().split("-")[0]
        if src == tgt:
            return Translation(text=text, src_lang=src, tgt_lang=tgt, engine=self.name)

        src_code = _ISO_TO_INDICTRANS.get(src)
        tgt_code = _ISO_TO_INDICTRANS.get(tgt)
        if src_code is None or tgt_code is None:
            raise ValueError(f"Unsupported language pair {src}->{tgt}")

        if tgt == "en":
            tok, mod = self._tok_indic_en, self._indic_en
        elif src == "en":
            tok, mod = self._tok_en_indic, self._en_indic
        else:
            # Pivot via English.
            en = await self.translate(text, src_lang=src, tgt_lang="en")
            return await self.translate(en.text, src_lang="en", tgt_lang=tgt)

        def _blocking_infer() -> str:
            import torch  # type: ignore[import-not-found]

            prefixed = f"{src_code} {tgt_code} {text}"
            inputs = tok(prefixed, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                out = mod.generate(
                    **inputs,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                )
            return tok.batch_decode(out, skip_special_tokens=True)[0]

        result = await asyncio.to_thread(_blocking_infer)
        return Translation(text=result, src_lang=src, tgt_lang=tgt, engine=self.name)
