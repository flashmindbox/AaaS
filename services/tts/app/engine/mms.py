"""Meta MMS-TTS backend.

Why this model:

- **Odia coverage is first-class.** Meta trained MMS on 1,100+ languages
  including Odia (``ory``), so pronunciation of conjuncts, matras and
  rare consonants is far better than any generic multilingual TTS.
- **Real-time on CPU.** The VITS variant ships at ~150 MB; a 10-word
  sentence synthesises in well under a second on a modern laptop CPU.
  No GPU required — which matters for an on-a-judge's-laptop demo.
- **Hugging Face convenience.** ``transformers.VitsModel`` loads it in
  one line. Weights can be pre-downloaded into ``MODEL_CACHE_DIR`` and
  shipped alongside the PyInstaller exe for a fully offline install.

Concurrency: torch inference is synchronous and not thread-safe across
calls on the same module instance, so we serialise with an ``asyncio``
lock and run the sync call in a thread via ``asyncio.to_thread``. That
keeps the event loop free to accept new HTTP connections while a
synthesis is in flight.

Chunking: VITS' attention degrades on very long inputs (empirically
past ~500 characters) — pitch drift, missed words, occasional glottal
noise. The engine splits on sentence terminators (``. ! ? । ॥``) and
fuses the per-chunk waveforms with a short silence in between. The cap
is configurable via ``chunk_chars``.
"""

from __future__ import annotations

import asyncio
import re
import time
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import structlog

from app.engine.base import TTSResult

if TYPE_CHECKING:  # heavy imports only at type-check time
    from transformers import PreTrainedTokenizerBase, VitsModel

logger = structlog.get_logger(__name__)


# Sentence terminators across the three scripts we support. Devanagari
# and Odia both use the danda (U+0964) and double danda (U+0965); Latin
# punctuation catches English. Keep colons/semicolons out — they're
# clause separators, not sentence enders, and splitting on them makes
# the output sound choppy.
_SENTENCE_TERMINATORS = ".!?।॥"
_SPLIT_RE = re.compile(rf"([^{re.escape(_SENTENCE_TERMINATORS)}]+[{re.escape(_SENTENCE_TERMINATORS)}]?)")

# Inter-chunk silence. 120 ms is barely perceptible as a pause but long
# enough to hide the splice and let the listener parse sentence
# boundaries. int16 mono at the model's native rate.
_INTER_CHUNK_SILENCE_MS = 120


class EmptyTokenisationError(ValueError):
    """Raised when the tokeniser maps the input to zero tokens.

    Happens when a user sends text the loaded model can't script-encode
    — e.g. Devanagari into the Odia checkpoint, or Odia into the English
    one. VITS crashes deep inside its attention layer on zero-token
    inputs, so we catch early and let the route turn this into a 400.
    """


def _normalise_text(text: str) -> str:
    """Strip zero-width chars, NFC-normalise, collapse whitespace.

    Browser copy-paste and WhatsApp-exported text routinely carry
    U+200B / U+200C / U+200D (zero-width joiners) that the tokeniser
    turns into ``<unk>`` tokens. NFC normalisation folds decomposed
    Indic sequences (base + combining mark) into their canonical form
    so the tokeniser sees consistent input regardless of how the text
    was typed.
    """
    text = unicodedata.normalize("NFC", text)
    # U+200B..U+200D and U+FEFF are invisible and break Indic tokenisers.
    text = re.sub("[​‌‍﻿]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str, max_chars: int) -> list[str]:
    """Break ``text`` into chunks no longer than ``max_chars`` chars.

    First pass splits on sentence terminators. If any fragment is still
    longer than ``max_chars`` (common for long Odia paragraphs without
    full stops), we fall back to splitting on spaces so no single chunk
    blows past the limit.
    """
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = [
        m.group(0).strip() for m in _SPLIT_RE.finditer(text) if m.group(0).strip()
    ]
    if not pieces:
        pieces = [text]

    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        # A single sentence longer than the cap — break it on spaces.
        if len(piece) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_split_on_spaces(piece, max_chars))
            continue
        if not buf:
            buf = piece
        elif len(buf) + 1 + len(piece) <= max_chars:
            buf = f"{buf} {piece}"
        else:
            chunks.append(buf)
            buf = piece
    if buf:
        chunks.append(buf)
    return chunks


def _split_on_spaces(text: str, max_chars: int) -> list[str]:
    """Last-resort splitter for super-long single sentences."""
    words = text.split(" ")
    chunks: list[str] = []
    buf = ""
    for word in words:
        if not buf:
            buf = word
        elif len(buf) + 1 + len(word) <= max_chars:
            buf = f"{buf} {word}"
        else:
            chunks.append(buf)
            buf = word
    if buf:
        chunks.append(buf)
    return chunks


class MMSEngine:
    """VITS-based engine backed by a Hugging Face ``transformers`` model."""

    sample_rate: int

    def __init__(
        self,
        *,
        model_id: str,
        cache_dir: Path,
        sample_rate: int,
        chunk_chars: int = 180,
    ) -> None:
        self._model_id = model_id
        self._cache_dir = cache_dir
        self.sample_rate = sample_rate
        self._chunk_chars = chunk_chars
        # Populated by ``load()`` — kept as ``Any`` to avoid importing
        # torch/transformers until the engine is actually built.
        self._model: VitsModel | None = None
        self._tokenizer: PreTrainedTokenizerBase | None = None
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Pull weights from the HF cache (or download once on first run)
        and build the model in a thread so startup doesn't block the loop."""
        started = time.perf_counter()
        await asyncio.to_thread(self._load_sync)
        logger.info(
            "tts.model_loaded",
            model_id=self._model_id,
            cache_dir=str(self._cache_dir),
            sample_rate=self.sample_rate,
            seconds=round(time.perf_counter() - started, 2),
        )

    def _load_sync(self) -> None:
        # Imports live here so the rest of the package (and its tests)
        # can be imported without the torch wheel installed.
        import torch
        from transformers import AutoTokenizer, VitsModel

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        model = VitsModel.from_pretrained(
            self._model_id, cache_dir=str(self._cache_dir)
        )
        # Force CPU — the judge laptops we target don't have CUDA, and
        # silently landing on MPS/CUDA makes warmup + first-call latency
        # swing by an order of magnitude between dev and demo hardware.
        model = model.to("cpu")
        model.eval()
        self._model = model
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._model_id, cache_dir=str(self._cache_dir)
        )
        # VitsModel exposes its native sample rate via config; trust it
        # over the settings default so a model swap doesn't silently
        # produce the wrong pitch.
        cfg_rate = getattr(model.config, "sampling_rate", None)
        if cfg_rate:
            self.sample_rate = int(cfg_rate)
        # Hint the interpreter at thread counts — single-request tiny
        # inference is faster with fewer threads (context-switch cost
        # outweighs parallelism below ~1k tokens). This is advisory;
        # users can still override via OMP_NUM_THREADS.
        try:
            torch.set_num_threads(max(1, (torch.get_num_threads() or 4) // 2))
        except RuntimeError:
            # set_num_threads raises if the pool is already in use;
            # harmless — we just keep the default.
            pass

    # Warmup text per language — each string is guaranteed to tokenise
    # non-empty with the matching MMS checkpoint. "Hello" for English,
    # "नमस्ते" for Hindi, "ନମସ୍କାର" for Odia.
    _WARMUP_TEXT: dict[str, str] = {
        "or": "ନମସ୍କାର",
        "hi": "नमस्ते",
        "en": "Hello.",
    }

    async def warmup(self, lang: str = "or") -> None:
        """One-shot inference so the first real request isn't 2× slower."""
        if self._model is None:
            await self.load()
        await self.synthesise(self._WARMUP_TEXT.get(lang, "Hello."), lang)

    async def synthesise(self, text: str, lang: str = "or") -> TTSResult:
        # ``lang`` is accepted for protocol compatibility; this engine is
        # bound to a single checkpoint and the caller (multi-engine
        # wrapper) has already routed to the right instance.
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("MMSEngine.load() must be awaited before use")
        clean = _normalise_text(text)
        if not clean:
            raise EmptyTokenisationError(
                "Input is empty after normalisation (only whitespace or "
                "zero-width characters)."
            )
        chunks = _split_sentences(clean, self._chunk_chars)
        async with self._lock:
            started = time.perf_counter()
            pcm = await asyncio.to_thread(self._synth_chunks_sync, chunks, lang)
            elapsed = time.perf_counter() - started
        duration = len(pcm) / (2 * self.sample_rate)  # int16 mono
        logger.info(
            "tts.synthesised",
            model=self._model_id,
            lang=lang,
            chars=len(clean),
            chunks=len(chunks),
            audio_seconds=round(duration, 2),
            wall_seconds=round(elapsed, 2),
            rtf=round(elapsed / duration, 2) if duration > 0 else None,
        )
        return TTSResult(
            audio=pcm, sample_rate=self.sample_rate, duration_seconds=duration
        )

    def _synth_chunks_sync(self, chunks: list[str], lang: str) -> bytes:
        if len(chunks) == 1:
            return self._synth_sync(chunks[0], lang)
        # Build silence once and splice between each chunk's waveform.
        silence = np.zeros(
            int(self.sample_rate * _INTER_CHUNK_SILENCE_MS / 1000), dtype=np.int16
        )
        parts: list[np.ndarray] = []
        for i, chunk in enumerate(chunks):
            pcm_bytes = self._synth_sync(chunk, lang)
            parts.append(np.frombuffer(pcm_bytes, dtype=np.int16))
            if i < len(chunks) - 1:
                parts.append(silence)
        return np.concatenate(parts).tobytes()

    def _synth_sync(self, text: str, lang: str) -> bytes:
        import torch

        assert self._model is not None
        assert self._tokenizer is not None
        inputs = self._tokenizer(text, return_tensors="pt")
        if inputs["input_ids"].shape[-1] == 0:
            raise EmptyTokenisationError(
                f"Input produced no tokens for the {self._model_id} checkpoint. "
                f"Expected {lang!r} script — check the lang field matches the text."
            )
        # inference_mode is a hair faster than no_grad and also disables
        # view tracking, which saves a bit of memory on the forward pass.
        with torch.inference_mode():
            waveform = self._model(**inputs).waveform
        # waveform shape: (1, samples), float32 in [-1, 1].
        samples = waveform.squeeze().cpu().numpy().astype(np.float32)
        if samples.ndim == 0 or samples.size == 0:
            raise RuntimeError(
                f"MMS-TTS returned an empty waveform for input {text!r}"
            )
        # Remove any DC offset the vocoder might have introduced — a
        # non-zero mean shows up as a faint thump at the start/end of
        # playback.
        samples = samples - float(samples.mean())
        # Peak-normalise to -1 dBFS to avoid clipping on unusually loud
        # outputs while keeping the relative dynamics.
        peak = float(np.max(np.abs(samples))) or 1.0
        if peak > 0:
            samples = samples * (0.89 / peak)  # 0.89 ≈ -1 dBFS
        pcm16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        return pcm16.tobytes()
