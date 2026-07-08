"""In-memory cosine-similarity vector index, persisted via the chunks table in SQLite.

Tradeoff (see README): a single-user, low-volume app doesn't need a dedicated
vector database. SQLite is the durable store; on process start we load every
chunk embedding into a numpy matrix and do a brute-force cosine similarity scan
per query. This is O(n) per query and rebuilt in memory on every restart -
intentional, and called out in the README as the first thing to swap out
(e.g. for pgvector or a proper ANN index) once item counts get large.
"""

import threading

import numpy as np

from app.db import get_connection
from app.logging_config import get_logger

logger = get_logger(__name__)


class VectorIndex:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunk_ids: list[int] = []
        self._embeddings: np.ndarray | None = None  # shape (n, dim), L2-normalized

    def load_from_db(self) -> None:
        with get_connection() as conn:
            rows = conn.execute("SELECT id, embedding FROM chunks ORDER BY id").fetchall()

        chunk_ids = [row["id"] for row in rows]
        vectors = [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]

        with self._lock:
            self._chunk_ids = chunk_ids
            self._embeddings = _normalize(np.vstack(vectors)) if vectors else None

        logger.info("vector_index_loaded chunks=%d", len(chunk_ids))

    def add(self, chunk_id: int, embedding: np.ndarray) -> None:
        normalized = _normalize(embedding.reshape(1, -1))
        with self._lock:
            self._chunk_ids.append(chunk_id)
            self._embeddings = (
                normalized
                if self._embeddings is None
                else np.vstack([self._embeddings, normalized])
            )

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        with self._lock:
            if self._embeddings is None or len(self._chunk_ids) == 0:
                return []
            chunk_ids = list(self._chunk_ids)
            embeddings = self._embeddings

        query = _normalize(query_embedding.reshape(1, -1))[0]
        scores = embeddings @ query  # cosine similarity, since rows are L2-normalized
        top_k = min(top_k, len(chunk_ids))
        top_indices = np.argpartition(-scores, top_k - 1)[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]

        return [(chunk_ids[i], float(scores[i])) for i in top_indices]


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


vector_index = VectorIndex()
