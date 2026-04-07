"""Unit tests for ``app.utils.text_consistency`` (string-level normalization)."""

from app.utils.text_consistency import (
    canonical_dedupe_key,
    clean_text,
    dedupe_text_items,
    normalize_bullet_list,
    normalize_bullet_text,
    normalize_punctuation,
    normalize_text_block,
    normalize_timestamp,
    normalize_timestamp_text,
)


def test_clean_text_whitespace_and_punctuation_spacing() -> None:
    assert clean_text("  hello  ,  world  ") == "hello, world"
    assert clean_text("oops!!") == "oops!"


def test_normalize_punctuation_matches_inline_rules() -> None:
    assert normalize_punctuation("a  ,  b") == "a, b"


def test_normalize_bullet_text_strips_markers() -> None:
    assert normalize_bullet_text("  *  Point one  ") == "Point one"


def test_dedupe_text_items_uses_canonical_key() -> None:
    out = dedupe_text_items(["Hello!", "hello.", "  Hello  "])
    assert out == ["Hello!"]


def test_normalize_timestamp_seconds() -> None:
    assert normalize_timestamp(83) == "01:23"
    assert normalize_timestamp(None) is None


def test_normalize_text_block_emits_uniform_bullets_when_mostly_bullets() -> None:
    block = normalize_text_block(" * A \n * B \n * A ")
    assert block == "- A\n- B"


def test_canonical_dedupe_key_stable() -> None:
    assert canonical_dedupe_key("- Point.") == canonical_dedupe_key("1) Point")


def test_normalize_bullet_list_reexports_behavior() -> None:
    assert normalize_bullet_list(["* x", "- x", "y"]) == ["x", "y"]


def test_normalize_timestamp_text_colon() -> None:
    assert normalize_timestamp_text("1:05:07") == "01:05:07"
