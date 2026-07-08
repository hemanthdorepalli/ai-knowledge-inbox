from fastapi import APIRouter

from app.schemas import QueryRequest, QueryResponse
from app.services.rag import answer_question

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    answer, sources = answer_question(request.question)
    return QueryResponse(answer=answer, sources=sources)
