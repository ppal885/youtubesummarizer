"""HTTP request tracing middleware and stage helper."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.request_tracing import RequestTracingMiddleware
from app.observability.request_tracing import (
    configure_request_tracing_logging,
    get_request_trace,
    parse_incoming_request_id,
    request_trace_stage,
)


def _app() -> FastAPI:
    configure_request_tracing_logging()
    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict[str, str]:
        with request_trace_stage("handler.ping"):
            return {"status": "ok"}

    app.add_middleware(RequestTracingMiddleware)
    return app


def test_request_tracing_sets_header_and_logs_start_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.observability.request_tracing as rt

    payloads: list[dict] = []

    def capture(event: str, **fields: object) -> None:
        payloads.append({"event": event, **fields})

    monkeypatch.setattr(rt, "log_request_trace_event", capture)

    client = TestClient(_app())
    r = client.get("/api/v1/ping")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid and len(rid) >= 32

    assert len(payloads) >= 2
    start = next(p for p in payloads if p["event"] == "http.request.start")
    complete = next(p for p in payloads if p["event"] == "http.request.complete")
    assert start["request_id"] == rid == complete["request_id"]
    assert start["method"] == "GET"
    assert complete["status_code"] == 200
    assert complete["total_duration_ms"] >= 0
    assert any(s.get("name") == "handler.ping" for s in complete.get("stages", []))


def test_incoming_x_request_id_honored_when_valid() -> None:
    client = TestClient(_app())
    custom = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    r = client.get("/api/v1/ping", headers={"X-Request-ID": custom})
    assert r.headers.get("X-Request-ID") == custom


def test_parse_incoming_request_id_rejects_garbage() -> None:
    assert parse_incoming_request_id("ok-id-123") == "ok-id-123"
    assert parse_incoming_request_id("bad id") is None
    assert parse_incoming_request_id(None) is None


def test_request_trace_stage_noop_without_middleware() -> None:
    with request_trace_stage("orphan"):
        assert get_request_trace() is None
