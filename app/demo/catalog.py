"""
Preloaded content for ``DEMO_MODE``: no YouTube fetch, transcript fetch, or LLM calls.

Sample: *Me at the zoo* (first public YouTube upload). Text is paraphrased from the
widely known ~19s clip so the demo reads naturally in the UI.
"""

from __future__ import annotations

import re

from app.config import Settings
from app.models.response_models import (
    AskCitationSource,
    AskResponse,
    DeveloperStudyDigest,
    FinalSummary,
    KeyMoment,
    VideoChapter,
)
from app.utils.output_normalizer import (
    normalize_ask_response,
    normalize_developer_digest,
    normalize_final_summary,
)

DEMO_VIDEO_ID = "jNQXAC9IVRw"
DEMO_VIDEO_TITLE = "Me at the zoo"
DEMO_VIDEO_URL = f"https://www.youtube.com/watch?v={DEMO_VIDEO_ID}"

_DEMO_TRANSCRIPT_SNIPPET = (
    "All right, so here we are in front of the elephants. The cool thing about these guys "
    "is that they have really, really long trunks, and that's cool. And that's pretty much all there is to say."
)

_DEMO_SOURCES = [
    AskCitationSource(
        start_time=0.0,
        formatted_time="0:00",
        text=_DEMO_TRANSCRIPT_SNIPPET[:220] + ("…" if len(_DEMO_TRANSCRIPT_SNIPPET) > 220 else ""),
    ),
]


def is_demo_video_for_settings(settings: Settings, video_id: str | None) -> bool:
    return bool(settings.demo_mode and video_id and video_id == DEMO_VIDEO_ID)


def demo_developer_digest() -> DeveloperStudyDigest:
    """Transcript-grounded developer digest for the demo clip (no code in the original upload)."""
    return normalize_developer_digest(DeveloperStudyDigest(
        concepts=[
            "Filming at a zoo, in front of the elephant enclosure.",
            "Elephants' trunks are called out as unusually long and interesting.",
        ],
        tools=[],
        patterns=[],
        best_practices=[],
        pitfalls=[],
        pseudo_code="",
        explanation=(
            "1. The speaker establishes they are at the zoo near the elephants. "
            "2. They focus on one observation: the elephants have very long trunks. "
            "3. They treat that trait as the main takeaway and wrap up the short clip."
        ),
    ))


def demo_final_summary() -> FinalSummary:
    return normalize_final_summary(FinalSummary(
        video_id=DEMO_VIDEO_ID,
        title=DEMO_VIDEO_TITLE,
        summary=(
            "In this very short clip, the speaker stands at the elephant exhibit at the zoo, "
            "points out how long their trunks are, and calls that neat—then signs off."
        ),
        bullets=[
            "Filmed at the zoo in front of the elephant enclosure.",
            "The speaker highlights elephants' long trunks as the main observation.",
            "Tone is casual; the clip ends after a quick remark.",
        ],
        key_moments=[
            KeyMoment(time="0:00", note="Introduction in front of the elephants at the zoo."),
            KeyMoment(time="0:08", note="Comment on how long the elephants' trunks are."),
        ],
        transcript_length=len(_DEMO_TRANSCRIPT_SNIPPET),
        chunks_processed=1,
        learning_level="intermediate",
        suggested_questions=[
            "What animal is the speaker standing in front of?",
            "What does the speaker say is cool about the elephants?",
            "How long is this clip in spirit—what happens before it ends?",
            "Where was this video filmed (setting)?",
            "Does the speaker say anything beyond the trunk observation?",
        ],
        chapters=[
            VideoChapter(
                title="Elephants at the zoo",
                start_time=0.0,
                formatted_time="0:00",
                short_summary="The speaker introduces the scene at the elephant exhibit and comments on their trunks.",
            )
        ],
    ))


def _normalize_q(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def demo_ask_response(question: str) -> AskResponse:
    n = _normalize_q(question)
    if "elephant" in n or "trunk" in n:
        answer = (
            "The speaker is in front of the elephants at the zoo. They say the cool thing about them "
            "is that they have really long trunks—that's the main fact called out in the clip."
        )
        confidence = 0.92
    elif "zoo" in n or "where" in n:
        answer = (
            "The video is shot at the zoo, in front of the elephant enclosure—the speaker says "
            'they are "here in front of the elephants."'
        )
        confidence = 0.9
    elif "cool" in n or "neat" in n or "interesting" in n:
        answer = (
            "The speaker thinks the elephants are cool mainly because of their very long trunks; "
            'they say that is "pretty much all there is to say" in this short clip.'
        )
        confidence = 0.88
    else:
        answer = (
            "This upload is a famous ~19-second clip: the speaker stands at the elephant exhibit, "
            "remarks on how long the elephants' trunks are, and wraps up. Ask about elephants, "
            "the zoo setting, or what they call “cool” for more detail."
        )
        confidence = 0.72

    return normalize_ask_response(AskResponse(
        answer=answer,
        sources=list(_DEMO_SOURCES),
        confidence=confidence,
        confidence_score=confidence,
    ))


def stream_demo_answer_chunks(answer: str, *, words_per_chunk: int = 4) -> list[str]:
    """Split demo answer into small token-like chunks for SSE (no real LLM stream)."""
    words = answer.split()
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(words):
        part = words[i : i + words_per_chunk]
        piece = " ".join(part)
        if i + words_per_chunk < len(words):
            piece += " "
        chunks.append(piece)
        i += words_per_chunk
    return chunks
