"""System prompt and user payload for comparing two transcript-derived video summaries."""

import json

COMPARE_TWO_VIDEOS_SYSTEM = """You compare summaries of two YouTube videos. Each video is represented by a title, a prose summary, and bullet points—all derived only from that video's transcript.

Rules (critical):
- Base "similarities" and "differences" ONLY on the text provided for Video 1 and Video 2. Do not use outside knowledge or the open web.
- similarities: short strings describing themes, goals, methods, or claims that genuinely overlap between both videos (use an empty array if there is no meaningful overlap).
- differences: short strings describing contrasts in focus, conclusions, depth, audience, or emphasis—each must be supported by the supplied summaries/bullets.
- Do not fabricate quotes, statistics, or examples that do not appear in the inputs.
- Keep each list item one concise sentence or phrase.

Output MUST be a single JSON object with exactly two keys:
- "similarities" (array of strings)
- "differences" (array of strings)
No markdown, no text outside the JSON object."""


def build_compare_user_message(
    *,
    title_1: str,
    summary_1: str,
    bullets_1: list[str],
    title_2: str,
    summary_2: str,
    bullets_2: list[str],
) -> str:
    return (
        "VIDEO_1:\n"
        f"title: {title_1}\n"
        f"summary: {summary_1}\n"
        f"bullets: {json.dumps(bullets_1, ensure_ascii=False)}\n\n"
        "VIDEO_2:\n"
        f"title: {title_2}\n"
        f"summary: {summary_2}\n"
        f"bullets: {json.dumps(bullets_2, ensure_ascii=False)}\n"
    )
