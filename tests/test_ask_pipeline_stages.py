"""Unit tests for staged ask pipeline helpers (no LangGraph)."""

from app.workflows.ask_pipeline.state_merge import merge_pipeline_state
from app.workflows.ask_pipeline.transcript_stage import validate_input
from app.workflows.ask_state import CopilotAskState


def test_validate_input_sets_error_for_empty_question() -> None:
    state = CopilotAskState(url="https://www.youtube.com/watch?v=jNQXAC9IVRw", question="  ")
    patch = validate_input(state, {})
    merged = merge_pipeline_state(state, patch)
    assert merged.errors
    assert "empty" in merged.errors[0].lower()


def test_merge_pipeline_state_adds_perf_deltas() -> None:
    s = CopilotAskState()
    s = merge_pipeline_state(s, {"perf_transcript_fetch_ms": 12.5})
    s = merge_pipeline_state(s, {"perf_transcript_fetch_ms": 3.0})
    assert s.perf_transcript_fetch_ms == 15.5

    s2 = merge_pipeline_state(s, {"perf_llm_ms": 100.0})
    s2 = merge_pipeline_state(s2, {"perf_llm_ms": 0.5})
    assert s2.perf_llm_ms == 100.5


def test_merge_pipeline_state_appends_errors() -> None:
    s = CopilotAskState()
    s = merge_pipeline_state(s, {"errors": ["a"]})
    s = merge_pipeline_state(s, {"errors": ["b"]})
    assert s.errors == ["a", "b"]
