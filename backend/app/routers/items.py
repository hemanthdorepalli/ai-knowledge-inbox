from fastapi import APIRouter

from app import repository
from app.schemas import IngestRequest, IngestResponse, ItemSummary
from app.services.ingest_pipeline import run_ingest

router = APIRouter(tags=["items"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
def ingest(request: IngestRequest) -> IngestResponse:
    return run_ingest(request)


@router.get("/items", response_model=list[ItemSummary])
def list_items() -> list[ItemSummary]:
    return repository.list_items()
