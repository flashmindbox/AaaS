"""Settings for the TTS service.

Loaded once via ``lru_cache`` so FastAPI dependency-injection hands out
the same instance to every request.

The service runs a single backend: Meta MMS-TTS, a family of VITS
checkpoints (``facebook/mms-tts-ory``, ``-hin``, ``-eng``). One engine
class, one tokeniser shape, three models on disk — ~150 MB each and
fast enough on CPU for the judge-laptop demo budget.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canonical default — Odia gets eager-loaded at startup; Hindi and English
# lazy-load on first request so cold-start stays fast on the judge
# laptop. All three are Meta MMS-TTS VITS checkpoints with the same
# tokeniser shape, which is why a single engine class fits all of them.
DEFAULT_LANGUAGE_MODELS: dict[str, str] = {
    "or": "facebook/mms-tts-ory",
    "hi": "facebook/mms-tts-hin",
    "en": "facebook/mms-tts-eng",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    aaas_env: str = "dev"
    log_level: str = "INFO"
    tts_port: int = 8001

    # Legacy single-model id — kept so existing .env files and tests that
    # set ``AAAS_TTS_MODEL_ID`` still work. At runtime this is treated as
    # the checkpoint for the default language; ``language_models`` wins
    # per language.
    model_id: str = "facebook/mms-tts-ory"
    model_cache_dir: Path = Path("./models")

    # ISO-639-1 → HF model id. Override any slot via
    # ``AAAS_TTS_LANGUAGE_MODELS`` (JSON), e.g. to swap in a custom Odia
    # checkpoint or disable a language.
    language_models: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_LANGUAGE_MODELS)
    )

    # Language loaded eagerly at startup and used when /synthesise is
    # called without a ``lang`` field. Everything else is lazy.
    default_language: str = "or"

    # Input limit — VITS emits artefacts on very long inputs and we also
    # need a guard rail on request size. Longer text is chunked inside
    # the engine so a single request can still speak a paragraph.
    max_input_chars: int = Field(default=600, ge=50, le=2000)

    # Per-chunk cap used by the engine's sentence splitter. Smaller
    # numbers bound worst-case wall-clock per chunk and keep the
    # attention stable; larger numbers reduce prosody seams between
    # chunks. 180 is the sweet spot for MMS-VITS on CPU.
    chunk_chars: int = Field(default=180, ge=40, le=600)

    # 16 kHz is the native rate of all three MMS-TTS VITS checkpoints we
    # ship. The engine's ``sample_rate`` attr is the source of truth at
    # request time — this setting is the pre-load hint and the default
    # for the WAV header before load.
    sample_rate: int = Field(default=16000, ge=8000, le=48000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
