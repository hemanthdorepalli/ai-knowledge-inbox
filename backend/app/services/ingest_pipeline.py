"""Orchestrates the full ingest flow: get text -> chunk -> embed -> persist.

Three entry points (note, URL, document) share one persist step, so chunking,
embedding, and storage live in exactly one place.
"""

from app import repository
from app.errors import EmptyContentError
from app.logging_config import get_logger
from app.schemas import IngestRequest, IngestResponse
from app.services import documents, ingestion
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

logger = get_logger(__name__)


def run_ingest(request: IngestRequest, *, user_id: str) -> IngestResponse:
    if request.type == "note":
        raw_content = ingestion.normalize_note_content(request.content)
        title = request.title
        source_url = None
    else:  # url
        title, raw_content = ingestion.fetch_url_content(request.url)
        title = request.title or title
        source_url = request.url

    return _persist(
        user_id=user_id, type_=request.type, title=title, source_url=source_url, raw_content=raw_content
    )


def run_ingest_document(
    *, user_id: str, filename: str, data: bytes, title: str | None = None
) -> IngestResponse:
    extracted_title, raw_content = documents.extract_text(filename, data)
    return _persist(
        user_id=user_id,
        type_="document",
        title=title or extracted_title,
        source_url=None,
        raw_content=raw_content,
    )


def _persist(
    *, user_id: str, type_: str, title: str | None, source_url: str | None, raw_content: str
) -> IngestResponse:
    chunks = chunk_text(raw_content)
    if not chunks:
        raise EmptyContentError("No content available to chunk after normalization")

    embeddings = embed_texts(chunks)

    item = repository.insert_item(
        user_id=user_id, type_=type_, title=title, source_url=source_url, raw_content=raw_content
    )
    repository.insert_chunks(
        user_id=user_id, item_id=item["id"], chunk_texts=chunks, embeddings=embeddings
    )

    logger.info("item_ingested item_id=%s type=%s chunks=%d", item["id"], type_, len(chunks))

    return IngestResponse(
        id=str(item["id"]),
        type=item["type"],
        title=item["title"],
        source_url=item["source_url"],
        created_at=item["created_at"],
        chunk_count=len(chunks),
    )
