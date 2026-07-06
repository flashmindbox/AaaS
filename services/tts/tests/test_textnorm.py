"""Unit tests for speech text normalisation (no torch needed)."""

from __future__ import annotations

from app.textnorm import (
    number_to_words,
    split_script_runs,
    verbalize_numbers,
)


def test_small_numbers_exact_odia() -> None:
    assert number_to_words(0, "or") == "ଶୂନ"
    assert number_to_words(8, "or") == "ଆଠ"
    assert number_to_words(19, "or") == "ଊଣେଇଶ"


def test_composed_numbers() -> None:
    assert number_to_words(47, "en") == "forty seven"
    assert number_to_words(300, "or") == "ତିନି ଶହ"
    assert number_to_words(2026, "or") == "ଦୁଇ ହଜାର କୋଡ଼ିଏ ଛଅ"
    assert number_to_words(305, "en") == "three hundred five"


def test_verbalize_amount_in_sentence() -> None:
    out = verbalize_numbers("ଦେୟ 300 ଟଙ୍କା", "or")
    assert "300" not in out
    assert "ତିନି ଶହ" in out


def test_odia_digits_folded() -> None:
    out = verbalize_numbers("୩୦୦ ଟଙ୍କା", "or")
    assert "୩" not in out
    assert "ତିନି ଶହ" in out


def test_long_runs_read_digit_by_digit() -> None:
    out = verbalize_numbers("କୋଡ଼ 17099", "or")
    # 5 digits -> digit-by-digit, so the '8'-free vocab issue and any
    # place-value weirdness never arise.
    assert "ଏକ ସାତ ଶୂନ ନଅ ନଅ" in out


def test_zero_padded_reads_digit_by_digit() -> None:
    out = verbalize_numbers("30/06/2026", "en")
    assert "thirty" in out
    assert "zero six" in out
    assert "two thousand twenty six" in out


def test_symbols() -> None:
    assert "percent" in verbalize_numbers("50%", "en")
    assert "ଏବଂ" in verbalize_numbers("ST & SC", "or")


def test_unknown_lang_passthrough() -> None:
    assert verbalize_numbers("300", "fr") == "300"


def test_split_runs_mixed() -> None:
    runs = split_script_runs("ପରିଚାଳିତ RESIDENTIAL SCHOOL ଦ୍ୱାରା", primary="or")
    assert [r[0] for r in runs] == ["or", "en", "or"]
    assert runs[1][1] == "RESIDENTIAL SCHOOL"


def test_split_runs_neutral_words_stick_to_previous() -> None:
    runs = split_script_runs("ଦେୟ 300 ଟଙ୍କା", primary="or")
    assert len(runs) == 1
    assert runs[0][0] == "or"


def test_split_runs_all_neutral_uses_primary() -> None:
    runs = split_script_runs("300 / 2026", primary="or")
    assert runs == [("or", "300 / 2026")]


def test_split_runs_leading_neutral_joins_first_run() -> None:
    runs = split_script_runs("300 ଟଙ୍କା ଦେୟ", primary="or")
    assert len(runs) == 1
    assert runs[0][1].startswith("300")
