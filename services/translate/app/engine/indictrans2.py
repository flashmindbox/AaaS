"""AI4Bharat IndicTrans2 (distilled 200M) backend.

Optional — enabled with ``AAAS_TRANSLATE_ENGINE=indictrans2`` and
``pip install -e .[indic]``. Handles 22 Indic languages ↔ English on
CPU; concurrent requests are decoded together in batches (see
``_Batcher``). License: MIT.

Model card: https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M
"""

from __future__ import annotations

import asyncio
import logging
import re
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


# Any whitespace-delimited token containing a digit — dates (05.04.2026),
# reference codes (EX-II/886), amounts (Rs.1000) — minus trailing sentence
# punctuation. On long inputs the model rewrites these ("2026" came back as
# "2021" on a BSE circular), so they never reach it: each is swapped for a
# "#n" placeholder, which the model copies through verbatim.
_NUMERIC_TOKEN = re.compile(r"\S*\d\S*?(?=[.,;:!?)\]]*(?:\s|$))")
# The model sometimes emits the placeholder back as "# 1" — accept both.
_PLACEHOLDER = re.compile(r"#\s?(\d+)")


def mask_numbers(text: str) -> tuple[str, list[str]]:
    """Replace digit-bearing tokens with ``#1``, ``#2``…; returns (masked, originals)."""
    if "#" in text:  # our marker already in use — leave the text alone
        return text, []
    originals: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        originals.append(m.group(0))
        return f"#{len(originals)}"

    return _NUMERIC_TOKEN.sub(_sub, text), originals


def unmask_numbers(text: str, originals: list[str]) -> tuple[str, bool]:
    """Put the original tokens back; returns (text, repaired).

    Greedy decoding drops, doubles or invents a placeholder in most longer
    sentences. Re-translating without the mask doubled the time and let the
    model rewrite the numbers (2026 -> 2021), so repair instead: every
    placeholder it kept gets its number (doubles included), invented ones
    are removed, and any it dropped are appended in brackets — no number is
    ever lost or altered.
    """
    kept: set[int] = set()

    def _sub(m: re.Match[str]) -> str:
        i = int(m.group(1))
        if 1 <= i <= len(originals):
            kept.add(i)
            return originals[i - 1]
        return ""

    out = _PLACEHOLDER.sub(_sub, text)
    missing = [originals[i - 1] for i in range(1, len(originals) + 1) if i not in kept]
    repaired = bool(missing) or len(_PLACEHOLDER.findall(text)) != len(originals)
    if missing:
        out = f"{out.rstrip()} ({', '.join(missing)})"
    return re.sub(r"[ \t]{2,}", " ", out).strip(), repaired


def _greedy_decode(tok: object, mod: object, texts: list[str]) -> list[str]:
    """Greedy-decode a padded batch, keeping the decoder's KV cache.

    ``generate()`` hands the model a transformers ``Cache`` object that
    IndicTrans2's bundled modeling code can't handle, so it had to run
    with ``use_cache=False`` and one sentence at a time. Driving
    ``forward()`` ourselves keeps the legacy ``past_key_values`` tuples the
    model was written for, and lets one call decode many sentences: on the
    8-vCPU droplet 8 short sentences take 1.9 s, against 15 s one-by-one
    with 4-beam ``generate()``. Output matches greedy ``generate()``.
    """
    import torch  # type: ignore[import-not-found]

    cfg = mod.config  # type: ignore[attr-defined]
    inputs = tok(  # type: ignore[operator]
        texts, return_tensors="pt", padding=True, truncation=True, max_length=512
    )
    with torch.no_grad():
        enc = mod.get_encoder()(  # type: ignore[attr-defined]
            input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"]
        )
        n = inputs["input_ids"].shape[0]
        seqs = torch.full((n, 1), cfg.decoder_start_token_id, dtype=torch.long)
        done = torch.zeros(n, dtype=torch.bool)
        # Per-sentence output cap. OCR junk ("Memo copy ... No. 35 ...") can
        # make the model repeat itself up to the 512 limit — 40 s that every
        # other sentence in the batch waits out. Real translations stay
        # under ~1.5x the input length (longest seen: 157 -> 240 tokens).
        limits = (inputs["attention_mask"].sum(dim=1).float() * 1.6 + 16).long()
        past = None
        for step in range(512):
            out = mod(  # type: ignore[operator]
                encoder_outputs=enc,
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=seqs if past is None else seqs[:, -1:],
                past_key_values=past,
                use_cache=True,
                return_dict=True,
            )
            past = out.past_key_values
            nxt = out.logits[:, -1, :].argmax(-1)
            nxt = torch.where(done, torch.full_like(nxt, cfg.pad_token_id), nxt)
            seqs = torch.cat([seqs, nxt[:, None]], dim=1)
            done |= (nxt == cfg.eos_token_id) | (step + 1 >= limits)
            if bool(done.all()):
                break
    return tok.batch_decode(seqs, skip_special_tokens=True)  # type: ignore[attr-defined]


# Requests that arrive together (a page translation sends several at once)
# are decoded as one batch. The short wait costs nothing noticeable and lets
# concurrent requests join the same batch.
_MAX_BATCH = 16
_BATCH_WAIT_S = 0.02


class _Batcher:
    """Collects concurrent inputs for one model and decodes them together.

    One worker per model, so inference for that model never runs twice at
    once and CPU threads aren't oversubscribed by parallel requests.
    """

    def __init__(self, infer: object) -> None:
        self._infer = infer
        self._queue: asyncio.Queue[tuple[str, asyncio.Future[str]]] | None = None
        self._worker: asyncio.Task[None] | None = None

    async def submit(self, text: str) -> str:
        loop = asyncio.get_running_loop()
        if self._queue is None:
            self._queue = asyncio.Queue()
            self._worker = loop.create_task(self._run())
        fut: asyncio.Future[str] = loop.create_future()
        await self._queue.put((text, fut))
        return await fut

    async def _run(self) -> None:
        assert self._queue is not None
        loop = asyncio.get_running_loop()
        while True:
            items = [await self._queue.get()]
            deadline = loop.time() + _BATCH_WAIT_S
            while len(items) < _MAX_BATCH:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    items.append(await asyncio.wait_for(self._queue.get(), remaining))
                except TimeoutError:
                    break
            await self._decode(items)

    async def _decode(self, items: list[tuple[str, asyncio.Future[str]]]) -> None:
        try:
            outs = await asyncio.to_thread(self._infer, [t for t, _ in items])  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            if len(items) > 1:
                # Isolate the input that broke the batch; the rest still succeed.
                for item in items:
                    await self._decode([item])
                return
            for _, fut in items:
                if not fut.done():
                    fut.set_exception(exc)
            return
        logger.info("translate.indictrans2.batch", size=len(items))
        for (_, fut), out in zip(items, outs):
            if not fut.done():
                fut.set_result(out)


class IndicTrans2Engine(TranslateEngine):
    name = "indictrans2"

    def __init__(self, cache_dir: str | Path = "./models"):
        self._cache_dir = Path(cache_dir)
        self._indic_en = None
        self._en_indic = None
        self._tok_indic_en = None
        self._tok_en_indic = None
        self._batch_indic_en = _Batcher(
            lambda texts: _greedy_decode(self._tok_indic_en, self._indic_en, texts)
        )
        self._batch_en_indic = _Batcher(
            lambda texts: _greedy_decode(self._tok_en_indic, self._en_indic, texts)
        )

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
        masked, originals = mask_numbers(text)
        if originals:
            out = await self._translate_raw(masked, src_lang=src_lang, tgt_lang=tgt_lang)
            restored, repaired = unmask_numbers(out.text, originals)
            if repaired:
                logger.info("translate.indictrans2.placeholder_repaired", n=len(originals))
            return Translation(
                text=restored, src_lang=out.src_lang, tgt_lang=out.tgt_lang, engine=self.name
            )
        return await self._translate_raw(text, src_lang=src_lang, tgt_lang=tgt_lang)

    async def _translate_raw(
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
            batcher = self._batch_indic_en
        elif src == "en":
            batcher = self._batch_en_indic
        else:
            # Pivot via English.
            en = await self.translate(text, src_lang=src, tgt_lang="en")
            return await self.translate(en.text, src_lang="en", tgt_lang=tgt)

        # IndicTrans2 operates in a Devanagari-normalised space: Indic INPUT
        # must be transliterated to Devanagari before tokenising, and Indic
        # OUTPUT transliterated from Devanagari back to the target's native
        # script (Oriya, Tamil, …). This is the pre/post-processing that
        # AI4Bharat's IndicProcessor performs; we do it with the pure-Python
        # indic-nlp-library so we don't need the Cython IndicTransToolkit
        # (which requires a C++ build toolchain absent on typical Windows
        # demo machines). English side stays Latin and is left untouched.
        from indicnlp.transliterate.unicode_transliterate import (
            UnicodeIndicTransliterator,
        )

        src_text = (
            text if src == "en"
            else UnicodeIndicTransliterator.transliterate(text, src, "hi")
        )

        raw = await batcher.submit(f"{src_code} {tgt_code} {src_text}")
        result = (
            raw if tgt == "en"
            else UnicodeIndicTransliterator.transliterate(raw, "hi", tgt)
        )
        return Translation(text=result, src_lang=src, tgt_lang=tgt, engine=self.name)
