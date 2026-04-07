"""Offline demo assets (precomputed summary and Q&A for a fixed sample video)."""

from app.demo.catalog import (
    DEMO_VIDEO_ID,
    DEMO_VIDEO_URL,
    demo_ask_response,
    demo_final_summary,
    is_demo_video_for_settings,
    stream_demo_answer_chunks,
)

__all__ = [
    "DEMO_VIDEO_ID",
    "DEMO_VIDEO_URL",
    "demo_ask_response",
    "demo_final_summary",
    "is_demo_video_for_settings",
    "stream_demo_answer_chunks",
]
