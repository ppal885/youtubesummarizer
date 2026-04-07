"""Interview prep learning path (structured JSON from transcript)."""

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.models.request_models import TranscriptLearningRequest
from app.services.learning_service import LearningService, _normalize_interview_prep
from app.services.llm.mock_provider import MockLLMService
from app.services.llm.schemas import (
    InterviewPrepEdgeCasePayload,
    InterviewPrepPayload,
    InterviewPrepQaPairPayload,
    InterviewPrepSystemDesignInsightPayload,
)


def test_normalize_interview_prep_filters_empty_strings() -> None:
    payload = InterviewPrepPayload(
        key_questions=[
            InterviewPrepQaPairPayload(question=" Q1 ", answer=" A1 "),
            InterviewPrepQaPairPayload(question="", answer="x"),
            InterviewPrepQaPairPayload(question="y", answer=""),
        ],
        system_design_insights=[
            InterviewPrepSystemDesignInsightPayload(title=" T ", insight=" I "),
        ],
        edge_cases=[
            InterviewPrepEdgeCasePayload(scenario=" S ", discussion=" D "),
        ],
    )
    kq, sd, ec = _normalize_interview_prep(payload)
    assert len(kq) == 1
    assert kq[0].question == "Q1" and kq[0].answer == "A1"
    assert len(sd) == 1 and sd[0].title == "T"
    assert len(ec) == 1


@pytest.mark.asyncio
async def test_learning_service_interview_prep_uses_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(llm_provider="mock", retriever_provider="mock")
    svc = LearningService(settings=settings, llm=MockLLMService())
    fake_ctx = SimpleNamespace(
        video_id="abc123",
        title="Mock title",
        labeled_transcript="[time=0:00 start_seconds=0.0] hello world",
    )
    monkeypatch.setattr(svc, "_context", lambda _req: fake_ctx)

    out = await svc.interview_prep(
        TranscriptLearningRequest(url="https://www.youtube.com/watch?v=abc123", language="en"),
    )
    assert out.video_id == "abc123"
    assert out.title == "Mock title"
    assert len(out.key_questions) >= 1
    assert all(q.question and q.answer for q in out.key_questions)
    assert isinstance(out.system_design_insights, list)
    assert isinstance(out.edge_cases, list)
