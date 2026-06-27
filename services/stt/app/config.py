"""Runtime configuration for the STT service.

Configured with the same shape as the gateway and TTS services — env
vars, optional `.env` file in dev, no secrets in source.

``AAAS_STT_ENGINE`` picks the backend:

- ``indic_wav2vec`` (default) — AI4Bharat IndicWav2Vec-Odia. Needs
  ``torch`` and ``transformers`` (``pip install -e .[indic]``). If the
  extras aren't installed the lifespan falls back to mock automatically
  so a bare ``pip install -e .`` still boots.
- ``whisper`` — faster-whisper-small. CPU-friendly English + multi
  (``pip install -e .[whisper]``).
- ``mock`` — canned Odia/English transcripts. Explicit opt-out used by
  the PyInstaller bundle (which ships without torch) and by the
  automated smoke test where determinism matters more than accuracy.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EngineName = Literal["mock", "indic_wav2vec", "whisper"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix="AAAS_STT_",
    )

    aaas_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    stt_port: int = Field(default=8002)

    engine: EngineName = Field(default="indic_wav2vec")
    model_cache_dir: str = Field(default="./models")
    # Max accepted audio duration in seconds. Keeps latency bounded.
    max_audio_seconds: int = Field(default=30)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
