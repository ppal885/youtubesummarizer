"""
Transcript Analyst agent: segments the transcript into coarse themes for orientation.

Uses a fast deterministic heuristic (time-banded chunks) so the stack stays cheap and
predictable for demos; themes are labeled as non-evidence in the composer prompt.
"""

from __future__ import annotations

from app.copilot.contracts import TranscriptAnalystResult, TranscriptTheme
from app.models.transcript_models import TranscriptTextChunk
from app.utils.time_utils import format_seconds_hh_mm_ss


class TranscriptAnalystAgent:
    """Derives section labels and theme summaries from chunked transcript text."""

    _MAX_THEMES: int = 5
    _PREVIEW_CHARS: int = 180

    def analyze(
        self,
        *,
        merged_transcript: str | None,
        chunks: list[TranscriptTextChunk],
        video_end_seconds: float,
    ) -> TranscriptAnalystResult:
        """
        Never raises: on failure returns ``ok=False`` with a safe empty theme list.

        ``chunk_indices`` in each theme match ``TranscriptChunkPassage.chunk_index`` after
        chunks are persisted in row order (0 .. n-1).
        """
        _ = merged_transcript
        _ = video_end_seconds
        try:
            if not chunks:
                return TranscriptAnalystResult(
                    ok=False,
                    themes=[],
                    fallback_reason="no_chunks",
                )
            n = len(chunks)
            n_seg = min(self._MAX_THEMES, max(1, min(n, max(2, n // 3))))
            themes: list[TranscriptTheme] = []
            for seg_i in range(n_seg):
                lo = seg_i * n // n_seg
                hi = (seg_i + 1) * n // n_seg
                if lo >= hi:
                    continue
                indices = list(range(lo, hi))
                merged_piece = " ".join(
                    chunks[j].text.strip() for j in indices if chunks[j].text.strip()
                )
                preview = merged_piece[: self._PREVIEW_CHARS].replace("\n", " ")
                if len(merged_piece) > self._PREVIEW_CHARS:
                    preview += "..."
                start_seconds = chunks[lo].start_seconds
                themes.append(
                    TranscriptTheme(
                        theme_id=seg_i,
                        title=f"Segment {seg_i + 1} (~{format_seconds_hh_mm_ss(start_seconds)})",
                        summary=preview,
                        chunk_indices=indices,
                    )
                )
            return TranscriptAnalystResult(ok=True, themes=themes, fallback_reason=None)
        except Exception as exc:
            return TranscriptAnalystResult(
                ok=False,
                themes=[],
                fallback_reason=f"analyst_error:{exc!s}",
            )
