import pytest

from app.models.transcript_models import TranscriptTextChunk
from app.services.chapter_pipeline import build_segments, detect_chapter_ranges
from app.services.llm.mock_provider import MockLLMService


def test_detect_single_chunk_one_range() -> None:
    chunks = [TranscriptTextChunk(text="only one segment here", start_seconds=0.0)]
    assert detect_chapter_ranges(chunks) == [(0, 0)]


def test_disjoint_topics_but_short_spans_merge_to_one_range() -> None:
    """Very short single-chapter spans are merged (minimum chapter duration guard)."""
    chunks = [
        TranscriptTextChunk(text="alpha beta gamma delta epsilon zeta", start_seconds=0.0),
        TranscriptTextChunk(text="violet indigo blue green yellow orange red", start_seconds=300.0),
    ]
    ranges = detect_chapter_ranges(chunks)
    assert ranges == [(0, 1)]


def test_three_chunks_disjoint_middle_low_sim_three_ranges() -> None:
    chunks = [
        TranscriptTextChunk(text="aaa bbb ccc ddd eee fff", start_seconds=0.0),
        TranscriptTextChunk(text="ggg hhh iii jjj kkk lll", start_seconds=80.0),
        TranscriptTextChunk(text="mmm nnn ooo ppp qqq rrr", start_seconds=200.0),
    ]
    ranges = detect_chapter_ranges(chunks)
    assert len(ranges) >= 1
    assert ranges[0][0] == 0 and ranges[-1][1] == 2


def test_build_segments_matches_ranges() -> None:
    chunks = [
        TranscriptTextChunk(text="aaa bbb", start_seconds=0.0),
        TranscriptTextChunk(text="ccc ddd", start_seconds=10.0),
    ]
    segs = build_segments(chunks, [(0, 1)])
    assert len(segs) == 1
    assert segs[0].start_seconds == 0.0
    assert "aaa" in segs[0].text and "ddd" in segs[0].text


@pytest.mark.asyncio
async def test_build_video_chapters_mock_returns_aligned() -> None:
    from app.services.chapter_pipeline import build_video_chapters

    chunks = [
        TranscriptTextChunk(text="introduction welcome viewers", start_seconds=0.0),
        TranscriptTextChunk(text="conclusion thanks for watching", start_seconds=120.0),
    ]
    llm = MockLLMService()
    chapters = await build_video_chapters(chunks, llm)
    assert len(chapters) >= 1
    assert all(c.formatted_time for c in chapters)
    assert all(c.start_time >= 0 for c in chapters)
