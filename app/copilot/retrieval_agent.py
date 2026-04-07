"""Retrieval agent: re-ranks hybrid hits using transcript themes + question overlap."""

from __future__ import annotations

import re

from app.copilot.contracts import TranscriptAnalystResult
from app.models.retrieval_models import RetrievalHit

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 3}


class RetrievalAgent:
    """
    Selects citation-quality ordering on top of the base retriever.

    Applies a small theme-aware boost so chunks that belong to question-aligned themes
    move up; if analysis failed, returns ``hits`` unchanged.
    """

    _MAX_BOOST: float = 0.12
    _PER_THEME_CAP: float = 0.04

    def rerank(
        self,
        *,
        question: str,
        hits: list[RetrievalHit],
        analysis: TranscriptAnalystResult | None,
    ) -> list[RetrievalHit]:
        if not hits:
            return []
        if analysis is None or not analysis.ok or not analysis.themes:
            return list(hits)
        try:
            q_tokens = _tokens(question)
            if not q_tokens:
                return list(hits)

            def boost_for(hit: RetrievalHit) -> float:
                extra = 0.0
                idx = hit.passage.chunk_index
                for th in analysis.themes:
                    if idx not in th.chunk_indices:
                        continue
                    tt = _tokens(th.title + " " + th.summary)
                    overlap = len(q_tokens & tt)
                    if overlap:
                        extra += min(self._PER_THEME_CAP, 0.01 * overlap)
                return min(self._MAX_BOOST, extra)

            ranked = sorted(
                hits,
                key=lambda h: h.final_score + boost_for(h),
                reverse=True,
            )
            return ranked
        except Exception:
            return list(hits)
