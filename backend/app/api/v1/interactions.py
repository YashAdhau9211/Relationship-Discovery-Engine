from fastapi import APIRouter, Depends, Query

from app.api.deps import get_interaction_service
from app.schemas.interactions import CommonInteractionsResponse
from app.services.interactions import InteractionService

router = APIRouter()


@router.get("/{entity_id}/common-interactions", response_model=CommonInteractionsResponse)
def get_common_interactions(
    entity_id: str,
    target: str = Query(..., description="Target Person canonical ID."),
    service: InteractionService = Depends(get_interaction_service),
) -> CommonInteractionsResponse:
    return service.get_common_interactions(source_id=entity_id, target_id=target)
