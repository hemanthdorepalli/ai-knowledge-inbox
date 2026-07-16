"""Postgres (Supabase) connection pool with pgvector support.

Replaces the old SQLite layer. A small pool of connections is opened at
startup; each connection registers the pgvector type adapter so we can bind and
read numpy vectors directly. Rows come back as dicts.
"""

from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    # Teaches this connection how to translate between numpy arrays and the
    # Postgres `vector` type, so we can pass embeddings straight through.
    register_vector(conn)


def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.supabase_db_url,
            min_size=1,
            max_size=5,
            configure=_configure,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        logger.info("db_pool_opened")


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("db_pool_closed")


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() first")
    # The pool context commits on clean exit and rolls back on exception.
    with _pool.connection() as conn:
        yield conn
