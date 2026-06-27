"""STT engine Protocol.

All backends expose the same shape so the service factory can plug them
in interchangeably. Async methods so the FastAPI route doesn't block the
event loop on model inference (even when the underlying call is
blocking, wrap it in ``asyncio.to_thread`` inside the engine).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Transcript:
    """Result of a single transcribe call."""

    text: str
    language: str  # BCP-47 or ISO-639-1 (e.g. "or", "en", "hi")
    confidence: float  # 0.0–1.0; engines without a real score return 1.0
    engine: str  # e.g. "mock", "indic_wav2vec", "whisper"


class STTEngine(Protocol):
    """What the FastAPI route sees.

    Engines must accept 16-bit PCM WAV bytes. Resampling / format coercion
    happens inside the engine.
    """

    async def transcribe(
        self, audio_bytes: bytes, *, language_hint: str | None = None
    ) -> Transcript: ...
