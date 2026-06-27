"""Smoke-test the webm/Opus decoder path added for the widget mic.

Generates a 1-second 16 kHz sine, encodes it to both WAV and webm/Opus
using PyAV (so the test is self-contained), then feeds each byte blob
to ``decode_audio`` and checks we get sensible float32 mono samples.
"""

from __future__ import annotations

import io

import av
import numpy as np

from app.engine._audio import decode_audio


def _sine_pcm(duration_s: float = 1.0, sr: int = 16_000, freq: int = 440) -> np.ndarray:
    t = np.linspace(0.0, duration_s, int(sr * duration_s), endpoint=False)
    return (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _encode(samples: np.ndarray, sr: int, container_fmt: str, codec: str) -> bytes:
    buf = io.BytesIO()
    out = av.open(buf, mode="w", format=container_fmt)
    stream = out.add_stream(codec, rate=sr)
    stream.layout = "mono"  # type: ignore[assignment]
    frame = av.AudioFrame.from_ndarray(
        samples.reshape(1, -1), format="flt", layout="mono"
    )
    frame.sample_rate = sr
    frame.pts = 0
    for packet in stream.encode(frame):
        out.mux(packet)
    for packet in stream.encode(None):
        out.mux(packet)
    out.close()
    return buf.getvalue()


def test_decode_wav():
    pcm = _sine_pcm()
    wav_bytes = _encode(pcm, 16_000, "wav", "pcm_s16le")
    audio, sr = decode_audio(wav_bytes, target_sr=16_000)
    assert sr == 16_000
    assert audio.dtype == np.float32
    assert audio.ndim == 1
    assert 0.9 * len(pcm) < len(audio) <= len(pcm) + 16_000  # rough length


def test_decode_webm_opus():
    """The widget records audio/webm — this is the case that was broken."""
    pcm = _sine_pcm(duration_s=1.0, sr=48_000)
    webm_bytes = _encode(pcm, 48_000, "webm", "libopus")
    audio, sr = decode_audio(webm_bytes, target_sr=16_000)
    assert sr == 16_000
    assert audio.dtype == np.float32
    assert audio.ndim == 1
    # 1 s of audio resampled to 16 kHz should be ~16 k samples.
    assert 14_000 < len(audio) < 18_000
    # Non-silent signal
    assert float(np.abs(audio).mean()) > 1e-3
