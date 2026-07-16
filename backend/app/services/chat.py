"""Chat orchestration: persist the conversation + messages around a RAG query.

Keeps rag.py focused on retrieval/answering; this layer handles the history
side-effects (create-or-continue a conversation, save both turns).
"""

from app import repository
from app.logging_config import get_logger
from app.schemas import SourceSnippet, ToolCallInfo
from app.services.rag import answer_question

logger = get_logger(__name__)
TITLE_MAX_CHARS = 60


def handle_query(
    *, user_id: str, question: str, conversation_id: str | None
) -> tuple[str, str, list[SourceSnippet], list[ToolCallInfo]]:
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

    answer, sources, tool_calls = answer_question(question, user_id=user_id)

    repository.insert_message(
        user_id=user_id,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=[s.model_dump() for s in sources],
        tool_calls=[t.model_dump() for t in tool_calls] if tool_calls else None,
    )
    repository.touch_conversation(user_id=user_id, conversation_id=conversation_id)

    logger.info(
        "chat_turn conversation_id=%s sources=%d tool_calls=%d",
        conversation_id, len(sources), len(tool_calls),
    )
    return conversation_id, answer, sources, tool_calls
