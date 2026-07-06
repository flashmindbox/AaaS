"""Speech-oriented text normalisation for the MMS voices.

Why this exists: each MMS-TTS checkpoint has a tiny character
vocabulary learned from its training corpus. The Odia one has **77
characters** — no Odia digits, no Latin letters, and Western digits
minus '8' (never appeared in the corpus). Characters outside the vocab
are silently dropped by the tokeniser, so "୩୦୦ ଟଙ୍କା" collapses to
near-silence and "1852" is spoken as "152". Government notices are
full of amounts, dates, IDs and English names, so before synthesis we:

1. **Verbalise numbers** — digit runs become number *words* the model
   was actually trained on ("300" → "ତିନି ଶହ"). Runs of 5+ digits
   (IDs, phone numbers) are spoken digit-by-digit, which is also how a
   human reads them out.
2. **Verbalise symbols** the vocabularies lack (%, &, ₹).
3. **Split mixed-script text into runs** so the multi-language engine
   can speak Latin fragments with the English voice instead of
   dropping them.

Number words: 0–20 and the tens are exact; 21–99 compose as
"<tens> <unit>" (e.g. 47 → "ଚାଳିଶ ସାତ"). That's not the idiomatic
fused form ("ସତଚାଳିଶ") but it is always *correct* and instantly
understood — a wrong fused numeral in a government notice would be far
worse. Native speakers on the team: extending _EXACT with the fused
forms is one dict entry per number.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Number words. _EXACT covers values we spell precisely; everything to
# 9999 composes from these. 5+ digit runs never get here (digit-by-digit).
# ---------------------------------------------------------------------------

_EXACT: dict[str, dict[int, str]] = {
    "or": {
        0: "ଶୂନ", 1: "ଏକ", 2: "ଦୁଇ", 3: "ତିନି", 4: "ଚାରି", 5: "ପାଞ୍ଚ",
        6: "ଛଅ", 7: "ସାତ", 8: "ଆଠ", 9: "ନଅ", 10: "ଦଶ", 11: "ଏଗାର",
        12: "ବାର", 13: "ତେର", 14: "ଚଉଦ", 15: "ପନ୍ଦର", 16: "ଷୋହଳ",
        17: "ସତର", 18: "ଅଠର", 19: "ଊଣେଇଶ", 20: "କୋଡ଼ିଏ", 30: "ତିରିଶ",
        40: "ଚାଳିଶ", 50: "ପଚାଶ", 60: "ଷାଠିଏ", 70: "ସତୁରି", 80: "ଅଶୀ",
        90: "ନବେ",
    },
    "hi": {
        0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच",
        6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस", 11: "ग्यारह",
        12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह",
        17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस", 30: "तीस",
        40: "चालीस", 50: "पचास", 60: "साठ", 70: "सत्तर", 80: "अस्सी",
        90: "नब्बे",
    },
    "en": {
        0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
        11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
        15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
        19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty",
        50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty",
        90: "ninety",
    },
}

_HUNDRED = {"or": "ଶହ", "hi": "सौ", "en": "hundred"}
_THOUSAND = {"or": "ହଜାର", "hi": "हज़ार", "en": "thousand"}

_SYMBOLS: dict[str, dict[str, str]] = {
    "%": {"or": "ପ୍ରତିଶତ", "hi": "प्रतिशत", "en": "percent"},
    "&": {"or": "ଏବଂ", "hi": "और", "en": "and"},
    "₹": {"or": "ଟଙ୍କା", "hi": "रुपये", "en": "rupees"},
}

# Odia and Devanagari digits fold to ASCII before verbalisation.
_DIGIT_FOLD = {ord(c): str(i) for i, c in enumerate("୦୧୨୩୪୫୬୭୮୯")}
_DIGIT_FOLD.update({ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")})

_DIGIT_RUN_RE = re.compile(r"\d+")

# Speak IDs / phone numbers / PINs digit-by-digit past this length.
_MAX_COMPOSED_DIGITS = 4


def _two_digits(n: int, lang: str) -> str:
    exact = _EXACT[lang]
    if n in exact:
        return exact[n]
    tens, unit = (n // 10) * 10, n % 10
    return f"{exact[tens]} {exact[unit]}"


def number_to_words(n: int, lang: str) -> str:
    """0–9999 as words. Composition keeps every part exact."""
    exact = _EXACT[lang]
    if n in exact:
        return exact[n]
    parts: list[str] = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        parts.append(f"{_two_digits(thousands, lang)} {_THOUSAND[lang]}")
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        parts.append(f"{exact[hundreds]} {_HUNDRED[lang]}")
    if rest:
        parts.append(_two_digits(rest, lang))
    return " ".join(parts)


def digits_to_words(run: str, lang: str) -> str:
    """Digit-by-digit reading — how a human dictates an ID or phone."""
    exact = _EXACT[lang]
    return " ".join(exact[int(d)] for d in run)


def verbalize_numbers(text: str, lang: str) -> str:
    """Replace every digit run in ``text`` with spoken words."""
    if lang not in _EXACT:
        return text
    folded = text.translate(_DIGIT_FOLD)

    def _replace(m: re.Match[str]) -> str:
        run = m.group(0)
        if len(run) > _MAX_COMPOSED_DIGITS or (len(run) > 1 and run[0] == "0"):
            # Long runs and zero-padded values ("06") read naturally
            # digit-by-digit; composing "06" as "six" would drop the
            # zero a listener expects in a date or code.
            return digits_to_words(run, lang)
        return number_to_words(int(run), lang)

    out = _DIGIT_RUN_RE.sub(_replace, folded)
    for sym, words in _SYMBOLS.items():
        if sym in out:
            out = out.replace(sym, f" {words[lang]} ")
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------------------
# Script runs: split mixed text so each fragment goes to the voice that
# can actually speak it.
# ---------------------------------------------------------------------------

_SCRIPT_RES = {
    "or": re.compile(r"[଀-୿]"),
    "hi": re.compile(r"[ऀ-ॿ]"),
    "en": re.compile(r"[A-Za-z]"),
}


def _word_script(word: str) -> str | None:
    for lang, pattern in _SCRIPT_RES.items():
        if pattern.search(word):
            return lang
    return None  # digits / punctuation / symbols — attach to a neighbour


def split_script_runs(text: str, primary: str) -> list[tuple[str, str]]:
    """Split into [(lang, fragment)] runs of consecutive same-script words.

    Script-neutral words (numbers, punctuation) stick to the preceding
    run — "ଦେୟ 300 ଟଙ୍କା" stays one Odia run — and lead the following
    run when nothing precedes them. All-neutral text belongs to
    ``primary``.
    """
    words = text.split()
    if not words:
        return []
    runs: list[tuple[str, list[str]]] = []
    pending: list[str] = []  # neutral words waiting for a script
    for word in words:
        script = _word_script(word)
        if script is None:
            if runs:
                runs[-1][1].append(word)
            else:
                pending.append(word)
            continue
        if runs and runs[-1][0] == script:
            runs[-1][1].append(word)
        else:
            runs.append((script, pending + [word] if pending else [word]))
            pending = []
    if pending:  # nothing but neutral words
        runs.append((primary, pending))
    return [(lang, " ".join(ws)) for lang, ws in runs]
