from app.models.response_models import (
    FinalSummary,
    FlashcardItem,
    FlashcardsResponse,
    GlossaryTerm,
    KeyMoment,
    NotesResponse,
    QuizQuestionItem,
    QuizResponse,
    VideoChapter,
)
from app.services.export_notes_markdown import build_notes_export_markdown, suggest_export_filename


def test_suggest_export_filename_sanitizes_and_includes_id() -> None:
    name = suggest_export_filename("abc123", 'Hello: World / Test "Video"!!!')
    assert name.endswith("-abc123.md")
    assert "hello" in name
    assert ":" not in name


def test_build_notes_export_markdown_includes_sections() -> None:
    final = FinalSummary(
        video_id="vid",
        title="My Video",
        summary="Main idea.",
        bullets=["First point", "Second point"],
        key_moments=[KeyMoment(time="00:01", note="n")],
        transcript_length=10,
        chunks_processed=1,
        chapters=[
            VideoChapter(
                title="Intro",
                start_time=0.0,
                formatted_time="00:00",
                short_summary="Opening.",
            )
        ],
    )
    notes = NotesResponse(
        video_id="vid",
        title="My Video",
        concise_notes="Short.",
        detailed_notes="Longer.",
        glossary_terms=[GlossaryTerm(term="T1", definition="D1")],
    )
    quiz = QuizResponse(
        video_id="vid",
        title="My Video",
        questions=[
            QuizQuestionItem(
                question="Q1?",
                options=["A", "B", "C", "D"],
                answer="A",
                explanation="Because.",
            )
        ],
    )
    flash = FlashcardsResponse(
        video_id="vid",
        title="My Video",
        cards=[
            FlashcardItem(front="F", back="B", timestamp_seconds=1.0, formatted_time="00:01"),
        ],
    )
    md = build_notes_export_markdown(final, notes, quiz, flash)
    assert "# My Video" in md
    assert "## Summary" in md
    assert "Main idea." in md
    assert "## Key Takeaways" in md
    assert "- First point" in md
    assert "## Chapters" in md
    assert "### Intro" in md
    assert "## Notes" in md
    assert "### Glossary" in md
    assert "| T1 | D1 |" in md
    assert "## Flashcards" in md
    assert "**Front:** F" in md
    assert "## Quiz" in md
    assert "**Answer:** A" in md


def test_neutralize_heading_in_user_content() -> None:
    final = FinalSummary(
        video_id="v",
        title="T",
        summary="# not a real heading",
        bullets=[],
        key_moments=[],
        transcript_length=1,
        chunks_processed=1,
    )
    notes = NotesResponse(
        video_id="v",
        title="T",
        concise_notes="x",
        detailed_notes="y",
        glossary_terms=[],
    )
    quiz = QuizResponse(video_id="v", title="T", questions=[])
    flash = FlashcardsResponse(video_id="v", title="T", cards=[])
    md = build_notes_export_markdown(final, notes, quiz, flash)
    assert "\\# not a real heading" in md
