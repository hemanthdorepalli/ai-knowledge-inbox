from fastapi import APIRouter, Depends, File, Form, UploadFile

from app import repository
from app.auth import get_current_user_id
from app.schemas import IngestRequest, IngestResponse, ItemSummary
from app.services.ingest_pipeline import run_ingest, run_ingest_document

router = APIRouter(tags=["items"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
def ingest(
    request: IngestRequest, user_id: str = Depends(get_current_user_id)
) -> IngestResponse:
    return run_ingest(request, user_id=user_id)


@router.post("/ingest/document", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
) -> IngestResponse:
    data = await file.read()
    return run_ingest_document(
        user_id=user_id, filename=file.filename or "", data=data, title=title
    )


@router.get("/items", response_model=list[ItemSummary])
def list_items(user_id: str = Depends(get_current_user_id)) -> list[ItemSummary]:
    return repository.list_items(user_id=user_id)
