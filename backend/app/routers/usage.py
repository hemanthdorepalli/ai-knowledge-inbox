from fastapi import APIRouter, Depends

from app.auth import get_current_user_id
from app.schemas import UsageResponse
from app.services import usage as usage_service

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
def get_usage(user_id: str = Depends(get_current_user_id)) -> UsageResponse:
    data = usage_service.get_usage(user_id=user_id)
    return UsageResponse(
        tokens_used=data["tokens_used"],
        tokens_limit=data["tokens_limit"],
        tokens_remaining=max(0, data["tokens_limit"] - data["tokens_used"]),
        resets_at=usage_service.resets_at(data["period_started_at"]),
    )
