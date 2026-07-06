"""Unit tests for the rule-based simplifier's pure functions."""

from __future__ import annotations

from app.engine.simplify_rules import (
    apply_glossary,
    expand_abbreviations,
    simplify_text,
    split_long_sentence,
    split_sentences,
    strip_boilerplate,
)


def test_glossary_respects_word_boundaries() -> None:
    # "commencement" has its own entry and must not be hit by "commence".
    assert apply_glossary("commencement", "en") == "start"
    assert apply_glossary("recommence", "en") == "recommence"


def test_glossary_preserves_leading_capital() -> None:
    assert apply_glossary("Furnish the form", "en") == "Give the form"


def test_glossary_cascade_reaches_fixpoint() -> None:
    # "mandatory" -> "required" uncovers "is required to" -> "must".
    out = apply_glossary("It is mandatory to apply.", "en")
    assert out == "It must apply."
    assert apply_glossary(out, "en") == out


def test_abbreviations() -> None:
    assert expand_abbreviations("w.e.f. 01.04.2026", "en") == "with effect from 01.04.2026"
    assert expand_abbreviations("Registration no. 42", "en") == "Registration number 42"
    # Sentence-ending "no" must never become "number".
    assert expand_abbreviations("The answer is no.", "en") == "The answer is no."
    # Sentence-final etc. keeps terminating the sentence.
    assert expand_abbreviations("Bring pens, paper, etc. All items matter.", "en") == (
        "Bring pens, paper, and so on. All items matter."
    )


def test_strip_boilerplate() -> None:
    assert strip_boilerplate("Whereas, the office will close.", "en") == "the office will close."


def test_split_sentences_handles_danda() -> None:
    assert split_sentences("ପ୍ରଥମ ବାକ୍ୟ। ଦ୍ୱିତୀୟ ବାକ୍ୟ।") == ["ପ୍ରଥମ ବାକ୍ୟ।", "ଦ୍ୱିତୀୟ ବାକ୍ୟ।"]


def test_split_long_sentence_only_over_limit() -> None:
    short = "The office will remain closed, and staff will stay home."
    assert split_long_sentence(short, "en") == [short]


def test_split_long_sentence_at_semicolon() -> None:
    long = (
        "The office of the District Collector will remain closed on all "
        "public holidays notified by the Government; employees are advised "
        "to plan their leave accordingly and inform their supervisors."
    )
    parts = split_long_sentence(long, "en")
    assert len(parts) == 2
    assert parts[0].endswith(".")
    assert parts[1][0].isupper()


def test_split_long_sentence_which_clause_gets_pronoun() -> None:
    long = (
        "The examination scheduled for the fourth week of March stands "
        "postponed until further orders from the Board of Secondary Education, "
        "which may cause inconvenience to candidates across all districts."
    )
    parts = split_long_sentence(long, "en")
    assert len(parts) == 2
    assert parts[1].startswith("This may cause")


def test_simplify_text_idempotent() -> None:
    text = (
        "It is hereby notified that all applicants shall furnish the "
        "requisite documents on or before the stipulated date; candidates "
        "who fail to comply shall be liable to rejection, which may be "
        "communicated expeditiously w.e.f. the date of notification."
    )
    once = simplify_text(text, "en")
    assert simplify_text(once, "en") == once
    assert "hereby" not in once
    assert "furnish" not in once


def test_simplify_text_empty() -> None:
    assert simplify_text("   ", "en") == ""
