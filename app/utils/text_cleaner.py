import re


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace and strip edges."""
    collapsed = re.sub(r"\s+", " ", text)
    return collapsed.strip()


def merge_transcript_segments(segments: list[str], separator: str = " ") -> str:
    """Join cleaned segments with a single separator."""
    parts = [normalize_whitespace(s) for s in segments if s and s.strip()]
    return separator.join(parts)
