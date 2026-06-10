from fastapi import APIRouter, Depends, Query

from app.api.deps import get_location_service
from app.schemas.locations import SharedLocationsResponse
from app.services.locations import LocationService

router = APIRouter()


@router.get("/{entity_id}/shared-locations", response_model=SharedLocationsResponse)
def get_shared_locations(
    entity_id: str,
    target: str = Query(..., description="Target Person canonical ID."),
    service: LocationService = Depends(get_location_service),
) -> SharedLocationsResponse:
    return service.get_shared_locations(source_id=entity_id, target_id=target)
