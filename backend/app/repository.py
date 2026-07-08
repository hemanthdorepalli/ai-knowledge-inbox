"""Thin data-access layer over the items/chunks tables. No business logic here."""

from datetime import datetime, timezone

import numpy as np

from app.db import get_connection
from app.errors import ItemNotFoundError

SNIPPET_LENGTH = 200


def insert_item(
    *, type_: str, title: str | None, source_url: str | None, raw_content: str
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO items (type, title, source_url, raw_content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (type_, title, source_url, raw_content, created_at),
        )
        return cursor.lastrowid


def insert_chunks(item_id: int, chunk_texts: list[str], embeddings: list[np.ndarray]) -> list[int]:
    with get_connection() as conn:
        ids = []
        for index, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
            cursor = conn.execute(
                """
                INSERT INTO chunks (item_id, chunk_index, chunk_text, embedding)
                VALUES (?, ?, ?, ?)
                """,
                (item_id, index, text, embedding.astype(np.float32).tobytes()),
            )
            ids.append(cursor.lastrowid)
        return ids


def get_item(item_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise ItemNotFoundError(f"Item {item_id} not found")
    return dict(row)


def list_items() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT i.id, i.type, i.title, i.source_url, i.raw_content, i.created_at,
                   COUNT(c.id) AS chunk_count
            FROM items i
            LEFT JOIN chunks c ON c.item_id = i.id
            GROUP BY i.id
            ORDER BY i.created_at DESC
            """
        ).fetchall()

    items = []
    for row in rows:
        data = dict(row)
        content = data.pop("raw_content")
        data["snippet"] = content[:SNIPPET_LENGTH] + ("..." if len(content) > SNIPPET_LENGTH else "")
        items.append(data)
    return items


def get_chunks_by_ids(chunk_ids: list[int]) -> dict[int, dict]:
    if not chunk_ids:
        return {}
    placeholders = ",".join("?" for _ in chunk_ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT c.id AS chunk_id, c.chunk_text, c.item_id,
                   i.title, i.source_url
            FROM chunks c
            JOIN items i ON i.id = c.item_id
            WHERE c.id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()
    return {row["chunk_id"]: dict(row) for row in rows}
