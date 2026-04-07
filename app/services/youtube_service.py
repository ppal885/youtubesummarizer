import re
from urllib.parse import parse_qs, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

_YOUTUBE_ID_RE = re.compile(r"^[\w-]{11}$")


class _YouTubeOEmbedPayload(BaseModel):
    """Subset of oEmbed JSON; ignores unknown keys."""

    model_config = ConfigDict(extra="ignore")
    title: str | None = None


def _normalize_video_id(candidate: str | None) -> str | None:
    if not candidate:
        return None
    vid = candidate.strip()
    if _YOUTUBE_ID_RE.fullmatch(vid):
        return vid
    return None


def extract_video_id(url: str) -> str | None:
    """Extract an 11-character YouTube video id from common URL shapes."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")

    if "youtu.be" in host:
        first_segment = path.split("/")[0] if path else ""
        return _normalize_video_id(first_segment)

    if "youtube.com" in host or "m.youtube.com" in host or "youtube-nocookie.com" in host:
        if path == "watch" or path.startswith("watch/"):
            query = parse_qs(parsed.query)
            v_param = (query.get("v") or [None])[0]
            return _normalize_video_id(v_param)

        for prefix in ("embed", "shorts", "live", "v"):
            if path.startswith(prefix + "/"):
                segment = path.split("/")[1] if "/" in path else ""
                return _normalize_video_id(segment)

    return None


def fetch_video_title(video_url: str, timeout_seconds: float = 10.0) -> str:
    """Best-effort title via YouTube oEmbed (no API key)."""
    oembed_url = "https://www.youtube.com/oembed"
    try:
        response = httpx.get(
            oembed_url,
            params={"url": video_url, "format": "json"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = _YouTubeOEmbedPayload.model_validate(response.json())
    except (httpx.HTTPError, ValidationError, ValueError):
        return "Unknown title"

    if payload.title and payload.title.strip():
        return payload.title.strip()
    return "Unknown title"
