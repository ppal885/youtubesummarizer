"""Offline demo path: precomputed summary and Q&A for the catalog sample video."""

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.demo.catalog import DEMO_VIDEO_ID, DEMO_VIDEO_URL, demo_developer_digest, demo_final_summary
from app.main import app
from app.models.request_models import AskRequest, SummarizeRequest
from app.services.llm import get_llm_service
from app.services.qa_service import QAService
from app.services.qa_streaming import iter_ask_sse_events
from app.services.retrieval import get_chunk_retriever
from app.services.summary_service import SummaryService
from app.db.session import SessionLocal


@pytest.mark.asyncio
async def test_demo_summary_skips_network_and_llm() -> None:
    settings = Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock")
    svc = SummaryService(settings, get_llm_service(settings))
    body = SummarizeRequest(url=DEMO_VIDEO_URL, summary_type="brief", language="en")
    out = await svc.summarize_from_url(body, trace_id="test-demo-sum")
    assert out.model_dump(exclude={"performance"}) == demo_final_summary().model_dump(exclude={"performance"})
    assert out.performance is not None and out.performance.llm_ms == 0.0


@pytest.mark.asyncio
async def test_demo_developer_mode_adds_digest_without_llm() -> None:
    settings = Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock")
    svc = SummaryService(settings, get_llm_service(settings))
    body = SummarizeRequest(
        url=DEMO_VIDEO_URL,
        summary_type="brief",
        language="en",
        developer_mode=True,
    )
    out = await svc.summarize_from_url(body, trace_id="test-demo-dev")
    expected = demo_final_summary().model_copy(update={"developer_digest": demo_developer_digest()})
    assert out.model_dump(exclude={"performance"}) == expected.model_dump(exclude={"performance"})
    assert out.performance is not None


@pytest.mark.asyncio
async def test_demo_ask_returns_canned_answer() -> None:
    settings = Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock")
    qa = QAService(settings, get_llm_service(settings), get_chunk_retriever(settings))
    db = SessionLocal()
    try:
        res = await qa.ask(
            AskRequest(url=DEMO_VIDEO_URL, question="What about the elephants?", language="en"),
            db,
        )
    finally:
        db.close()
    assert "trunk" in res.answer.lower()
    assert res.sources
    assert 0.0 <= res.confidence <= 1.0
    assert 0.0 <= res.confidence_score <= 1.0


def test_ask_negotiated_accept_event_stream_matches_explicit_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /ask + Accept: text/event-stream must emit the same SSE as POST /ask/stream."""
    demo = Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock")
    monkeypatch.setattr("app.routers.ask.settings", demo)

    client = TestClient(app)
    body = {"url": DEMO_VIDEO_URL, "question": "Where was this filmed?", "language": "en"}
    explicit = client.post("/api/v1/ask/stream", json=body)
    negotiated = client.post("/api/v1/ask", json=body, headers={"Accept": "text/event-stream"})
    assert explicit.status_code == 200
    assert negotiated.status_code == 200
    assert "text/event-stream" in explicit.headers.get("content-type", "")
    assert "text/event-stream" in negotiated.headers.get("content-type", "")
    assert explicit.text == negotiated.text


def test_ask_without_accept_returns_json_ask_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.ask.settings", Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock"))
    client = TestClient(app)
    r = client.post(
        "/api/v1/ask",
        json={"url": DEMO_VIDEO_URL, "question": "What about the elephants?", "language": "en"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "answer" in data and "sources" in data and "confidence" in data
    assert "confidence_score" in data


@pytest.mark.asyncio
async def test_demo_stream_emits_done_with_sources() -> None:
    settings = Settings(demo_mode=True, llm_provider="mock", retriever_provider="mock")
    db = SessionLocal()
    try:
        lines: list[str] = []
        async for ln in iter_ask_sse_events(
            AskRequest(url=DEMO_VIDEO_URL, question="Where was this filmed?", language="en"),
            db,
            settings=settings,
        ):
            lines.append(ln)
    finally:
        db.close()
    assert lines
    done_payloads: list[dict] = []
    for ln in lines:
        if not ln.startswith("data:"):
            continue
        try:
            obj = json.loads(ln[5:].strip())
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "delta":
            assert "text" in obj
        if obj.get("type") == "done":
            done_payloads.append(obj)
    assert len(done_payloads) == 1
    assert done_payloads[0]["answer"]
    assert done_payloads[0]["sources"]
    assert "confidence_score" in done_payloads[0]


def test_config_exposes_demo_url_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routers.config_public as cp

    fresh = Settings(demo_mode=True, llm_provider="mock")
    monkeypatch.setattr(cp, "settings", fresh)

    client = TestClient(app)
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    data = r.json()
    assert data["demo_mode"] is True
    assert data["demo_sample_video_url"] == DEMO_VIDEO_URL
    assert DEMO_VIDEO_ID in data["demo_sample_video_url"]
