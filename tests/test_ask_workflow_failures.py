from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.copilot.verifier_agent import VerifierAgent
from app.db.session import SessionLocal
from app.exceptions import (
    BackendWorkflowError,
    EmbeddingInvocationError,
    LLMInvocationError,
    TranscriptFetchError,
)
from app.main import app
from app.models.qa_models import TranscriptChunkPassage
from app.models.request_models import AskRequest
from app.models.retrieval_models import RetrievalHit
from app.routers.ask import get_qa_service
from app.services.llm.mock_provider import MockLLMService
from app.services.qa_service import QAService
from app.services.query_understanding import run_query_understanding
from app.services.retrieval import get_chunk_retriever
from app.workflows.ask_graph import AskGraphDeps, node_answer_question
from app.workflows.ask_state import CopilotAskState


def _passage(idx: int = 0) -> TranscriptChunkPassage:
    return TranscriptChunkPassage(
        id=idx + 1,
        chunk_index=idx,
        start_seconds=10.0 + idx,
        text=f"Passage {idx} about Redis and caching.",
    )


def _hit(idx: int = 0) -> RetrievalHit:
    return RetrievalHit(
        passage=_passage(idx),
        semantic_score=0.8,
        keyword_score=0.7,
        final_score=0.75,
        ranking_explanation="unit-test",
    )


class _FailingQueryUnderstandingLLM(MockLLMService):
    async def understand_qa_query(self, question: str):
        raise LLMInvocationError("synthetic failure")


class _FailingAnswerLLM(MockLLMService):
    async def answer_question(self, question: str, context_passages, **kwargs):
        raise LLMInvocationError("answer failure")


class _FakeGraphMissingResponse:
    async def ainvoke(self, initial, config):
        _ = initial
        _ = config
        return CopilotAskState(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            question="What is Redis?",
            language="en",
        ).model_dump()


class _BackendWorkflowFailureService:
    async def ask(self, body, db):
        _ = body
        _ = db
        raise BackendWorkflowError("graph failed")


class _EmbeddingFailureService:
    async def ask(self, body, db):
        _ = body
        _ = db
        raise EmbeddingInvocationError("embedding broke")


class _TranscriptFailureService:
    async def ask(self, body, db):
        _ = body
        _ = db
        raise TranscriptFetchError("No transcript was found for this video.")


@pytest.mark.asyncio
async def test_run_query_understanding_falls_back_when_llm_fails() -> None:
    payload = await run_query_understanding("What is Redis?", _FailingQueryUnderstandingLLM())
    assert payload.intent == "definition"
    assert "redis" in payload.normalized_query.lower()


@pytest.mark.asyncio
async def test_node_answer_question_falls_back_when_composer_fails() -> None:
    settings = Settings(llm_provider="mock", retriever_provider="mock")
    deps = AskGraphDeps(
        settings=settings,
        llm=_FailingAnswerLLM(),
        retriever=get_chunk_retriever(settings),
        transcript_repo=SimpleNamespace(),
        db=SimpleNamespace(),
    )
    state = CopilotAskState(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        question="What is Redis?",
        selected_passages=[_passage(0)],
        retrieved_chunks=[_hit(0)],
    )

    patch = await node_answer_question(state, {"configurable": {"deps": deps}})
    assert patch["answer"]
    assert patch["confidence"] == 0.0
    assert patch["confidence_score"] == 0.0
    assert patch["raw_llm_answer"] == ""


def test_verifier_returns_safe_fallback_on_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.copilot.verifier_agent.evaluate_qa_answer",
        lambda raw, passages: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    result = VerifierAgent().verify("raw answer", [_passage(0)])
    assert result.ok is False
    assert result.confidence == 0.0
    assert result.confidence_score == 0.0
    assert result.final_answer


def test_verifier_marks_low_overlap_answers_low_confidence() -> None:
    result = VerifierAgent().verify(
        "Redis is a cache, but the speaker also explains kubernetes autoscaling and service meshes.",
        [_passage(0)],
    )

    assert result.ok is True
    assert result.accepted is True
    assert result.final_answer.startswith("Redis is a cache")
    assert 0.08 <= result.confidence_score < 0.22
    assert result.confidence == result.confidence_score
    assert result.notes == "low_overlap"


@pytest.mark.asyncio
async def test_qa_service_raises_backend_workflow_error_when_graph_omits_final_response() -> None:
    settings = Settings(llm_provider="mock", retriever_provider="mock")
    service = QAService(settings, MockLLMService(), get_chunk_retriever(settings))
    service._copilot_graph = _FakeGraphMissingResponse()
    db = SessionLocal()
    try:
        with pytest.raises(BackendWorkflowError, match="final_response"):
            await service.ask(
                AskRequest(
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    question="What is Redis?",
                    language="en",
                ),
                db,
            )
    finally:
        db.close()


def test_ask_route_maps_backend_workflow_error_to_500() -> None:
    app.dependency_overrides[get_qa_service] = lambda: _BackendWorkflowFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/ask",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "question": "What is Redis?",
                "language": "en",
            },
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "graph failed"}
    finally:
        app.dependency_overrides.clear()


def test_ask_route_maps_embedding_failure_to_502() -> None:
    app.dependency_overrides[get_qa_service] = lambda: _EmbeddingFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/ask",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "question": "What is Redis?",
                "language": "en",
            },
        )
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_ask_route_maps_transcript_failure_via_shared_status_logic() -> None:
    app.dependency_overrides[get_qa_service] = lambda: _TranscriptFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/ask",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "question": "What is Redis?",
                "language": "en",
            },
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_streaming_path_emits_error_event_for_backend_workflow_failure() -> None:
    client = TestClient(app)
    try:
        import app.routers.ask as ask_router

        original = ask_router.iter_ask_sse_events

        async def _broken(body, db, settings):
            raise BackendWorkflowError("graph failed")
            yield ""  # pragma: no cover

        ask_router.iter_ask_sse_events = _broken
        response = client.post(
            "/api/v1/ask",
            headers={"Accept": "text/event-stream"},
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "question": "What is Redis?",
                "language": "en",
            },
        )
        assert response.status_code == 200
        assert "graph failed" in response.text
    finally:
        ask_router.iter_ask_sse_events = original
        app.dependency_overrides.clear()
