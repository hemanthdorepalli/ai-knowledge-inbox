from fastapi import APIRouter, Depends

from app.auth import get_current_user_id
from app.schemas import QueryRequest, QueryResponse
from app.services.chat import handle_query

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest, user_id: str = Depends(get_current_user_id)
) -> QueryResponse:
    conversation_id, answer, sources, tool_calls = handle_query(
        user_id=user_id, question=request.question, conversation_id=request.conversation_id
    )
    return QueryResponse(
        answer=answer, sources=sources, conversation_id=conversation_id, tool_calls=tool_calls
    )
