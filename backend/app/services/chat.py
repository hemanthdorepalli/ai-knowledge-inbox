"""Chat orchestration: persist the conversation + messages around a RAG query.

Keeps rag.py focused on retrieval/answering; this layer handles the history
side-effects (create-or-continue a conversation, save both turns).
"""

from app import repository
from app.logging_config import get_logger
from app.schemas import SourceSnippet
from app.services.rag import answer_question

logger = get_logger(__name__)
TITLE_MAX_CHARS = 60


def handle_query(
    *, user_id: str, question: str, conversation_id: str | None
) -> tuple[str, str, list[SourceSnippet]]:
    # Continue an existing (owned) conversation, or start a new one titled from
    # the first question.
    if conversation_id:
        repository.get_conversation(user_id=user_id, conversation_id=conversation_id)
    else:
        conv = repository.create_conversation(
            user_id=user_id, title=question.strip()[:TITLE_MAX_CHARS]
        )
        conversation_id = conv["id"]

    repository.insert_message(
        user_id=user_id, conversation_id=conversation_id, role="user", content=question, sources=None
    )

    answer, sources = answer_question(question, user_id=user_id)

    repository.insert_message(
        user_id=user_id,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=[s.model_dump() for s in sources],
    )
    repository.touch_conversation(user_id=user_id, conversation_id=conversation_id)

    logger.info("chat_turn conversation_id=%s sources=%d", conversation_id, len(sources))
    return conversation_id, answer, sources
