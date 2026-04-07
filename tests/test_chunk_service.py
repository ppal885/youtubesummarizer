import pytest

from app.config import Settings
from app.models.transcript_models import TranscriptItem
from app.services.chunk_service import (
    chunk_ranges,
    chunk_transcript_items,
    sentence_spans,
)


@pytest.fixture
def chunk_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Chunk-related env vars override .env so tests are deterministic."""
    monkeypatch.setenv("MAX_CHUNK_CHARS", "300")
    monkeypatch.setenv("CHUNK_OVERLAP_CHARS", "40")
    monkeypatch.setenv("CHUNK_USE_TOKENS", "false")
    return Settings()


def test_sentence_spans_on_punctuation_and_whitespace() -> None:
    text = "First one. Second one? Third!"
    spans = sentence_spans(text)
    assert spans == [(0, 10), (11, 22), (23, 29)]


def test_sentence_spans_no_punctuation_is_single_span() -> None:
    text = "no punctuation here"
    assert sentence_spans(text) == [(0, len(text))]


def test_sentence_spans_whitespace_only_is_empty() -> None:
    assert sentence_spans("   \n\t  ") == []


def test_chunk_ranges_is_deterministic(chunk_settings: Settings) -> None:
    merged = (
        "Alpha sentence here. Beta sentence follows. "
        "Gamma is third. Delta adds more. "
        "Epsilon speaks. Zeta closes the chunk story."
    ) * 4
    first = chunk_ranges(merged, chunk_settings)
    second = chunk_ranges(merged, chunk_settings)
    assert first == second
    assert len(first) >= 2
    for start, end in first:
        assert end - start <= chunk_settings.max_chunk_chars


def test_chunk_ranges_splits_oversized_sentence(chunk_settings: Settings) -> None:
    """A single 'sentence' longer than max triggers character fallback inside it."""
    long_run = "x" * 400
    merged = long_run + ". Tail end."
    ranges = chunk_ranges(merged, chunk_settings)
    assert len(ranges) >= 2
    for start, end in ranges:
        assert 0 <= start < end <= len(merged)
    assert ranges[-1][1] == len(merged)


def test_chunk_transcript_items_public_api(chunk_settings: Settings) -> None:
    items = [
        TranscriptItem(start=0.0, duration=1.0, text="Hello."),
        TranscriptItem(start=1.0, duration=1.0, text="World today."),
    ]
    chunks = chunk_transcript_items(items, chunk_settings)
    assert len(chunks) >= 1
    assert all(c.text.strip() for c in chunks)
    assert all(c.start_seconds >= 0 for c in chunks)


def test_chunk_ranges_token_mode_when_tiktoken_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tiktoken = pytest.importorskip("tiktoken")
    assert tiktoken is not None
    monkeypatch.setenv("CHUNK_USE_TOKENS", "true")
    monkeypatch.setenv("MAX_CHUNK_TOKENS", "35")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "6")
    monkeypatch.setenv("MAX_CHUNK_CHARS", "4000")
    monkeypatch.setenv("CHUNK_OVERLAP_CHARS", "200")
    settings = Settings()

    merged = (
        "Short opener. Another clause here. "
        "Third idea continues. Fourth wraps it up."
    ) * 3
    ranges = chunk_ranges(merged, settings)
    enc = tiktoken.get_encoding(settings.chunk_token_encoding)
    for start, end in ranges:
        tok_len = len(enc.encode(merged[start:end]))
        assert tok_len <= settings.max_chunk_tokens
