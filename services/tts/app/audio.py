"""Wrap raw int16 PCM into a RIFF/WAV container.

We build the 44-byte header by hand rather than pulling in ``scipy`` or
``soundfile`` at request time — it keeps the synthesis hot path free of
extra allocations and avoids a PyInstaller dependency on libsndfile.
"""

from __future__ import annotations

import struct


def pcm16_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Return a playable WAV byte string for 16-bit mono PCM input."""
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm)

    header = b"".join(
        [
            b"RIFF",
            struct.pack("<I", 36 + data_size),
            b"WAVE",
            b"fmt ",
            struct.pack("<I", 16),  # PCM fmt chunk size
            struct.pack("<H", 1),  # AudioFormat = PCM
            struct.pack("<H", num_channels),
            struct.pack("<I", sample_rate),
            struct.pack("<I", byte_rate),
            struct.pack("<H", block_align),
            struct.pack("<H", bits_per_sample),
            b"data",
            struct.pack("<I", data_size),
        ]
    )
    return header + pcm
