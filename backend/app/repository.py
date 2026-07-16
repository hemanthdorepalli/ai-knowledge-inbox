"""Data-access layer over Postgres (Supabase). No business logic here.

Every function is scoped to a user_id, so a user only ever touches their own
rows. (Row-Level Security enforces the same thing at the database level once
real auth is wired in Phase 2 — this app-level scoping is defense in depth.)
"""

import numpy as np
from psycopg.types.json import Json

from app.db import get_connection
from app.errors import ItemNotFoundError

SNIPPET_LENGTH = 200


def insert_item(
    *, user_id: str, type_: str, title: str | None, source_url: str | None, raw_content: str
) -> dict:
    """Insert an item and return its stored row (id, type, title, source_url, created_at)."""
    with get_connection() as conn:
        return conn.execute(
            """
            INSERT INTO items (user_id, type, title, source_url, raw_content)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, type, title, source_url, created_at
            """,
            (user_id, type_, title, source_url, raw_content),
        ).fetchone()


def insert_chunks(
    *, user_id: str, item_id: str, chunk_texts: list[str], embeddings: list[np.ndarray]
) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for index, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
            cur.execute(
                """
                INSERT INTO chunks (user_id, item_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, item_id, index, text, np.asarray(embedding, dtype=np.float32)),
            )


def list_items(*, user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT i.id, i.type, i.title, i.source_url, i.raw_content, i.created_at,
                   COUNT(c.id) AS chunk_count
            FROM items i
            LEFT JOIN chunks c ON c.item_id = i.id
            WHERE i.user_id = %s
            GROUP BY i.id
            ORDER BY i.created_at DESC
            """,
            (user_id,),
        ).fetchall()

    items = []
    for row in rows:
        content = row.pop("raw_content")
        row["id"] = str(row["id"])
        row["snippet"] = content[:SNIPPET_LENGTH] + ("..." if len(content) > SNIPPET_LENGTH else "")
        items.append(row)
    return items


def search_chunks(*, user_id: str, query_embedding: np.ndarray, top_k: int) -> list[dict]:
    """Top-k most similar chunks for a user via the pgvector match_chunks function.

    Returns rows with: chunk_id, item_id, chunk_text, title, source_url, similarity.
    """
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM match_chunks(%s, %s, %s)",
            (np.asarray(query_embedding, dtype=np.float32), top_k, user_id),
        ).fetchall()


# --- Conversations & messages (chat history) ---------------------------------


def create_conversation(*, user_id: str, title: str | None) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO conversations (user_id, title)
            VALUES (%s, %s)
            RETURNING id, title, created_at, updated_at
            """,
            (user_id, title),
        ).fetchone()
    row["id"] = str(row["id"])
    return row


def get_conversation(*, user_id: str, conversation_id: str) -> dict:
    """Fetch a conversation owned by the user, or raise ItemNotFoundError."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        ).fetchone()
    if row is None:
        raise ItemNotFoundError("Conversation not found")
    row["id"] = str(row["id"])
    return row


def list_conversations(*, user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        row["id"] = str(row["id"])
    return rows


def delete_conversation(*, user_id: str, conversation_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )


def insert_message(
    *, user_id: str, conversation_id: str, role: str, content: str, sources: list | None
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (user_id, conversation_id, role, content, sources)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, conversation_id, role, content, Json(sources) if sources is not None else None),
        )


def touch_conversation(*, user_id: str, conversation_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )


def list_messages(*, user_id: str, conversation_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, sources, created_at
            FROM messages
            WHERE conversation_id = %s AND user_id = %s
            ORDER BY created_at ASC
            """,
            (conversation_id, user_id),
        ).fetchall()
    for row in rows:
        row["id"] = str(row["id"])
    return rows
