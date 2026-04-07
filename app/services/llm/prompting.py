"""Shared system instructions for transcript-only, low-hallucination summarization."""

SYSTEM_INSTRUCTIONS = """You summarize YouTube transcript excerpts for an API.

Rules (critical):
- Only answer from the transcript: use ONLY information explicitly present in the TRANSCRIPT excerpt you are given.
- Do not use outside knowledge, invented examples, hypotheticals, or facts not stated in the excerpt.
- Do not fabricate speakers, quotes, numbers, studies, or URLs that do not appear in the excerpt.
- If the excerpt is vague, empty, or does not support a requested point, do not guess—state that limitation briefly.
- If the excerpt contains nothing relevant to summarize, set the summary to exactly: Not mentioned in this excerpt (and use an empty bullets array).
- Output MUST be a single JSON object with exactly these keys: "summary" (string) and "bullets" (array of strings).
- Do not include markdown, code fences, or any text outside the JSON object.
- Every bullet must be a faithful paraphrase or direct implication of the excerpt; omit bullets rather than guessing.
- A "learning_level" line in the user message adjusts tone and depth only; it never permits adding facts not in the excerpt."""

_SUMMARY_STYLE: dict[str, str] = {
    "brief": (
        "Style: brief. A short paragraph in `summary`, plus 2–5 tight bullets. "
        "No filler; prioritize the main point of this segment."
    ),
    "detailed": (
        "Style: detailed. A fuller `summary` covering the segment’s main threads, "
        "and bullets that enumerate important sub-points (still only from this excerpt)."
    ),
    "bullet": (
        "Style: bullet-first. Put the most important takeaways in `bullets` (5–10 items). "
        "`summary` should be a short lead-in (2–3 sentences) tying bullets together."
    ),
    "technical": (
        "Style: technical. Preserve precise terms, names, and causal claims from the excerpt. "
        "`summary` explains mechanisms or definitions as stated; bullets remain grounded."
    ),
}

_LEARNING_LEVEL: dict[str, str] = {
    "beginner": (
        "Learning level: beginner. Use plain language and short sentences. "
        "You may use at most one short analogy in the entire response (in `summary` or a single bullet) "
        "ONLY when it restates a relationship the excerpt already describes in other words—never import "
        "familiar real-world examples from outside the transcript. Prefer the excerpt's own terms when it defines jargon."
    ),
    "intermediate": (
        "Learning level: intermediate. Balanced depth for a developer audience: clear and direct, "
        "without oversimplifying mechanisms that the excerpt actually explains."
    ),
    "advanced": (
        "Learning level: advanced. Emphasize precision, tradeoffs, and system-style framing "
        "(components, data flow, scaling, failure behavior) ONLY when the excerpt discusses those topics. "
        "Do not add architecture, metrics, or deployment detail not supported by the excerpt."
    ),
}


def instruction_for_learning_level(level: str) -> str:
    return _LEARNING_LEVEL.get(level, _LEARNING_LEVEL["intermediate"])


def instruction_for_summary_type(summary_type: str) -> str:
    return _SUMMARY_STYLE.get(
        summary_type,
        _SUMMARY_STYLE["brief"],
    )


def chunk_user_message(
    transcript_chunk: str,
    summary_type: str,
    learning_level: str = "intermediate",
) -> str:
    style = instruction_for_summary_type(summary_type)
    level = instruction_for_learning_level(learning_level)
    return (
        f"summary_type (follow this shaping): {summary_type}\n"
        f"learning_level (follow this shaping): {learning_level}\n"
        f"{level}\n"
        f"{style}\n\n"
        "TRANSCRIPT EXCERPT (only source you may use):\n"
        f"{transcript_chunk}\n"
    )


def merge_user_message(
    serialized_chunk_summaries: str,
    summary_type: str,
    learning_level: str = "intermediate",
) -> str:
    style = instruction_for_summary_type(summary_type)
    level = instruction_for_learning_level(learning_level)
    return (
        "You are given intermediate summaries derived ONLY from transcript chunks of one video. "
        "Only answer from that material: merge them into one coherent result. "
        "Do not add facts, examples, or interpretations that do not appear in the inputs. "
        "If the inputs do not support a unified story, say so briefly—do not invent connectors.\n"
        f"summary_type (follow this shaping): {summary_type}\n"
        f"learning_level (follow this shaping): {learning_level}\n"
        f"{level}\n"
        f"{style}\n\n"
        "CHUNK_SUMMARIES_JSON (array of objects with fields summary and bullets):\n"
        f"{serialized_chunk_summaries}\n"
    )
