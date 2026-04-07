from fastapi.testclient import TestClient

from app.config import settings
from app.exceptions import TranscriptFetchError
from app.main import app
from app.models.response_models import FinalSummary
from app.routers.summarize import get_summary_job_service
from app.services.summary_job_service import SummaryJobService

client = TestClient(app)


class _SuccessSummaryService:
    async def summarize_from_url(self, request, *, trace_id: str) -> FinalSummary:
        return FinalSummary(
            video_id="abc123xyz89",
            title="Demo video",
            summary=f"Summary for {request.summary_type}",
            bullets=["one", "two"],
            key_moments=[{"time": "00:00", "note": "Opening"}],
            transcript_length=1234,
            chunks_processed=3,
            suggested_questions=["What changed?"],
            chapters=[
                {
                    "title": "Intro",
                    "start_time": 0.0,
                    "formatted_time": "00:00",
                    "short_summary": "Opening segment",
                }
            ],
        )


class _FailingSummaryService:
    async def summarize_from_url(self, request, *, trace_id: str) -> FinalSummary:
        raise TranscriptFetchError("Transcript is unavailable for this video.")


def test_summarize_returns_job_id_and_completed_status() -> None:
    service = SummaryJobService(
        settings=settings,
        summary_service_factory=lambda: _SuccessSummaryService(),
    )
    app.dependency_overrides[get_summary_job_service] = lambda: service

    try:
        response = client.post(
            "/api/v1/summarize",
            json={
                "url": "https://www.youtube.com/watch?v=abc123xyz89",
                "summary_type": "brief",
                "language": "en",
            },
        )

        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "queued"
        assert payload["job_id"]
        assert payload["status_url"] == f"/api/v1/status/{payload['job_id']}"

        status_response = client.get(payload["status_url"])
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["status"] == "completed"
        assert status_payload["result"]["summary"] == "Summary for brief"
        assert status_payload["result"]["video_id"] == "abc123xyz89"
        assert status_payload["summary_result_id"] is not None
    finally:
        app.dependency_overrides.clear()


def test_summarize_status_reports_failed_job() -> None:
    service = SummaryJobService(
        settings=settings,
        summary_service_factory=lambda: _FailingSummaryService(),
    )
    app.dependency_overrides[get_summary_job_service] = lambda: service

    try:
        response = client.post(
            "/api/v1/summarize",
            json={
                "url": "https://www.youtube.com/watch?v=abc123xyz89",
                "summary_type": "brief",
                "language": "en",
            },
        )

        assert response.status_code == 202
        payload = response.json()

        status_response = client.get(payload["status_url"])
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["status"] == "failed"
        assert status_payload["error"]["stage"] == "transcript_fetch"
        assert status_payload["error"]["type"] == "TranscriptFetchError"
        assert status_payload["error"]["detail"] == "Transcript is unavailable for this video."
        assert status_payload["result"] is None
    finally:
        app.dependency_overrides.clear()


def test_status_returns_404_for_unknown_job() -> None:
    response = client.get("/api/v1/status/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Summary job not found."}
