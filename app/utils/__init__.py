"""Shared helpers; import ``text_consistency`` for string-level normalization."""

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

__all__ = [
    "canonical_dedupe_key",
    "clean_text",
    "dedupe_text_items",
    "normalize_bullet_list",
    "normalize_bullet_text",
    "normalize_punctuation",
    "normalize_text_block",
    "normalize_timestamp",
    "normalize_timestamp_text",
]
