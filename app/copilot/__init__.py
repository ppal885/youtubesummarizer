"""
Multi-agent copilot building blocks for transcript Q&A.

Agents are plain services with explicit :mod:`app.copilot.contracts` DTOs; the LangGraph
workflow in :mod:`app.workflows.ask_graph` wires stages from :mod:`app.workflows.ask_pipeline`.
"""

from app.copilot.answer_composer import AnswerComposerAgent
from app.copilot.contracts import (
    ComposerResult,
    TranscriptAnalystResult,
    TranscriptTheme,
    VerifierResult,
)
from app.copilot.retrieval_agent import RetrievalAgent
from app.copilot.transcript_analyst import TranscriptAnalystAgent
from app.copilot.verifier_agent import VerifierAgent

__all__ = [
    "AnswerComposerAgent",
    "ComposerResult",
    "RetrievalAgent",
    "TranscriptAnalystAgent",
    "TranscriptAnalystResult",
    "TranscriptTheme",
    "VerifierAgent",
    "VerifierResult",
]
