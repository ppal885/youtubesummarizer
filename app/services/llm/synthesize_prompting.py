"""System prompt and user payload for synthesizing several transcript-derived summaries under one topic."""

import json


MULTI_VIDEO_SYNTHESIS_SYSTEM = """You synthesize multiple YouTube videos for a single TOPIC. Each video is represented only by:
- title (from metadata or transcript context)
- summary (prose from transcript)
- bullets (key points from transcript)

Rules (critical):
- Use ONLY the text in the user message. Do not browse, invent statistics, or add facts from outside knowledge.
- The TOPIC tells you what to emphasize; ignore details that do not relate to that lens when possible, but do not fabricate connections.
- combined_summary: coherent prose that integrates what the videos collectively say about the topic (multiple short paragraphs allowed).
- common_ideas: short strings for ideas that genuinely recur or clearly align across at least two videos; empty array if none.
- differences: short strings for meaningful contrasts (tone, depth, recommendations, technical choices, etc.); each must be supported by the supplied summaries/bullets.
- best_explanation: 2–6 sentences naming which video title gives the clearest explanation of the most important part of the topic, OR a tight synthesis that explicitly weaves only what those videos state. Mention titles when comparing clarity.

Output MUST be a single JSON object with exactly these keys (no extras):
- "combined_summary" (string)
- "common_ideas" (array of strings)
- "differences" (array of strings)
- "best_explanation" (string)

No markdown outside JSON, no commentary."""


def build_multi_video_synthesis_user_message(
    *,
    topic: str,
    videos: list[tuple[int, str, str, str, list[str]]],
) -> str:
    """
    ``videos`` entries: ``(ordinal, video_id, title, summary, bullets)``.
    """
    blocks: list[str] = [
        f"TOPIC: {topic.strip()}\n",
        f"VIDEO_COUNT: {len(videos)}\n",
    ]
    for ordinal, video_id, title, summary, bullets in videos:
        blocks.append(
            f"VIDEO_{ordinal}:\n"
            f"video_id: {video_id}\n"
            f"title: {title}\n"
            f"summary: {summary}\n"
            f"bullets: {json.dumps(bullets, ensure_ascii=False)}\n",
        )
    return "\n".join(blocks)
