"""AI4Bharat IndicWav2Vec engine for Odia STT.

Optional backend — selected with ``AAAS_STT_ENGINE=indic_wav2vec`` and
``pip install -e .[indic]``. Kept out of the base install so the mock
engine works everywhere without pulling 1+ GB of torch wheels.

Model card: https://huggingface.co/ai4bharat/indicwav2vec-odia
License: MIT. Model loads from ``AAAS_STT_MODEL_CACHE_DIR`` if present,
otherwise Hugging Face Hub on first use.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import structlog

from app.engine._audio import decode_audio
from app.engine.base import STTEngine, Transcript

logger = structlog.get_logger(__name__)


class IndicWav2VecEngine(STTEngine):
    """Wraps AI4Bharat IndicWav2Vec for Odia STT.

    Inference is blocking (torch), so all model calls go through
    ``asyncio.to_thread`` to keep the event loop responsive.
    """

    name = "indic_wav2vec"
    MODEL_ID = "ai4bharat/indicwav2vec-odia"
    SAMPLE_RATE = 16_000

    def __init__(self, cache_dir: str | Path = "./models"):
        self._cache_dir = Path(cache_dir)
        self._model = None
        self._processor = None

    async def load(self) -> None:
        """Load the processor + model once at process startup."""
        try:
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForCTC,
                AutoProcessor,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Install transformers + torch: pip install -e .[indic]"
            ) from exc

        def _blocking_load() -> tuple[object, object]:
            processor = AutoProcessor.from_pretrained(
                self.MODEL_ID, cache_dir=str(self._cache_dir)
            )
            model = AutoModelForCTC.from_pretrained(
                self.MODEL_ID, cache_dir=str(self._cache_dir)
            )
            model.eval()
            return processor, model

        logger.info("stt.indic.load_start", model=self.MODEL_ID)
        self._processor, self._model = await asyncio.to_thread(_blocking_load)
        logger.info("stt.indic.load_ok", model=self.MODEL_ID)

    async def transcribe(
        self, audio_bytes: bytes, *, language_hint: str | None = None
    ) -> Transcript:
        if self._model is None or self._processor is None:
            raise RuntimeError("engine not loaded; call load() during lifespan")

        # Decode container (WAV/FLAC/OGG via libsndfile, webm/Opus via
        # PyAV) and resample to 16 kHz mono.
        audio, _ = decode_audio(audio_bytes, target_sr=self.SAMPLE_RATE)

        def _blocking_infer() -> str:
            import torch  # type: ignore[import-not-found]

            inputs = self._processor(
                audio,
                sampling_rate=self.SAMPLE_RATE,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = self._model(inputs.input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            text = self._processor.batch_decode(predicted_ids)[0]
            return str(text)

        text = await asyncio.to_thread(_blocking_infer)
        return Transcript(
            text=text.strip(),
            language="or",
            confidence=1.0,  # CTC doesn't expose a clean confidence
            engine=self.name,
        )
