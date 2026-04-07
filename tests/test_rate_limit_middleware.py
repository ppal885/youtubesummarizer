"""In-memory API rate limiting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware, rate_limit_user_key


def _app_with_rate_limit(rpm: int = 2) -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"ok": "true"}

    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=rpm,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def test_rate_limit_returns_429_when_exceeded() -> None:
    client = TestClient(_app_with_rate_limit(rpm=2))
    assert client.get("/api/v1/ping").status_code == 200
    assert client.get("/api/v1/ping").status_code == 200
    r = client.get("/api/v1/ping")
    assert r.status_code == 429
    assert r.json()["detail"]
    assert "Retry-After" in r.headers


def test_rate_limit_skips_non_api_paths() -> None:
    client = TestClient(_app_with_rate_limit(rpm=1))
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200


def test_rate_limit_user_key_prefers_api_key_over_ip() -> None:
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [
            (b"x-api-key", b"secret-a"),
            (b"x-forwarded-for", b"203.0.113.1"),
        ],
        "client": ("127.0.0.1", 1234),
        "method": "GET",
        "scheme": "http",
        "server": ("test", 80),
        "path": "/api/v1/x",
        "query_string": b"",
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    req = Request(scope, receive)
    assert rate_limit_user_key(req) == "key:secret-a"
