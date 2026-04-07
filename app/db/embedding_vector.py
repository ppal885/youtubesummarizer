"""Pgvector ``vector`` on PostgreSQL; JSON text on SQLite for local/tests without Postgres."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[misc, assignment]

from app.db.constants import VECTOR_STORAGE_DIMENSIONS


class EmbeddingVector(TypeDecorator[list[float] | None]):
    """Store float vectors: native ``vector`` on PostgreSQL, JSON array text on SQLite."""

    impl = Text
    cache_ok = True

    def __init__(self, dimension: int = VECTOR_STORAGE_DIMENSIONS) -> None:
        super().__init__()
        self.dimension = dimension

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(self.dimension))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[float] | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            if isinstance(value, (list, tuple)):
                return [float(x) for x in value]
            return [float(x) for x in list(value)]
        if isinstance(value, str):
            return [float(x) for x in json.loads(value)]
        return [float(x) for x in value]
