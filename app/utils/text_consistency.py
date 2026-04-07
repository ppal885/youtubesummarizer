"""
Consistent user-facing text: bullet shape, timestamps, deduplication, whitespace, and punctuation.

Use this module for raw strings from LLMs or transcripts before model wrapping. For Pydantic
response shaping, see ``app.utils.output_normalizer``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.utils.time_utils import format_seconds_hh_mm_ss

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•·]+|\d+[\).\]-])\s*")
_INLINE_WS_RE = re.compile(r"[ \t\r\f\v]+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_TIMESTAMP_COLON_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2})$")
_TIMESTAMP_WORD_RE = re.compile(
    r"^(?:(?P<h>\d+)\s*h(?:ours?)?\s*)?"
    r"(?:(?P<m>\d+)\s*m(?:in(?:ute)?s?)?\s*)?"
    r"(?:(?P<s>\d+)\s*s(?:ec(?:ond)?s?)?)?$",
    re.IGNORECASE,
)
_CANONICAL_TEXT_RE = re.compile(r"[^a-z0-9]+")

_TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("\u00a0", " "),
    ("â€¦", "..."),
    ("…", "..."),
    ("â€”", "-"),
    ("—", "-"),
    ("â€“", "-"),
    ("–", "-"),
    ("â€œ", '"'),
    ("â€", '"'),
    ("“", '"'),
    ("”", '"'),
    ("â€˜", "'"),
    ("â€™", "'"),
    ("‘", "'"),
    ("’", "'"),
)


def _replace_common_text_artifacts(text: str) -> str:
    value = text
    for raw, cleaned in _TEXT_REPLACEMENTS:
        value = value.replace(raw, cleaned)
    return value


def normalize_punctuation(text: str) -> str:
    """
    Collapse awkward punctuation spacing and repeated marks (inline text only).

    Intended as a building block; ``clean_text`` applies this after artifact fixes.
    """
    return _normalize_inline_punctuation_and_space(text)


def _normalize_inline_punctuation_and_space(text: str) -> str:
    value = _INLINE_WS_RE.sub(" ", text)
    value = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", value)
    value = re.sub(r"\(\s+", "(", value)
    value = re.sub(r"\s+\)", ")", value)
    value = re.sub(r"\[\s+", "[", value)
    value = re.sub(r"\s+\]", "]", value)
    value = re.sub(r"\.{4,}", "...", value)
    value = re.sub(r"([!?])\1+", r"\1", value)
    value = re.sub(r",{2,}", ",", value)
    value = re.sub(r";{2,}", ";", value)
    value = re.sub(r":{2,}", ":", value)
    return value.strip()


def clean_text(text: str, *, preserve_newlines: bool = False) -> str:
    """Normalize whitespace, smart-quote / mojibake artifacts, and punctuation."""
    value = _replace_common_text_artifacts(str(text or ""))
    if preserve_newlines:
        lines = [_normalize_inline_punctuation_and_space(line) for line in value.splitlines()]
        output: list[str] = []
        last_blank = False
        for line in lines:
            if not line:
                if output and not last_blank:
                    output.append("")
                last_blank = True
                continue
            output.append(line)
            last_blank = False
        while output and output[0] == "":
            output.pop(0)
        while output and output[-1] == "":
            output.pop()
        return "\n".join(output)
    return _normalize_inline_punctuation_and_space(value)


def normalize_bullet_text(text: str) -> str:
    """Strip bullet markers / numbering and return a single clean point string."""
    value = clean_text(text)
    value = _BULLET_PREFIX_RE.sub("", value)
    return clean_text(value)


def dedupe_text_items(
    items: Iterable[str],
    *,
    normalizer=clean_text,
) -> list[str]:
    """Remove near-duplicate lines using ``canonical_dedupe_key``; preserve first-seen wording."""
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = normalizer(item)
        key = canonical_dedupe_key(normalized)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def normalize_bullet_list(items: Iterable[str]) -> list[str]:
    """Normalize bullets to plain strings (no leading ``-``) and drop duplicate points."""
    return dedupe_text_items(items, normalizer=normalize_bullet_text)


def normalize_text_block(text: str) -> str:
    """Clean multiline text; if mostly bullets, emit consistent ``- item`` lines and dedupe."""
    value = clean_text(text, preserve_newlines=True)
    if not value:
        return ""
    non_empty = [line for line in value.splitlines() if line.strip()]
    bulletish = [line for line in non_empty if _BULLET_PREFIX_RE.match(line)]
    if non_empty and len(bulletish) >= max(1, len(non_empty) // 2):
        bullets = normalize_bullet_list(non_empty)
        if bullets:
            return "\n".join(f"- {bullet}" for bullet in bullets)
    return value


def canonical_dedupe_key(text: str) -> str:
    """Lowercase alphanumeric fingerprint for duplicate detection (after bullet strip)."""
    base = normalize_bullet_text(text).lower()
    return _CANONICAL_TEXT_RE.sub(" ", base).strip()


def normalize_timestamp(seconds: float | int | None) -> str | None:
    """Format seconds as ``mm:ss`` or ``hh:mm:ss`` (aligned with ``time_utils``)."""
    if seconds is None:
        return None
    try:
        return format_seconds_hh_mm_ss(float(seconds))
    except (TypeError, ValueError):
        return None


def normalize_timestamp_text(value: str | None) -> str | None:
    """Parse common timestamp strings (colon or ``2m 3s``) into ``hh:mm:ss`` / ``mm:ss``."""
    if value is None:
        return None
    cleaned = clean_text(value)
    if not cleaned:
        return None

    colon_match = _TIMESTAMP_COLON_RE.fullmatch(cleaned)
    if colon_match:
        hours = int(colon_match.group(1) or 0)
        minutes = int(colon_match.group(2))
        seconds = int(colon_match.group(3))
        return format_seconds_hh_mm_ss((hours * 3600) + (minutes * 60) + seconds)

    word_match = _TIMESTAMP_WORD_RE.fullmatch(cleaned)
    if word_match and any(word_match.group(name) for name in ("h", "m", "s")):
        hours = int(word_match.group("h") or 0)
        minutes = int(word_match.group("m") or 0)
        seconds = int(word_match.group("s") or 0)
        return format_seconds_hh_mm_ss((hours * 3600) + (minutes * 60) + seconds)

    return cleaned
