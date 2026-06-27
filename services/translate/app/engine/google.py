"""Google Translate engine — free public web endpoint, no API key.

Calls ``translate.googleapis.com/translate_a/single`` (``client=gtx``) —
the same endpoint Google's own page widget uses. No credentials, handles
arbitrary text, and returns real Odia / Hindi / English. Requires
internet.

Why this is the practical default for the live demo: the ``mock`` corpus
only covers a handful of curated phrases (everything else comes back as a
``[en->or] original`` passthrough), and the local NLLB / IndicTrans2
engines need gigabytes of weights. Google gives real translations for any
page text with zero setup, at the cost of one outbound HTTPS call per
chunk (the widget caches aggressively, so repeat reads are free).

When the network is unavailable the engine transparently falls back to
the curated :class:`MockTranslateEngine`, so the scripted demo phrases
still translate offline and the UI keeps flowing.
"""

from __future__ import annotations

import httpx
import structlog

from app.engine.base import Translation, TranslateEngine
from app.engine.mock import MockTranslateEngine

logger = structlog.get_logger(__name__)

_ENDPOINT = "https://translate.googleapis.com/translate_a/single"


class GoogleTranslateEngine(TranslateEngine):
    name = "google"

    def __init__(self, timeout: float = 12.0) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._fallback = MockTranslateEngine()

    async def load(self) -> None:
        # Cheap: just open a reusable client. /readyz goes green immediately,
        # like the mock engine — no model weights to wait on.
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "Mozilla/5.0 (AaaS-Translate)"},
        )
        logger.info("translate.google.ready")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def translate(
        self, text: str, *, src_lang: str, tgt_lang: str
    ) -> Translation:
        if self._client is None:
            raise RuntimeError("engine not loaded; call load() during lifespan")

        src = src_lang.lower().split("-")[0]
        tgt = tgt_lang.lower().split("-")[0]
        if src == tgt or not text.strip():
            return Translation(text=text, src_lang=src, tgt_lang=tgt, engine=self.name)

        params = {
            "client": "gtx",
            "sl": src or "auto",
            "tl": tgt,
            "dt": "t",
            "q": text,
        }
        try:
            resp = await self._client.get(_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
            segments = data[0] or []
            out = "".join(seg[0] for seg in segments if seg and seg[0])
        except (httpx.HTTPError, IndexError, TypeError, ValueError) as exc:
            # Network down / unexpected payload: keep the demo alive with the
            # curated corpus instead of surfacing a hard 503.
            logger.warning("translate.google.fallback", error=str(exc), src=src, tgt=tgt)
            return await self._fallback.translate(
                text, src_lang=src_lang, tgt_lang=tgt_lang
            )

        if not out.strip():
            out = text  # empty response — pass the source through unchanged
        return Translation(text=out, src_lang=src, tgt_lang=tgt, engine=self.name)
