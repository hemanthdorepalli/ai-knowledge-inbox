from google.genai import errors, types

from app import repository
from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.schemas import SourceSnippet
from app.services import usage
from app.services.embeddings import embed_query
from app.services.gemini_client import client

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using only the provided context "
    "snippets from the user's saved notes and pages. If the context does not contain "
    "enough information to answer, say so clearly instead of guessing. Keep answers "
    "concise and reference which source(s) you used."
)


def answer_question(question: str, *, user_id: str) -> tuple[str, list[SourceSnippet]]:
    # A query costs at least the embedding of the question; the chat call's
    # exact cost isn't known until it returns, so we just require some
    # headroom before starting and record the precise total afterward.
    usage.check_quota(user_id=user_id, needed_tokens=usage.estimate_tokens(question))

    query_embedding = embed_query(question)
    embed_tokens = usage.estimate_tokens(question)

    matches = repository.search_chunks(
        user_id=user_id, query_embedding=query_embedding, top_k=settings.top_k
    )

    if not matches:
        usage.record_usage(user_id=user_id, tokens=embed_tokens)
        return (
            "I don't have any saved content yet, so I can't answer that. "
            "Add a note or URL first.",
            [],
        )

    sources = [
        SourceSnippet(
            item_id=str(m["item_id"]),
            title=m["title"],
            source_url=m["source_url"],
            chunk_text=m["chunk_text"],
            score=round(float(m["similarity"]), 4),
        )
        for m in matches
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
        usage.record_usage(user_id=user_id, tokens=embed_tokens)
        logger.error("chat_completion_failed error=%s", exc)
        raise LlmProviderError(f"Answer generation failed: {exc}") from exc

    answer = response.text or ""

    chat_tokens = (
        response.usage_metadata.total_token_count
        if response.usage_metadata and response.usage_metadata.total_token_count
        else usage.estimate_tokens(user_prompt) + usage.estimate_tokens(answer)
    )
    usage.record_usage(user_id=user_id, tokens=embed_tokens + chat_tokens)

    logger.info("query_answered question=%r sources=%d tokens=%d", question, len(sources), embed_tokens + chat_tokens)
    return answer, sources
