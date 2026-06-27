"""Unit tests for the pure-python helpers in ``app.engine.mms``.

These don't pull in torch/transformers — they exercise the text
normaliser and the sentence splitter that wrap the model call.
"""

from __future__ import annotations

import pytest

from app.engine.mms import _normalise_text, _split_sentences


def test_normalise_strips_zero_width_joiners() -> None:
    raw = "ନ‌ମ‍ସ​କାର"
    assert _normalise_text(raw) == "ନମସକାର"


def test_normalise_collapses_whitespace_and_bom() -> None:
    raw = "﻿  ନମସ୍କାର   ଓଡ଼ିଶା  "
    assert _normalise_text(raw) == "ନମସ୍କାର ଓଡ଼ିଶା"


def test_normalise_nfc_composes_decomposed_form() -> None:
    # NFD decomposition of é → NFC-composed é. VITS tokeniser treats
    # these as different characters otherwise.
    decomposed = "Café"
    assert _normalise_text(decomposed) == "Café"


def test_split_returns_single_chunk_for_short_text() -> None:
    assert _split_sentences("Hello world.", 180) == ["Hello world."]


def test_split_breaks_on_sentence_terminators() -> None:
    text = (
        "ନମସ୍କାର। ମୁଁ ଓଡ଼ିଶା ସରକାରଙ୍କ ଏକ ଉଦ୍ୟୋଗ। "
        "ଆପଣଙ୍କୁ କେମିତି ସହଯୋଗ କରିପାରିବି?"
    )
    chunks = _split_sentences(text, max_chars=40)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 40


def test_split_handles_paragraph_without_punctuation() -> None:
    # A paragraph with no full stops falls back to space-splitting.
    text = " ".join(["word"] * 100)
    chunks = _split_sentences(text, max_chars=50)
    for chunk in chunks:
        assert len(chunk) <= 50
    assert " ".join(chunks) == text


def test_split_preserves_terminator_with_chunk() -> None:
    chunks = _split_sentences("First. Second. Third.", max_chars=8)
    # Each chunk should keep its trailing terminator so prosody cues
    # stay attached to the right sentence.
    joined = "".join(chunks).replace(" ", "")
    assert joined == "First.Second.Third."


@pytest.mark.parametrize(
    "terminator",
    [".", "!", "?", "।", "॥"],
)
def test_split_recognises_all_sentence_terminators(terminator: str) -> None:
    text = f"one{terminator} two{terminator} three{terminator}"
    chunks = _split_sentences(text, max_chars=6)
    assert len(chunks) >= 2
