"""CLI entry: evaluate one video + question set; print JSON to stdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import settings
from app.db.session import init_db
from app.evaluation.runner import run_video_evaluation


def _load_questions(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Questions file must be a JSON array of strings.")
    out: list[str] = []
    for item in data:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Each question must be a non-empty string.")
        out.append(item.strip())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate summary faithfulness + Q&A metrics for one YouTube video.",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="YouTube video URL (must have captions).",
    )
    parser.add_argument(
        "--questions-file",
        type=Path,
        required=True,
        help='JSON file: ["question 1", "question 2", ...]',
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Caption language code (default: en).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write JSON results to this path (default: stdout only).",
    )
    args = parser.parse_args(argv)

    questions = _load_questions(args.questions_file)
    if not questions:
        print("No questions to evaluate (empty array).", file=sys.stderr)
        return 2

    init_db()

    run = run_video_evaluation(
        settings,
        video_url=args.url,
        questions=questions,
        language=args.language,
    )
    text = run.model_dump_json(indent=2)
    if args.output is not None:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
