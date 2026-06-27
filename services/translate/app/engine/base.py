"""Translation engine Protocol.

Languages are referenced by ISO-639-1 codes (``or``, ``hi``, ``en``,
etc.) throughout, with a BCP-47 fallback accepted at the HTTP boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Translation:
    text: str
    src_lang: str
    tgt_lang: str
    engine: str


class TranslateEngine(Protocol):
    async def translate(
        self, text: str, *, src_lang: str, tgt_lang: str
    ) -> Translation: ...
