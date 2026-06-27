"""faster-whisper backend for multilingual STT (English, Hindi, Odia).

Optional — select with ``AAAS_STT_ENGINE=whisper`` and install
``pip install -e .[whisper]``. CTranslate2 runtime is CPU-friendly
(~250 MB model, ~2 s latency for 10 s audio on a modern laptop).

Odia support in whisper-small is poor (~40% WER). Prefer
``indic_wav2vec`` for Odia; whisper is the pragmatic choice for English
and Hindi, and the universal fallback when no Indic model is available.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import structlog

from app.engine._audio import decode_audio
from app.engine.base import STTEngine, Transcript

logger = structlog.get_logger(__name__)


class WhisperEngine(STTEngine):
    name = "whisper"
    MODEL_SIZE = "small"  # good accuracy/speed tradeoff on CPU
    SAMPLE_RATE = 16_000

    def __init__(self, cache_dir: str | Path = "./models"):
        self._cache_dir = Path(cache_dir)
        self._model = None

    async def load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "Install faster-whisper: pip install -e .[whisper]"
            ) from exc

        def _blocking_load() -> object:
            return WhisperModel(
                self.MODEL_SIZE,
                device="cpu",
                compute_type="int8",
                download_root=str(self._cache_dir),
            )

        logger.info("stt.whisper.load_start", size=self.MODEL_SIZE)
        self._model = await asyncio.to_thread(_blocking_load)
        logger.info("stt.whisper.load_ok", size=self.MODEL_SIZE)

    async def transcribe(
        self, audio_bytes: bytes, *, language_hint: str | None = None
    ) -> Transcript:
        if self._model is None:
            raise RuntimeError("engine not loaded; call load() during lifespan")

        # faster-whisper wants float32 mono at 16 kHz.
        audio, _ = decode_audio(audio_bytes, target_sr=self.SAMPLE_RATE)

        lang = None
        if language_hint:
            lang = language_hint.lower().split("-")[0]
            if lang not in {"en", "hi", "or"}:
                lang = None

        def _blocking_infer() -> tuple[str, str]:
            segments, info = self._model.transcribe(
                audio,
                language=lang,
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text, info.language

        text, detected = await asyncio.to_thread(_blocking_infer)
        return Transcript(
            text=text,
            language=detected,
            confidence=1.0,
            engine=self.name,
        )
