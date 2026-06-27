"""Mock STT engine.

Returns canned transcripts so the demo UI, tests, and bundle smoke test
all work without a 300+ MB model download. The behaviour is
intentionally deterministic: the same audio length → the same
transcript, so rehearsals are reproducible.

Rotation: we cycle through a small library of demo phrases keyed on the
language hint. That way the judge can mic-in any sound and get a
plausible demo response in their chosen language.
"""

from __future__ import annotations

import hashlib

from app.engine.base import STTEngine, Transcript

# Curated demo phrases. Odia transliterations match what a student in
# Jajpur might actually say to the admissions form. Keep to ASCII keys
# so the file is encoding-robust; Odia/Hindi/English text lives in the
# list values which are UTF-8 on disk but Python sees them as unicode
# strings once decoded.
_PHRASES: dict[str, list[str]] = {
    "or": [
        "ମୋ ନାମ ପ୍ରିୟା",  # "My name is Priya"
        "ମୁଁ ଜାଜପୁରରୁ ଆସିଛି",  # "I am from Jajpur"
        "ଭୂଗୋଳ",  # "geography" — subject answer
        "ଉତ୍କଳ ବିଶ୍ୱବିଦ୍ୟାଳୟ",  # "Utkal University"
        "୨୦୦୫",  # "2005" — a year-of-birth
    ],
    "hi": [
        "मेरा नाम प्रिया है",
        "मैं जाजपुर से हूं",
        "भूगोल",
        "उत्कल विश्वविद्यालय",
        "२००५",
    ],
    "en": [
        "My name is Priya",
        "I am from Jajpur",
        "Geography",
        "Utkal University",
        "2005",
    ],
}


class MockSTTEngine(STTEngine):
    """Canned-response STT. No ML, no network, no file I/O."""

    name = "mock"

    async def transcribe(
        self, audio_bytes: bytes, *, language_hint: str | None = None
    ) -> Transcript:
        lang = (language_hint or "or").lower().split("-")[0]
        if lang not in _PHRASES:
            lang = "or"
        phrases = _PHRASES[lang]
        # Deterministic choice so audio-of-same-length → same phrase.
        # Hash the raw bytes rather than length so the "same click
        # twice" case cycles naturally through the library.
        digest = hashlib.sha256(audio_bytes).digest()
        idx = digest[0] % len(phrases)
        return Transcript(
            text=phrases[idx],
            language=lang,
            confidence=1.0,
            engine=self.name,
        )
