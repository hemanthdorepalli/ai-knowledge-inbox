"""Orchestrates the full ingest flow: normalize content -> chunk -> embed -> persist."""

from app import repository
from app.errors import EmptyContentError
from app.logging_config import get_logger
from app.schemas import IngestRequest, IngestResponse
from app.services import ingestion
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.vector_store import vector_index

logger = get_logger(__name__)


def run_ingest(request: IngestRequest) -> IngestResponse:
    if request.type == "note":
        raw_content = ingestion.normalize_note_content(request.content)
        title = request.title
        source_url = None
    else:
        title, raw_content = ingestion.fetch_url_content(request.url)
        title = request.title or title
        source_url = request.url

    chunks = chunk_text(raw_content)
    if not chunks:
        raise EmptyContentError("No content available to chunk after normalization")

    embeddings = embed_texts(chunks)

    item_id = repository.insert_item(
        type_=request.type, title=title, source_url=source_url, raw_content=raw_content
    )
    chunk_ids = repository.insert_chunks(item_id, chunks, embeddings)

    for chunk_id, embedding in zip(chunk_ids, embeddings):
        vector_index.add(chunk_id, embedding)

    item = repository.get_item(item_id)
    logger.info(
        "item_ingested item_id=%d type=%s chunks=%d", item_id, request.type, len(chunks)
    )

    return IngestResponse(
        id=item["id"],
        type=item["type"],
        title=item["title"],
        source_url=item["source_url"],
        created_at=item["created_at"],
        chunk_count=len(chunks),
    )
