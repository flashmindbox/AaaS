"""Deterministic mock OCR engine.

No ML, no external binary, no file IO — mirrors the STT mock: a small
library of plausible scanned-notice texts, picked deterministically
from the input bytes so demos and tests are stable. This is what the
service falls back to when the Tesseract binary or the [ocr] extras
are missing, so the demo never dies on a fresh machine.
"""

from __future__ import annotations

import hashlib

from app.engine.ocr_base import OcrPage, OcrResult

_NOTICES: dict[str, list[str]] = {
    "en": [
        (
            "GOVERNMENT OF ODISHA. It is hereby notified that all applicants "
            "shall furnish the requisite documents on or before the stipulated "
            "date w.e.f. 01.04.2026. Applications received subsequent to the "
            "said date shall be liable to rejection."
        ),
        (
            "OFFICE OF THE DISTRICT COLLECTOR, JAJPUR. Pursuant to the "
            "aforesaid notification, the competent authority has stipulated "
            "that scholarship disbursement shall commence w.e.f. 15.05.2026."
        ),
    ],
    "or": [
        (
            "ଓଡ଼ିଶା ସରକାର। ସମସ୍ତ ଆବେଦନକାରୀଙ୍କୁ ଅବଗତ କରାଯାଉଅଛି ଯେ ନିର୍ଦ୍ଧାରିତ "
            "ତାରିଖ ପୂର୍ବରୁ ଆବଶ୍ୟକୀୟ କାଗଜପତ୍ର ଦାଖଲ କରିବେ।"
        ),
    ],
    "hi": [
        (
            "ओडिशा सरकार। सभी आवेदकों को सूचित किया जाता है कि निर्धारित "
            "तिथि से पूर्व आवश्यक दस्तावेज़ जमा करें।"
        ),
    ],
}


class MockOcrEngine:
    """Canned notice text keyed on a hash of the upload."""

    name = "mock"

    async def recognize(
        self, data: bytes, *, media_type: str, lang: str
    ) -> OcrResult:
        key = lang.lower().split("-")[0]
        notices = _NOTICES.get(key) or _NOTICES["en"]
        pick = hashlib.sha256(data).digest()[0] % len(notices)
        text = notices[pick]
        return OcrResult(
            text=text,
            pages=[OcrPage(page=1, text=text, source="mock")],
            lang=key if key in _NOTICES else "en",
            engine=self.name,
        )
