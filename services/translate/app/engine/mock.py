"""Mock translation engine — curated parallel corpus for demos.

For any sentence in the curated dictionary, we return the exact
human-translated target. For anything else we fall back to a
best-effort passthrough annotated with the language pair, so the UI
keeps flowing even off-script.

The curated entries cover:
- the five demo phrases used by the mock STT engine
- the title + intro copy of every demo site
- exam question text (so switching language during the exam works)

The purpose is to keep rehearsals deterministic and the cloud demo
runnable without gigabytes of model weights.
"""

from __future__ import annotations

import logging
import re

import structlog

from app.engine.base import Translation, TranslateEngine

logger = structlog.get_logger(__name__)


# Parallel corpus — keyed by (src, tgt, normalised_source_text).
#
# To add a new phrase: drop it into _CORPUS with all the language pairs
# you want to support. We generate the reverse pairs (en↔or, or↔en etc.)
# at import time so you don't have to duplicate entries.
_CORPUS_RAW: list[dict[str, str]] = [
    # --- STT demo phrases ---
    {
        "or": "ମୋ ନାମ ପ୍ରିୟା",
        "hi": "मेरा नाम प्रिया है",
        "en": "My name is Priya",
    },
    {
        "or": "ମୁଁ ଜାଜପୁରରୁ ଆସିଛି",
        "hi": "मैं जाजपुर से हूं",
        "en": "I am from Jajpur",
    },
    {"or": "ଭୂଗୋଳ", "hi": "भूगोल", "en": "Geography"},
    {
        "or": "ଉତ୍କଳ ବିଶ୍ୱବିଦ୍ୟାଳୟ",
        "hi": "उत्कल विश्वविद्यालय",
        "en": "Utkal University",
    },
    # --- Demo-site copy ---
    {
        "or": "ଜାଜପୁର ଜିଲ୍ଲାପାଳ କାର୍ଯ୍ୟାଳୟ",
        "hi": "जाजपुर कलेक्टर कार्यालय",
        "en": "Jajpur Collectorate",
    },
    {
        "or": "ନାଗରିକ ସେବା",
        "hi": "नागरिक सेवाएं",
        "en": "Citizen Services",
    },
    {
        "or": "ଭର୍ତ୍ତି ଆବେଦନ",
        "hi": "प्रवेश आवेदन",
        "en": "Admission Application",
    },
    {
        "or": "ଉତ୍କଳ ବିଶ୍ୱବିଦ୍ୟାଳୟ, ଭୁବନେଶ୍ୱର",
        "hi": "उत्कल विश्वविद्यालय, भुवनेश्वर",
        "en": "Utkal University, Bhubaneswar",
    },
    {
        "or": "ଓଡ଼ିଶା ମାଧ୍ୟମିକ ଶିକ୍ଷା ପରିଷଦ",
        "hi": "ओडिशा माध्यमिक शिक्षा परिषद",
        "en": "Board of Secondary Education, Odisha",
    },
    # --- Exam module strings ---
    {
        "or": "ପ୍ରଶ୍ନ",
        "hi": "प्रश्न",
        "en": "Question",
    },
    {
        "or": "ଉତ୍ତର ଦେବାକୁ କ୍ଲିକ୍ କରନ୍ତୁ",
        "hi": "उत्तर देने के लिए क्लिक करें",
        "en": "Click to answer",
    },
    {
        "or": "ଓଡ଼ିଶାର ରାଜଧାନୀ କଣ?",
        "hi": "ओडिशा की राजधानी क्या है?",
        "en": "What is the capital of Odisha?",
    },
    {
        "or": "ଭୁବନେଶ୍ୱର",
        "hi": "भुवनेश्वर",
        "en": "Bhubaneswar",
    },
    {
        "or": "ଅତିରିକ୍ତ ସମୟ ସକ୍ରିୟ",
        "hi": "अतिरिक्त समय सक्रिय",
        "en": "Extra time active",
    },
]


def _normalise(text: str) -> str:
    """Whitespace-tolerant, trailing-punct-tolerant key."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[.।॥!?]+$", "", text)  # trailing . / । / ॥ / ! / ?
    return text


# Build a flat lookup: (src, tgt) -> {normalised_src_text: target_text}
_CORPUS: dict[tuple[str, str], dict[str, str]] = {}
for row in _CORPUS_RAW:
    langs = list(row.keys())
    for src in langs:
        for tgt in langs:
            if src == tgt:
                continue
            _CORPUS.setdefault((src, tgt), {})[_normalise(row[src])] = row[tgt]


class MockTranslateEngine(TranslateEngine):
    name = "mock"

    async def translate(
        self, text: str, *, src_lang: str, tgt_lang: str
    ) -> Translation:
        src = src_lang.lower().split("-")[0]
        tgt = tgt_lang.lower().split("-")[0]
        if src == tgt:
            return Translation(text=text, src_lang=src, tgt_lang=tgt, engine=self.name)
        corpus = _CORPUS.get((src, tgt), {})
        norm = _normalise(text)
        hit = corpus.get(norm)
        if hit is not None:
            return Translation(text=hit, src_lang=src, tgt_lang=tgt, engine=self.name)
        # Unknown phrase: return a language-annotated passthrough so the
        # UI keeps flowing. The annotation is intentionally visible to
        # make it obvious we're in "mock, off-script" territory during
        # rehearsal — real model will replace this with proper output.
        annotated = f"[{src}->{tgt}] {text}"
        logger.info("translate.mock_passthrough", src=src, tgt=tgt, text=text[:80])
        return Translation(
            text=annotated, src_lang=src, tgt_lang=tgt, engine=self.name
        )
