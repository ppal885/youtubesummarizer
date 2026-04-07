from fastapi import status

from app.routers.error_mapping import transcript_fetch_status_code


def test_transcript_missing_maps_to_404() -> None:
    assert (
        transcript_fetch_status_code("No transcript was found for this video.")
        == status.HTTP_404_NOT_FOUND
    )


def test_transcript_blocked_maps_to_503() -> None:
    assert (
        transcript_fetch_status_code(
            "YouTube blocked automated transcript access for this video (additional verification may be required)."
        )
        == status.HTTP_503_SERVICE_UNAVAILABLE
    )


def test_transcript_upstream_failure_maps_to_502() -> None:
    assert (
        transcript_fetch_status_code("Could not retrieve the transcript for this video.")
        == status.HTTP_502_BAD_GATEWAY
    )


def test_unknown_transcript_failure_defaults_to_502() -> None:
    assert (
        transcript_fetch_status_code("Something unexpected happened while fetching captions.")
        == status.HTTP_502_BAD_GATEWAY
    )
