"""Offline evaluation helpers for summary and Q&A quality (portfolio / smoke metrics)."""

from app.evaluation.models import (
    EvaluationAggregateMetrics,
    QuestionEvaluationResult,
    SummaryEvaluationResult,
    VideoEvaluationRun,
)
from app.evaluation.runner import CopilotEvaluationRunner, run_video_evaluation

__all__ = [
    "CopilotEvaluationRunner",
    "EvaluationAggregateMetrics",
    "QuestionEvaluationResult",
    "SummaryEvaluationResult",
    "VideoEvaluationRun",
    "run_video_evaluation",
]
