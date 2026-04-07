"""Parse model output into validated Pydantic payloads."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def parse_llm_json_object(content: str, model: type[T]) -> T:
    """Strip optional markdown fences and validate JSON as the given model."""
    text = content.strip()
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"LLM JSON did not match expected schema: {exc}") from exc
