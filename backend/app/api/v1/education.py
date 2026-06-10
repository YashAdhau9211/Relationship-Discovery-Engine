from fastapi import APIRouter, Depends, Query

from app.api.deps import get_education_service
from app.schemas.education import SharedEducationResponse
from app.services.education import EducationService

router = APIRouter()


@router.get("/{entity_id}/shared-edu", response_model=SharedEducationResponse)
def get_shared_education(
    entity_id: str,
    target: str = Query(..., description="Target Person canonical ID."),
    service: EducationService = Depends(get_education_service),
) -> SharedEducationResponse:
    return service.get_shared_education(source_id=entity_id, target_id=target)
