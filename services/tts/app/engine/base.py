"""Engine contract for the TTS backend.

Kept narrow so a future ONNX-quantised variant or a different VITS
checkpoint family can slot in behind the same Protocol without
touching the FastAPI layer or the widget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TTSResult:
    """Raw PCM audio plus the metadata a client needs to play it.

    ``audio`` is little-endian 16-bit PCM mono at ``sample_rate`` Hz.
    WAV framing is added in the route handler so callers that want raw
    samples (e.g. browser ``AudioBuffer``) can skip the header.
    """

    audio: bytes
    sample_rate: int
    duration_seconds: float


class TTSEngine(Protocol):
    """Minimum surface a TTS backend must expose.

    ``lang`` is an ISO-639-1 hint ("or", "hi", "en"). Single-model
    backends ignore it; the multi-language wrapper uses it to route.
    The default keeps legacy single-arg callers (mostly tests) working.
    """

    sample_rate: int

    async def synthesise(self, text: str, lang: str = "or") -> TTSResult: ...

    async def warmup(self) -> None:
        """Optional: run one throwaway inference so the first real
        request doesn't pay the JIT/graph-build cost."""
