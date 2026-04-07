from app.models.response_models import (
    AskCitationSource,
    AskResponse,
    FinalSummary,
    FlashcardItem,
    FlashcardsResponse,
    GlossaryTerm,
    KeyMoment,
    NotesResponse,
    VideoChapter,
)
from app.utils.output_normalizer import (
    normalize_ask_response,
    normalize_bullet_list,
    normalize_final_summary,
    normalize_flashcards_response,
    normalize_notes_response,
    normalize_timestamp_text,
)


def test_normalize_bullet_list_cleans_format_and_removes_duplicates() -> None:
    bullets = normalize_bullet_list(
        [
            " - First point  ",
            "* First point.",
            "2) Second point  !!",
            "• Third point  ....",
        ]
    )

    assert bullets == ["First point", "Second point!", "Third point..."]


def test_normalize_timestamp_text_standardizes_common_formats() -> None:
    assert normalize_timestamp_text("0:0") == "00:00"
    assert normalize_timestamp_text("1:2:3") == "01:02:03"
    assert normalize_timestamp_text("2m 3s") == "02:03"


def test_normalize_notes_response_normalizes_bullets_and_dedupes_glossary() -> None:
    response = NotesResponse(
        video_id="abc123",
        title="  Redis  Notes ",
        concise_notes="  * Fast cache \n * Fast cache \n 2) Durable storage ",
        detailed_notes=" - One benefit  \n - One benefit \n * Another benefit ",
        glossary_terms=[
            GlossaryTerm(term=" Redis ", definition=" in-memory store "),
            GlossaryTerm(term="redis", definition="duplicate"),
        ],
    )

    normalized = normalize_notes_response(response)

    assert normalized.title == "Redis Notes"
    assert normalized.concise_notes == "- Fast cache\n- Durable storage"
    assert normalized.detailed_notes == "- One benefit\n- Another benefit"
    assert normalized.glossary_terms == [GlossaryTerm(term="Redis", definition="in-memory store")]


def test_normalize_final_summary_cleans_bullets_and_timestamps() -> None:
    summary = FinalSummary(
        video_id="video-1",
        title="  Sample  Title ",
        summary="A short summary  !!",
        bullets=["- First point", "1) First point.", "* Second point  "],
        key_moments=[KeyMoment(time="0:08", note="  Opening note  ")],
        transcript_length=120,
        chunks_processed=2,
        learning_level="intermediate",
        suggested_questions=[" What is Redis? ", "What is Redis?"],
        chapters=[
            VideoChapter(
                title=" Intro ",
                start_time=8.0,
                formatted_time="0:08",
                short_summary="  Overview of Redis  ",
            )
        ],
    )

    normalized = normalize_final_summary(summary)

    assert normalized.title == "Sample Title"
    assert normalized.summary == "A short summary!"
    assert normalized.bullets == ["First point", "Second point"]
    assert normalized.key_moments[0].time == "00:08"
    assert normalized.key_moments[0].note == "Opening note"
    assert normalized.suggested_questions == ["What is Redis?"]
    assert normalized.chapters[0].formatted_time == "00:08"


def test_normalize_ask_response_dedupes_sources_and_normalizes_timestamp() -> None:
    response = AskResponse(
        answer="  Redis is a cache  ",
        sources=[
            AskCitationSource(start_time=0.0, formatted_time="0:0", text=" Redis is used for caching. "),
            AskCitationSource(start_time=0.0, formatted_time="00:00", text="Redis is used for caching."),
        ],
        confidence=0.8,
        confidence_score=0.6,
    )

    normalized = normalize_ask_response(response)

    assert normalized.answer == "Redis is a cache"
    assert len(normalized.sources) == 1
    assert normalized.sources[0].formatted_time == "00:00"


def test_normalize_flashcards_response_cleans_duplicate_cards() -> None:
    response = FlashcardsResponse(
        video_id="video-1",
        title=" Flashcards ",
        cards=[
            FlashcardItem(front=" What is Redis? ", back=" In-memory store ", timestamp_seconds=3.0, formatted_time=None),
            FlashcardItem(front="What is Redis?", back="In-memory store.", timestamp_seconds=3.0, formatted_time="0:03"),
        ],
    )

    normalized = normalize_flashcards_response(response)

    assert normalized.title == "Flashcards"
    assert len(normalized.cards) == 1
    assert normalized.cards[0].formatted_time == "00:03"
