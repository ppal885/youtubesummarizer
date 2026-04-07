"""System prompt + user message for LLM-based RAG context compression."""

from app.models.retrieval_models import RetrievalHit

COMPRESS_QA_CONTEXT_SYSTEM = """You compress retrieved transcript excerpts for downstream Q&A.

Rules:
- Output ONLY valid JSON with a top-level key "items" (array).
- Produce exactly TARGET_COUNT objects (the user message states TARGET_COUNT).
- Each object must have: "summary" (string), "source_chunk_indices" (non-empty array of integers), "time_start_seconds" (number), optional "time_end_seconds" (number).
- Every fact in "summary" must appear in the cited excerpts (paraphrase allowed; do not invent).
- "source_chunk_indices" must be chunk_index values that appear in the RETRIEVAL blocks.
- Prefer merging adjacent low-value overlap; keep numbers, names, and causal claims when present.
- Keep summaries concise (roughly 2–6 sentences each) to save tokens.

Do not include markdown fences or commentary outside the JSON object."""


def build_compress_qa_user_message(question: str, hits: list[RetrievalHit], target_count: int) -> str:
    lines = [
        f"TARGET_COUNT: {target_count}",
        "",
        "QUESTION (use only to focus compression; do not answer it):",
        question.strip(),
        "",
        "RETRIEVAL (each block is one transcript chunk):",
    ]
    for h in hits:
        p = h.passage
        lines.append(f"[chunk_index={p.chunk_index} time={p.time_display}]")
        lines.append(p.text.strip())
        lines.append("---")
    if lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)
