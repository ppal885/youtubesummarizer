"""Heuristic query understanding (used by mock LLM and as LLM fallback)."""

import pytest

from app.services.llm.schemas import QaQueryUnderstandingPayload
from app.services.query_understanding import (
    heuristic_query_understanding,
    merge_retrieval_query_text,
    run_query_understanding,
)
from app.services.llm.mock_provider import MockLLMService


def test_heuristic_definition_intent() -> None:
    p = heuristic_query_understanding("What is a vector database?")
    assert p.intent == "definition"
    assert "vector" in p.normalized_query.lower()


def test_heuristic_comparison_intent() -> None:
    p = heuristic_query_understanding("Compare Postgres vs Mongo for this use case")
    assert p.intent == "comparison"


def test_heuristic_conceptual_intent() -> None:
    p = heuristic_query_understanding("Why does the speaker prefer caching here?")
    assert p.intent == "conceptual"


def test_merge_retrieval_query_text_combines_keywords() -> None:
    payload = QaQueryUnderstandingPayload(
        intent="factual",
        normalized_query="elephant trunk length zoo",
        expansion_keywords=["pachyderm", "anatomy"],
    )
    merged = merge_retrieval_query_text(payload, fallback="ignored")
    assert "elephant" in merged and "pachyderm" in merged


def test_merge_retrieval_query_text_fallback() -> None:
    payload = QaQueryUnderstandingPayload(
        intent="factual",
        normalized_query="   ",
        expansion_keywords=[],
    )
    assert merge_retrieval_query_text(payload, fallback="  original  ") == "original"


@pytest.mark.asyncio
async def test_run_query_understanding_uses_mock_llm() -> None:
    llm = MockLLMService()
    p = await run_query_understanding("What is Redis?", llm)
    assert p.intent == "definition"
