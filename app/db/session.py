from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base


def _sqlite_connect_args(url: str) -> dict[str, bool]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    connect_args=_sqlite_connect_args(settings.database_url),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create tables if they do not exist (MVP; no migrations)."""
    from app.db import models  # noqa: F401 — register ORM mappers

    url = settings.database_url.lower()
    if url.startswith("postgresql"):
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as exc:
            raise RuntimeError(
                "Could not run CREATE EXTENSION vector on PostgreSQL. "
                "Use a role with extension rights, or create the extension manually, then restart. "
                f"Detail: {exc}"
            ) from exc

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
