"""OCR engine Protocol.

Same shape philosophy as translation and simplification: the HTTP
surface stays stable across engines, so the Tesseract engine that
ships today can be swapped for Surya (or the planned content-adapter
service) later without touching the route or the widget.

``lang`` is the AaaS ISO-639-1 code (``or``, ``hi``, ``en``) or
``auto``; engines map it to their own language identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OcrPage:
    page: int
    text: str
    source: str  # "text-layer" | "ocr" | "mock"


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str  # all pages joined with blank lines
    pages: list[OcrPage]
    lang: str
    engine: str


class OcrEngine(Protocol):
    async def recognize(
        self, data: bytes, *, media_type: str, lang: str
    ) -> OcrResult: ...
