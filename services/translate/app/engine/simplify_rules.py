"""Rule-based text simplification ("Easy Read").

Rewrites bureaucratic government prose into shorter, plainer sentences
without any ML: expand abbreviations, swap legalese for everyday words
via a per-language glossary, drop boilerplate openers, and split
overlong sentences at semicolons and conjunctions. Fully offline — this
is the engine the portable demo bundle ships.

The pipeline is deliberately idempotent: running the output through the
engine again yields the same text, so the widget double-clicking "Easy
Read" can never compound rewrites.

Glossaries are seed lists — extend them freely; keys are matched
longest-first so multi-word phrases win over their sub-words.
"""

from __future__ import annotations

import asyncio
import re

from app.engine.simplify_base import Simplification

# ---------------------------------------------------------------------------
# Data. lang -> { bureaucratic phrase : plain replacement }.
# English matching is case-insensitive with \b word boundaries;
# Odia uses whitespace lookaround boundaries (\b is unreliable for
# Indic scripts in Python's re).
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, dict[str, str]] = {
    "en": {
        "it is hereby notified that": "please note:",
        "notwithstanding anything contained herein": "even so,",
        "for the kind information of": "to inform",
        "shall be deemed to be": "counts as",
        "shall be liable to": "must",
        "is required to": "must",
        "are required to": "must",
        "at the earliest": "as soon as possible",
        "competent authority": "responsible officer",
        "in accordance with": "following",
        "with reference to": "about",
        "in the event of": "if",
        "in respect of": "about",
        "on or before": "by",
        "prior to": "before",
        "subsequent to": "after",
        "pursuant to": "under",
        "aforesaid": "mentioned above",
        "aforementioned": "mentioned above",
        "herein": "in this document",
        "hereby": "now",
        "thereof": "of it",
        "therein": "in it",
        "commence": "start",
        "commencement": "start",
        "utilize": "use",
        "utilise": "use",
        "endeavour": "try",
        "furnish": "give",
        "peruse": "read",
        "avail": "get",
        "intimate": "inform",
        "intimation": "notice",
        "remuneration": "pay",
        "emoluments": "salary",
        "domicile": "home address",
        "requisite": "required",
        "stipulated": "fixed",
        "undertake": "promise",
        "reside": "live",
        "obtain": "get",
        "mandatory": "required",
        "grievance": "complaint",
        "grievances": "complaints",
        "expeditiously": "quickly",
        "forthwith": "immediately",
    },
    # Bureaucratic Odia -> everyday Odia. Seed list; extend during
    # demo rehearsal against the real notice text.
    "or": {
        "ଅବଗତ କରାଯାଉଅଛି": "ଜଣାଇ ଦିଆଯାଉଛି",
        "ନିମ୍ନଲିଖିତ": "ତଳେ ଲେଖା",
        "ନିର୍ଦ୍ଧାରିତ": "ସ୍ଥିର",
        "ଆବଶ୍ୟକୀୟ": "ଦରକାରୀ",
        "ପ୍ରଦାନ କରିବେ": "ଦେବେ",
        "ପ୍ରଦାନ କରାଯିବ": "ଦିଆଯିବ",
        "କାର୍ଯ୍ୟକାରୀ ହେବ": "ଲାଗୁ ହେବ",
        "ବିଜ୍ଞପ୍ତି": "ସୂଚନା",
        "ଅଭିଯୋଗ": "ସମସ୍ୟା",
        "ତତ୍‌କ୍ଷଣାତ୍": "ସଙ୍ଗେ ସଙ୍ଗେ",
    },
    # Present so the API accepts hi; entries can come later.
    "hi": {},
}

# Matched case-insensitively; keys may contain dots (escaped when
# compiled). Applied before the glossary so "w.e.f." never reaches the
# sentence splitter (its dots would create false sentence breaks).
ABBREVIATIONS: dict[str, str] = {
    "w.e.f.": "with effect from",
    "w.r.t.": "regarding",
    "i.e.": "that is",
    "e.g.": "for example",
    "viz.": "namely",
    "etc.": "and so on",
    "govt.": "government",
    "dept.": "department",
    "s/o": "son of",
    "d/o": "daughter of",
    "r/o": "resident of",
}

# Context-sensitive abbreviations, tried before the generic table:
# "no." only means "number" when digits follow (never rewrite the word
# "no" at a sentence end), and a sentence-final "etc." must keep its
# role as a terminator.
_ABBR_SPECIAL: list[tuple[str, str]] = [
    (r"(?i)(?<!\w)no\.(?=\s*\d)", "number"),
    (r"(?i)(?<!\w)etc\.(?=\s+[A-Z])", "and so on."),
]

# Regex -> replacement, applied first. Deletes decorative legal framing
# that carries no information for the reader.
BOILERPLATE: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"(?i)^\s*whereas[, ]\s*", ""),
        (r"(?i)\bby order of the [^,.;]+[,.;]?\s*", ""),
        (r"(?i)\bsubject to the provisions of [^,.;]+[,.;]?\s*", ""),
    ],
    "or": [],
    "hi": [],
}

# Sentence terminators: Latin + danda/double danda.
_SENTENCE_RE = re.compile(r"[^.!?।॥]+[.!?।॥]+\s*|[^.!?।॥]+$")

# Clause-level split points for overlong sentences, per language:
# (break string, prefix for the right half). which-clauses read better
# restarted with a pronoun ("…closed, which may…" -> "…closed. This
# may…"); the rest just get capitalized.
_CLAUSE_BREAKS: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("; ", ""),
        (", and ", ""),
        (", but ", ""),
        (", which ", "This "),
        (", whereas ", ""),
    ],
    "or": [
        ("; ", ""),
        (", ଏବଂ ", ""),
        (", କିନ୍ତୁ ", ""),
        (", ଯାହା ", "ଏହା "),
        (" ଏବଂ ", ""),
        (" କିନ୍ତୁ ", ""),
    ],
    "hi": [
        ("; ", ""),
        (", और ", ""),
        (", लेकिन ", ""),
        (", जो ", "यह "),
    ],
}

_MAX_SENTENCE_CHARS = 120


def _terminator(lang: str) -> str:
    return "।" if lang in ("or", "hi") else "."


def _compile_glossary() -> dict[str, list[tuple[re.Pattern[str], str]]]:
    compiled: dict[str, list[tuple[re.Pattern[str], str]]] = {}
    for lang, entries in GLOSSARY.items():
        rules: list[tuple[re.Pattern[str], str]] = []
        # Longest key first so multi-word phrases win over sub-words.
        for phrase in sorted(entries, key=len, reverse=True):
            if lang == "en":
                pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            else:
                pat = re.compile(r"(?<!\S)" + re.escape(phrase) + r"(?!\S)")
            rules.append((pat, entries[phrase]))
        compiled[lang] = rules
    return compiled


def _compile_abbreviations() -> list[tuple[re.Pattern[str], str]]:
    rules: list[tuple[re.Pattern[str], str]] = []
    for abbr in sorted(ABBREVIATIONS, key=len, reverse=True):
        # No trailing \b: keys often end in "." which is a non-word
        # char, so \b there would anchor incorrectly.
        pat = re.compile(r"(?<!\w)" + re.escape(abbr), re.IGNORECASE)
        rules.append((pat, ABBREVIATIONS[abbr]))
    return rules


_GLOSSARY_COMPILED = _compile_glossary()
_ABBREVIATIONS_COMPILED = _compile_abbreviations()
_BOILERPLATE_COMPILED = {
    lang: [(re.compile(pat), repl) for pat, repl in rules]
    for lang, rules in BOILERPLATE.items()
}


def _match_case(replacement: str, original: str) -> str:
    """Keep a leading capital when replacing a sentence-initial word."""
    if original[:1].isupper() and replacement[:1].islower():
        return replacement[0].upper() + replacement[1:]
    return replacement


def expand_abbreviations(text: str, lang: str) -> str:
    for raw, repl in _ABBR_SPECIAL:
        text = re.sub(raw, repl, text)
    for pat, repl in _ABBREVIATIONS_COMPILED:
        text = pat.sub(lambda m, r=repl: _match_case(r, m.group(0)), text)
    return text


def apply_glossary(text: str, lang: str) -> str:
    # Substitutions can uncover new matches ("is mandatory to" ->
    # "is required to" -> "must"), so run to a fixpoint. The cap only
    # guards against a pathological future glossary cycle.
    for _ in range(5):
        before = text
        for pat, repl in _GLOSSARY_COMPILED.get(lang, []):
            text = pat.sub(lambda m, r=repl: _match_case(r, m.group(0)), text)
        if text == before:
            break
    return text


def strip_boilerplate(text: str, lang: str) -> str:
    for pat, repl in _BOILERPLATE_COMPILED.get(lang, []):
        text = pat.sub(repl, text)
    return text


def split_sentences(text: str) -> list[str]:
    return [m.group(0).strip() for m in _SENTENCE_RE.finditer(text) if m.group(0).strip()]


def split_long_sentence(sentence: str, lang: str, max_chars: int = _MAX_SENTENCE_CHARS) -> list[str]:
    """Split one overlong sentence at its strongest clause boundary.

    Recurses on the halves so a triple-clause monster becomes three
    sentences. Under max_chars the sentence passes through untouched.
    """
    if len(sentence) <= max_chars:
        return [sentence]
    term = _terminator(lang)
    for brk, prefix in _CLAUSE_BREAKS.get(lang, _CLAUSE_BREAKS["en"]):
        idx = sentence.find(brk, max_chars // 3)
        if idx == -1:
            continue
        left = sentence[:idx].rstrip(" ,;")
        right = prefix + sentence[idx + len(brk):].lstrip()
        if not left or not right.strip():
            continue
        if not left.endswith((".", "!", "?", "।", "॥")):
            left += term
        if right[:1].islower():
            right = right[0].upper() + right[1:]
        return split_long_sentence(left, lang, max_chars) + split_long_sentence(right, lang, max_chars)
    return [sentence]


def simplify_text(text: str, lang: str) -> str:
    """Full pipeline. Idempotent: simplify(simplify(x)) == simplify(x)."""
    out = re.sub(r"\s+", " ", text).strip()
    if not out:
        return out
    out = strip_boilerplate(out, lang)
    out = expand_abbreviations(out, lang)
    out = apply_glossary(out, lang)
    pieces: list[str] = []
    for sentence in split_sentences(out):
        pieces.extend(split_long_sentence(sentence, lang))
    return " ".join(pieces)


class RuleSimplifyEngine:
    """Offline rule-based simplifier. No load() — ready at import."""

    name = "rules"

    async def simplify(self, text: str, *, lang: str) -> Simplification:
        lang = lang.lower().split("-")[0]
        result = await asyncio.to_thread(simplify_text, text, lang)
        return Simplification(text=result, lang=lang, engine=self.name)
