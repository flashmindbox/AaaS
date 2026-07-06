"""Runtime configuration for the Translation service.

``AAAS_TRANSLATE_ENGINE`` picks the backend:

- ``google`` (default) — Google Translate's free public web endpoint
  (``translate.googleapis.com``, no API key). Real Odia/Hindi/English for
  arbitrary text with zero setup; needs internet. Transparently falls
  back to the curated ``mock`` corpus when the network is unavailable.
- ``indictrans2`` — AI4Bharat IndicTrans2 distilled-200M. Best Indic
  quality; this is what the demo ships (``.env.example`` selects it and
  the weights are bundled under ``./models``). The HF repos are
  "auto"-gated: a fresh download needs any logged-in HF account
  (``huggingface-cli login``), but the bundled cache loads offline
  without authentication.
- ``nllb`` — Meta NLLB-200 distilled-600M, 200 languages ↔ 200 languages
  including Odia/Hindi/English. Needs ``torch`` + ``transformers``
  (``pip install -e .[indic]``) and ~2.4 GB of model weights
  (``python bundle/prefetch_model.py``). Not gated on HF, so loads
  without authentication. Not bundled with the demo.
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
OcrEngineName = Literal["tesseract", "mock"]


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

    # OCR (/ocr — scanned notices). tesseract needs the external binary;
    # the app factory falls back to the mock engine when it's missing.
    ocr_engine: OcrEngineName = Field(default="tesseract")
    tesseract_cmd: str = Field(default="tesseract")
    # Empty -> auto-resolve to ./models/tessdata when that dir exists
    # (populated by bundle/prefetch_tessdata.py).
    tessdata_dir: str = Field(default="")
    ocr_max_bytes: int = Field(default=15_000_000)
    ocr_max_pages: int = Field(default=10)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
