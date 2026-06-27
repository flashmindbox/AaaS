"""Runtime configuration for the Translation service.

``AAAS_TRANSLATE_ENGINE`` picks the backend:

- ``google`` (default) — Google Translate's free public web endpoint
  (``translate.googleapis.com``, no API key). Real Odia/Hindi/English for
  arbitrary text with zero setup; needs internet. Transparently falls
  back to the curated ``mock`` corpus when the network is unavailable.
- ``nllb`` — Meta NLLB-200 distilled-600M, 200 languages ↔ 200 languages
  including Odia/Hindi/English. Needs ``torch`` + ``transformers``
  (``pip install -e .[indic]``) and ~2.4 GB of model weights
  (``python bundle/prefetch_model.py``). Not gated on HF, so loads
  without authentication.
- ``indictrans2`` — AI4Bharat IndicTrans2 distilled-200M. Slightly
  better Indic quality than NLLB, but the HF repo is gated: requires
  ``huggingface-cli login`` and manual access approval on the HF
  website before ``prefetch_model.py`` can download weights. Opt in
  explicitly once credentials are set up.
- ``mock`` — curated parallel corpus. Explicit opt-out used by the
  PyInstaller bundle (ships without torch) and by the smoke test where
  deterministic output matters. Failure to load a real engine no
  longer silently switches to mock; set this value to force it.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EngineName = Literal["mock", "nllb", "indictrans2", "google"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix="AAAS_TRANSLATE_",
    )

    aaas_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    translate_port: int = Field(default=8003)

    engine: EngineName = Field(default="google")
    model_cache_dir: str = Field(default="./models")
    max_input_chars: int = Field(default=2000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
