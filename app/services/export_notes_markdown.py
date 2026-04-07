"""Build markdown export documents from summary + learning assistant payloads."""

import re

from app.models.response_models import (
    FinalSummary,
    FlashcardsResponse,
    NotesResponse,
    QuizResponse,
)


def suggest_export_filename(video_id: str, title: str) -> str:
    """Safe, filesystem-friendly ``.md`` name (ASCII-ish slug + video id)."""
    raw = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", raw).strip("-").lower()
    if not slug:
        slug = "youtube-learning"
    slug = slug[:80]
    return f"{slug}-{video_id}.md"


def _neutralize_line_headings(text: str) -> str:
    """Prefix lines that look like ATX headings so user content cannot break section structure."""
    out_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            indent_len = len(line) - len(stripped)
            out_lines.append(f"{line[:indent_len]}\\{stripped}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _md_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def build_notes_export_markdown(
    summary: FinalSummary,
    notes: NotesResponse,
    quiz: QuizResponse,
    flashcards: FlashcardsResponse,
) -> str:
    """Assemble markdown with fixed top-level sections for downstream tools."""
    title_line = summary.title.strip() or "YouTube video"
    h1 = f"# {title_line}"

    summary_body = _neutralize_line_headings(summary.summary.strip() or "—")

    takeaway_lines = "\n".join(f"- {b.strip()}" for b in summary.bullets if b.strip()) or "- —"

    if summary.chapters:
        chapter_blocks: list[str] = []
        for ch in summary.chapters:
            chapter_blocks.append(
                f"### {ch.title} ({ch.formatted_time})\n\n"
                f"{_neutralize_line_headings(ch.short_summary.strip() or '—')}"
            )
        chapters_md = "\n\n".join(chapter_blocks)
    else:
        chapters_md = "_No chapters were generated for this video._"

    glossary_rows = ""
    if notes.glossary_terms:
        glossary_rows = "\n".join(
            f"| {_md_table_cell(g.term)} | {_md_table_cell(g.definition)} |"
            for g in notes.glossary_terms
        )
        glossary_md = (
            "| Term | Definition |\n| --- | --- |\n"
            f"{glossary_rows}\n"
        )
    else:
        glossary_md = "_No glossary terms._\n"

    concise = _neutralize_line_headings(notes.concise_notes.strip() or "—")
    detailed = _neutralize_line_headings(notes.detailed_notes.strip() or "—")

    flash_lines: list[str] = []
    for i, card in enumerate(flashcards.cards, start=1):
        front = _neutralize_line_headings(card.front.strip())
        back = _neutralize_line_headings(card.back.strip())
        time_hint = ""
        if card.formatted_time:
            time_hint = f" _({card.formatted_time})_"
        flash_lines.append(f"{i}. **Front:** {front}  \n   **Back:** {back}{time_hint}")
    flash_md = "\n\n".join(flash_lines) if flash_lines else "_No flashcards._"

    quiz_blocks: list[str] = []
    labels = ("a", "b", "c", "d")
    for i, q in enumerate(quiz.questions, start=1):
        opts = "\n".join(
            f"- **{labels[j]})** {_neutralize_line_headings(o.strip())}"
            for j, o in enumerate(q.options)
            if j < len(labels)
        )
        ans = _neutralize_line_headings(q.answer.strip())
        expl = _neutralize_line_headings(q.explanation.strip() or "—")
        qtext = _neutralize_line_headings(q.question.strip())
        quiz_blocks.append(
            f"### Question {i}\n\n{qtext}\n\n{opts}\n\n"
            f"**Answer:** {ans}  \n**Explanation:** {expl}"
        )
    quiz_md = "\n\n".join(quiz_blocks) if quiz_blocks else "_No quiz items._"

    parts = [
        h1,
        "",
        "## Summary",
        "",
        summary_body,
        "",
        "## Key Takeaways",
        "",
        takeaway_lines,
        "",
        "## Chapters",
        "",
        chapters_md,
        "",
        "## Notes",
        "",
        "### Concise",
        "",
        concise,
        "",
        "### Detailed",
        "",
        detailed,
        "",
        "### Glossary",
        "",
        glossary_md.rstrip(),
        "",
        "## Flashcards",
        "",
        flash_md,
        "",
        "## Quiz",
        "",
        quiz_md,
        "",
    ]
    return "\n".join(parts).strip() + "\n"
