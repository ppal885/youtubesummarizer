from youtube_transcript_api import (
    AgeRestricted,
    CouldNotRetrieveTranscript,
    FetchedTranscript,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    PoTokenRequired,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
    YouTubeTranscriptApiException,
)

from app.exceptions import TranscriptFetchError
from app.models.transcript_models import TranscriptItem
from app.utils.text_cleaner import merge_transcript_segments, normalize_whitespace


def _fetched_to_items(fetched: FetchedTranscript) -> list[TranscriptItem]:
    return [
        TranscriptItem(start=snippet.start, duration=snippet.duration, text=snippet.text)
        for snippet in fetched.snippets
    ]


def _dedupe_preserve_order(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def fetch_transcript_items(video_id: str, language: str) -> list[TranscriptItem]:
    """
    Fetch captions as typed models. Try requested language (plus English fallback when
    different), then any transcript available on the video.
    """
    api = YouTubeTranscriptApi()
    last_error: YouTubeTranscriptApiException | None = None

    lang_order = _dedupe_preserve_order([language, "en"] if language != "en" else [language])
    try:
        fetched = api.fetch(video_id, languages=lang_order)
        return _fetched_to_items(fetched)
    except YouTubeTranscriptApiException as exc:
        last_error = exc

    try:
        transcript_list = api.list(video_id)
        for transcript in transcript_list:
            try:
                fetched = transcript.fetch()
                return _fetched_to_items(fetched)
            except YouTubeTranscriptApiException:
                continue
    except YouTubeTranscriptApiException as exc:
        last_error = exc

    raise TranscriptFetchError(_transcript_error_message(video_id, last_error)) from last_error


def _transcript_error_message(
    video_id: str,
    exc: YouTubeTranscriptApiException | None,
) -> str:
    if exc is None:
        return f"No transcript could be fetched for video '{video_id}'."

    if isinstance(exc, TranscriptsDisabled):
        return "Transcripts are disabled for this video."
    if isinstance(exc, NoTranscriptFound):
        return "No transcript was found for this video."
    if isinstance(exc, VideoUnavailable):
        return "This video is unavailable."
    if isinstance(exc, VideoUnplayable):
        return "This video cannot be played; transcripts may be unavailable."
    if isinstance(exc, CouldNotRetrieveTranscript):
        return "Could not retrieve the transcript for this video."
    if isinstance(exc, InvalidVideoId):
        return "The video id appears to be invalid."
    if isinstance(exc, AgeRestricted):
        return "This video is age-restricted; transcripts may be unavailable."
    if isinstance(exc, PoTokenRequired):
        return (
            "YouTube blocked automated transcript access for this video "
            "(additional verification may be required)."
        )
    if isinstance(exc, IpBlocked):
        return "YouTube blocked this request (rate limit or IP); try again later."
    if isinstance(exc, RequestBlocked):
        return "YouTube blocked this transcript request; try again later."

    return f"Transcript fetch failed: {exc!s}"


def merge_transcript_text(items: list[TranscriptItem]) -> str:
    """Normalize and join all caption lines into one string."""
    texts = [normalize_whitespace(item.text) for item in items]
    return merge_transcript_segments(texts)
