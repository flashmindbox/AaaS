"""Digit-bearing tokens are shielded from IndicTrans2 by #n placeholders."""

from __future__ import annotations

from app.engine.indictrans2 import mask_numbers, unmask_numbers


def test_dates_and_codes_are_masked_without_sentence_punctuation() -> None:
    masked, originals = mask_numbers("No. EX-II/886 Date: 05.04.2026. Starts 21.04.2026.")
    assert masked == "No. #1 Date: #2. Starts #3."
    assert originals == ["EX-II/886", "05.04.2026", "21.04.2026"]


def test_round_trip_restores_originals_in_translated_text() -> None:
    _, originals = mask_numbers("Date: 05.04.2026, fee Rs.1000")
    assert unmask_numbers("ତାରିଖଃ #1, ଫିସ୍ #2", originals) == "ତାରିଖଃ 05.04.2026, ଫିସ୍ Rs.1000"


def test_placeholders_can_be_reordered_by_the_model() -> None:
    _, originals = mask_numbers("from 2 June to 30 June")
    assert unmask_numbers("#2 ରୁ #1", originals) == "30 ରୁ 2"


def test_placeholder_echoed_with_a_space_is_restored() -> None:
    _, originals = mask_numbers("48.5 lakh")
    assert unmask_numbers("# 1 ଲକ୍ଷ", originals) == "48.5 ଲକ୍ଷ"


def test_lost_or_invented_placeholder_signals_fallback() -> None:
    _, originals = mask_numbers("Date: 05.04.2026 No. 886")
    assert unmask_numbers("ତାରିଖଃ #1", originals) is None
    assert unmask_numbers("#1 #2 #3", originals) is None


def test_text_without_digits_or_with_hash_is_untouched() -> None:
    assert mask_numbers("Apply for the pension") == ("Apply for the pension", [])
    assert mask_numbers("Issue #5 fixed in 2026") == ("Issue #5 fixed in 2026", [])


def test_odia_digits_are_masked_too() -> None:
    masked, originals = mask_numbers("ତାରିଖ ୧୮.୦୫.୨୦୨୬ ରୁ")
    assert masked == "ତାରିଖ #1 ରୁ"
    assert originals == ["୧୮.୦୫.୨୦୨୬"]
