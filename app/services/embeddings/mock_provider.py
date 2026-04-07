import hashlib
import math
import struct

from app.config import Settings
from app.services.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-embeddings from text hashes (offline, no network)."""

    def __init__(self, settings: Settings) -> None:
        self._dim = settings.embedding_dimensions

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(_vector_from_text(t, self._dim)) for t in texts]


def _vector_from_text(text: str, dim: int) -> list[float]:
    buf = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    salt = 0
    while len(out) < dim:
        for i in range(0, len(buf) - 3, 4):
            if len(out) >= dim:
                return out
            out.append(struct.unpack("<f", buf[i : i + 4])[0])
        salt += 1
        buf = hashlib.sha256(buf + text.encode("utf-8") + struct.pack("<I", salt)).digest()
    return out


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return [0.0] * len(vec)
    return [x / norm for x in vec]
