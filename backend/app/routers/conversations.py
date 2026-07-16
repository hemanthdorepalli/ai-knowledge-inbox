from fastapi import APIRouter, Depends

from app import repository
from app.auth import get_current_user_id
from app.schemas import ConversationSummary, MessageOut

router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(user_id: str = Depends(get_current_user_id)) -> list[ConversationSummary]:
    return repository.list_conversations(user_id=user_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: str, user_id: str = Depends(get_current_user_id)
) -> list[MessageOut]:
    # Ownership check: raises 404 if the conversation isn't the user's.
    repository.get_conversation(user_id=user_id, conversation_id=conversation_id)
    return repository.list_messages(user_id=user_id, conversation_id=conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, user_id: str = Depends(get_current_user_id)
) -> None:
    repository.delete_conversation(user_id=user_id, conversation_id=conversation_id)
