"""System prompt for grounded video chapter titles and summaries."""

from app.models.chapter_models import ChapterSegment
from app.utils.time_utils import format_seconds_hh_mm_ss

CHAPTERS_SYSTEM = """You label logical chapters of a YouTube video using ONLY the timed TRANSCRIPT SEGMENTS provided.

Rules:
- Output valid JSON with a single key "chapters": an array with EXACTLY one object per segment, in the SAME ORDER as the segments.
- Each object has "title" (short, specific) and "short_summary" (1–3 sentences).
- Every title and summary must be directly supported by that segment's text only. No outside knowledge.
- If a segment is vague or repetitive, still give a modest title and summary that paraphrase only what is there.
- Do not invent timestamps; segment order is fixed.

Return only the JSON object, no markdown."""


def build_chapters_user_message(segments: list[ChapterSegment]) -> str:
    """Format ordered timed segments for the chapter-labeling model."""
    lines: list[str] = [
        f"You must return exactly {len(segments)} chapter objects in order.",
        "",
    ]
    for i, seg in enumerate(segments):
        t = format_seconds_hh_mm_ss(seg.start_seconds)
        lines.append(f"SEGMENT {i + 1} start={seg.start_seconds:.2f}s formatted={t}")
        lines.append(seg.text.strip())
        lines.append("---")
    if lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)
