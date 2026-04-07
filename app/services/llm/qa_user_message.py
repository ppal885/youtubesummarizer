from app.models.qa_models import TranscriptChunkPassage


def build_qa_user_prompt(
    question: str,
    passages: list[TranscriptChunkPassage],
    *,
    orientation_notes: str | None = None,
    evidence_synthesis_notes: str | None = None,
) -> str:
    """Format question + labeled transcript blocks for the chat model."""
    lines = [
        "Answer ONLY using the CONTEXT below. If CONTEXT does not contain the answer, output exactly: Not mentioned in video",
        "",
        "QUESTION:",
        question.strip(),
        "",
    ]
    if orientation_notes and orientation_notes.strip():
        lines.extend(
            [
                "ORIENTATION (not evidence — do not cite or treat as facts):",
                orientation_notes.strip(),
                "",
            ]
        )
    if evidence_synthesis_notes and evidence_synthesis_notes.strip():
        lines.extend([evidence_synthesis_notes.strip(), ""])
    lines.append("CONTEXT (transcript excerpts):")
    for passage in passages:
        lines.append(
            f"[chunk_index={passage.chunk_index} time={passage.time_display}]\n{passage.text.strip()}"
        )
        lines.append("---")
    if lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)
