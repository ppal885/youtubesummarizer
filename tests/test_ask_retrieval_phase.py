from app.workflows.ask_retrieval_phase import merge_copilot_state
from app.workflows.ask_state import CopilotAskState


def test_merge_copilot_state_appends_errors() -> None:
    s = CopilotAskState()
    s = merge_copilot_state(s, {"errors": ["first"]})
    assert s.errors == ["first"]
    s = merge_copilot_state(s, {"errors": ["second"]})
    assert s.errors == ["first", "second"]


def test_merge_copilot_state_overwrites_other_keys() -> None:
    s = CopilotAskState(url="u", question="q")
    s = merge_copilot_state(s, {"video_id": "abc"})
    assert s.video_id == "abc"
