"""Simplification engine Protocol.

Same shape philosophy as the translation Protocol in ``base.py``: the
HTTP surface stays stable across engines, so the rule-based engine that
ships today can be swapped for an LLM-backed one later without touching
the widget or the route.

Languages are ISO-639-1 codes (``or``, ``hi``, ``en``), with BCP-47
accepted at the HTTP boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Simplification:
    text: str
    lang: str
    engine: str


class SimplifyEngine(Protocol):
    async def simplify(self, text: str, *, lang: str) -> Simplification: ...
