from fastapi import status


_TRANSCRIPT_NOT_FOUND_MESSAGES = (
    "No transcript was found for this video.",
    "Transcripts are disabled for this video.",
    "This video is unavailable.",
    "This video cannot be played; transcripts may be unavailable.",
    "This video is age-restricted; transcripts may be unavailable.",
)

_TRANSCRIPT_TEMPORARY_FAILURE_MESSAGES = (
    "YouTube blocked automated transcript access for this video",
    "YouTube blocked this request",
    "YouTube blocked this transcript request",
)

_TRANSCRIPT_UPSTREAM_FAILURE_MESSAGES = (
    "Could not retrieve the transcript for this video.",
    "Transcript fetch failed:",
    "Transcript was empty after cleaning.",
)


def transcript_fetch_status_code(detail: str) -> int:
    normalized = (detail or "").strip()

    if any(normalized.startswith(prefix) for prefix in _TRANSCRIPT_NOT_FOUND_MESSAGES):
        return status.HTTP_404_NOT_FOUND

    if any(normalized.startswith(prefix) for prefix in _TRANSCRIPT_TEMPORARY_FAILURE_MESSAGES):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    if any(normalized.startswith(prefix) for prefix in _TRANSCRIPT_UPSTREAM_FAILURE_MESSAGES):
        return status.HTTP_502_BAD_GATEWAY

    return status.HTTP_502_BAD_GATEWAY
