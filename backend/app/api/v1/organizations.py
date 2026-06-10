from fastapi import APIRouter, Depends, Query

from app.api.deps import get_organization_service
from app.schemas.organizations import SharedOrganizationsResponse
from app.services.organizations import OrganizationService

router = APIRouter()


@router.get("/{entity_id}/shared-orgs", response_model=SharedOrganizationsResponse)
def get_shared_organizations(
    entity_id: str,
    target: str = Query(..., description="Target Person canonical ID."),
    service: OrganizationService = Depends(get_organization_service),
) -> SharedOrganizationsResponse:
    return service.get_shared_organizations(source_id=entity_id, target_id=target)
