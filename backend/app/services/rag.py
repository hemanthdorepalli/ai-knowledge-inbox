from google.genai import errors, types

from app import repository
from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.schemas import SourceSnippet
from app.services.embeddings import embed_query
from app.services.gemini_client import client
from app.services.vector_store import vector_index

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using only the provided context "
    "snippets from the user's saved notes and pages. If the context does not contain "
    "enough information to answer, say so clearly instead of guessing. Keep answers "
    "concise and reference which source(s) you used."
)


def answer_question(question: str) -> tuple[str, list[SourceSnippet]]:
    query_embedding = embed_query(question)
    matches = vector_index.search(query_embedding, top_k=settings.top_k)

    if not matches:
        return (
            "I don't have any saved content yet, so I can't answer that. "
            "Add a note or URL first.",
            [],
        )

    chunk_ids = [chunk_id for chunk_id, _ in matches]
    chunk_details = repository.get_chunks_by_ids(chunk_ids)

    sources = [
        SourceSnippet(
            item_id=chunk_details[chunk_id]["item_id"],
            title=chunk_details[chunk_id]["title"],
            source_url=chunk_details[chunk_id]["source_url"],
            chunk_text=chunk_details[chunk_id]["chunk_text"],
            score=round(score, 4),
        )
        for chunk_id, score in matches
        if chunk_id in chunk_details
    ]

    context_block = "\n\n---\n\n".join(
        f"[Source {i + 1}] {s.title or s.source_url or 'Untitled'}\n{s.chunk_text}"
        for i, s in enumerate(sources)
    )

    user_prompt = (
        f"Context snippets:\n\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, and mention which source number(s) you used."
    )

    try:
        response = client.models.generate_content(
            model=settings.chat_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )
    except errors.APIError as exc:
        logger.error("chat_completion_failed error=%s", exc)
        raise LlmProviderError(f"Answer generation failed: {exc}") from exc

    answer = response.text or ""
    logger.info("query_answered question=%r sources=%d", question, len(sources))
    return answer, sources
