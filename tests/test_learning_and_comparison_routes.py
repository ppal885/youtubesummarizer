import pytest
from fastapi.testclient import TestClient

from app.exceptions import LLMInvocationError, TranscriptFetchError
from app.main import app
from app.routers.compare import get_compare_service
from app.routers.learning import get_learning_service
from app.routers.synthesize import get_synthesize_service


class _LearningSuccessService:
    async def notes(self, body):
        _ = body
        return {
            "video_id": "vid",
            "title": "Notes",
            "concise_notes": "short",
            "detailed_notes": "long",
            "glossary_terms": [],
        }

    async def quiz(self, body):
        _ = body
        return {
            "video_id": "vid",
            "title": "Quiz",
            "questions": [
                {
                    "question": "Q1",
                    "options": ["A", "B", "C", "D"],
                    "answer": "A",
                    "explanation": "Because",
                }
            ],
        }

    async def flashcards(self, body):
        _ = body
        return {
            "video_id": "vid",
            "title": "Cards",
            "cards": [{"front": "F", "back": "B", "timestamp_seconds": None, "formatted_time": None}],
        }

    async def interview_prep(self, body):
        _ = body
        return {
            "video_id": "vid",
            "title": "Interview",
            "key_questions": [{"question": "Q", "answer": "A"}],
            "system_design_insights": [],
            "edge_cases": [],
        }


class _LearningTranscriptFailureService(_LearningSuccessService):
    async def notes(self, body):
        _ = body
        raise TranscriptFetchError("YouTube blocked this transcript request; try again later.")

    quiz = notes
    flashcards = notes
    interview_prep = notes


class _LearningLlmFailureService(_LearningSuccessService):
    async def notes(self, body):
        _ = body
        raise LLMInvocationError("provider timed out")

    quiz = notes
    flashcards = notes
    interview_prep = notes


class _CompareSuccessService:
    async def compare_from_urls(self, body, trace_id: str):
        _ = body
        _ = trace_id
        return {
            "summary_1": "one",
            "summary_2": "two",
            "similarities": ["same"],
            "differences": ["diff"],
        }


class _CompareFailureService:
    async def compare_from_urls(self, body, trace_id: str):
        _ = body
        _ = trace_id
        raise LLMInvocationError("provider timed out")


class _SynthesizeSuccessService:
    async def synthesize_from_urls(self, body, trace_id: str):
        _ = body
        _ = trace_id
        return {
            "combined_summary": "combo",
            "common_ideas": ["one"],
            "differences": ["two"],
            "best_explanation": "best",
        }


class _SynthesizeFailureService:
    async def synthesize_from_urls(self, body, trace_id: str):
        _ = body
        _ = trace_id
        raise TranscriptFetchError("Could not retrieve the transcript for this video.")


@pytest.mark.parametrize(
    ("path", "service"),
    [
        ("/api/v1/notes", _LearningSuccessService()),
        ("/api/v1/quiz", _LearningSuccessService()),
        ("/api/v1/flashcards", _LearningSuccessService()),
        ("/api/v1/interview-prep", _LearningSuccessService()),
    ],
)
def test_learning_routes_happy_path(path: str, service) -> None:
    app.dependency_overrides[get_learning_service] = lambda: service
    client = TestClient(app)
    try:
        response = client.post(
            path,
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "language": "en",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/v1/notes", "/api/v1/quiz", "/api/v1/flashcards", "/api/v1/interview-prep"])
def test_learning_routes_map_transcript_blocking_to_503(path: str) -> None:
    app.dependency_overrides[get_learning_service] = lambda: _LearningTranscriptFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            path,
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "language": "en",
            },
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/v1/notes", "/api/v1/quiz", "/api/v1/flashcards", "/api/v1/interview-prep"])
def test_learning_routes_map_llm_failures_to_502(path: str) -> None:
    app.dependency_overrides[get_learning_service] = lambda: _LearningLlmFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            path,
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "language": "en",
            },
        )
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_compare_route_happy_path() -> None:
    app.dependency_overrides[get_compare_service] = lambda: _CompareSuccessService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/compare",
            json={
                "url_1": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "url_2": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "summary_type": "brief",
                "language": "en",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_compare_route_maps_llm_failure_to_502() -> None:
    app.dependency_overrides[get_compare_service] = lambda: _CompareFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/compare",
            json={
                "url_1": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "url_2": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "summary_type": "brief",
                "language": "en",
            },
        )
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_synthesize_route_happy_path() -> None:
    app.dependency_overrides[get_synthesize_service] = lambda: _SynthesizeSuccessService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/synthesize",
            json={
                "urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                ],
                "topic": "Caching",
                "summary_type": "brief",
                "language": "en",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_synthesize_route_maps_transcript_upstream_failure_to_502() -> None:
    app.dependency_overrides[get_synthesize_service] = lambda: _SynthesizeFailureService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/synthesize",
            json={
                "urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                ],
                "topic": "Caching",
                "summary_type": "brief",
                "language": "en",
            },
        )
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()
