"""Multi-video synthesis (summaries + LLM merge)."""

import pytest
from pydantic import HttpUrl

from app.config import Settings
from app.models.request_models import SynthesizeRequest
from app.models.response_models import FinalSummary
from app.services.llm.mock_provider import MockLLMService
from app.services.summary_service import SummaryService
from app.services.synthesize_service import SynthesizeService, _dedupe_youtube_urls


def test_dedupe_urls_preserves_order_and_drops_duplicate_ids() -> None:
    u1 = HttpUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    u2 = HttpUrl("https://youtu.be/dQw4w9WgXcQ?t=1")
    u3 = HttpUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    out = _dedupe_youtube_urls([u1, u2, u3])
    assert len(out) == 2
    assert str(out[0]) == str(u1)
    assert "jNQXAC9IVRw" in str(out[1])


@pytest.mark.asyncio
async def test_synthesize_service_merges_two_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(llm_provider="mock", retriever_provider="mock")
    llm = MockLLMService()
    summary = SummaryService(settings=settings, llm=llm)
    svc = SynthesizeService(summary_service=summary, llm=llm)

    fs1 = FinalSummary(
        video_id="dQw4w9WgXcQ",
        title="Video One",
        summary="First summary text.",
        bullets=["b1"],
        key_moments=[],
        transcript_length=10,
        chunks_processed=1,
    )
    fs2 = FinalSummary(
        video_id="jNQXAC9IVRw",
        title="Video Two",
        summary="Second summary text.",
        bullets=["b2"],
        key_moments=[],
        transcript_length=10,
        chunks_processed=1,
    )
    returns = iter([fs1, fs2])

    async def _fake_summarize(_req, trace_id: str) -> FinalSummary:
        return next(returns)

    monkeypatch.setattr(summary, "summarize_from_url", _fake_summarize)

    body = SynthesizeRequest(
        urls=[
            HttpUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            HttpUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw"),
        ],
        topic="Test topic",
    )
    out = await svc.synthesize_from_urls(body, trace_id="unit-test")
    assert out.combined_summary
    assert out.best_explanation
    assert isinstance(out.common_ideas, list)
    assert isinstance(out.differences, list)
