"""Audio byte decoder shared by the real STT engines.

Browsers send ``audio/webm`` (Opus in a webm container) from
``MediaRecorder`` — libsndfile via ``soundfile`` doesn't read webm, so
we fall back to PyAV (ffmpeg bindings with embedded libs in the wheel)
for anything soundfile rejects. That keeps a pip-only install working
on Windows without a system ffmpeg.
"""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf


def decode_audio(audio_bytes: bytes, target_sr: int = 16_000) -> tuple[np.ndarray, int]:
    """Return (float32 mono waveform, sample rate).

    Tries libsndfile (WAV, FLAC, OGG, AIFF) first. Falls back to PyAV
    for container formats libsndfile can't handle — primarily webm/Opus
    emitted by MediaRecorder in Chromium and Firefox.
    """
    try:
        audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    except (sf.LibsndfileError, RuntimeError):
        audio, sr = _decode_with_pyav(audio_bytes)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if sr != target_sr:
        n = int(len(audio) * target_sr / sr)
        audio = np.interp(
            np.linspace(0, len(audio), n, endpoint=False),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)
        sr = target_sr

    return audio.astype(np.float32), sr


def _decode_with_pyav(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    try:
        import av  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Could not decode audio container (not WAV/FLAC/OGG). "
            "Install PyAV for webm/Opus support: pip install 'av>=12'"
        ) from exc

    container = av.open(io.BytesIO(audio_bytes))
    try:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise RuntimeError("No audio stream in payload")

        resampler = av.AudioResampler(format="flt", layout="mono", rate=stream.rate)
        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                arr = resampled.to_ndarray()
                if arr.ndim > 1:
                    arr = arr.reshape(-1)
                chunks.append(arr.astype(np.float32))

        for resampled in resampler.resample(None):
            arr = resampled.to_ndarray()
            if arr.ndim > 1:
                arr = arr.reshape(-1)
            chunks.append(arr.astype(np.float32))

        if not chunks:
            raise RuntimeError("Empty audio after decode")

        return np.concatenate(chunks), stream.rate
    finally:
        container.close()
