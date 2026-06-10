from fastapi import APIRouter, Depends, Query

from app.api.deps import get_social_service
from app.schemas.social import MutualConnectionResponse, SocialConnectionsResponse, SocialProfileResponse
from app.services.social import SocialService

router = APIRouter()


@router.get("/{entity_id}/social", response_model=SocialProfileResponse)
def get_social_profile(
    entity_id: str,
    limit: int = Query(default=10, ge=1, le=100, description="Maximum top-list results per section."),
    service: SocialService = Depends(get_social_service),
) -> SocialProfileResponse:
    return service.get_social_profile(entity_id=entity_id, limit=limit)


@router.get("/{entity_id}/followers", response_model=SocialConnectionsResponse)
def get_followers(
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=250),
    service: SocialService = Depends(get_social_service),
) -> SocialConnectionsResponse:
    return service.get_followers(entity_id=entity_id, limit=limit)


@router.get("/{entity_id}/following", response_model=SocialConnectionsResponse)
def get_following(
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=250),
    service: SocialService = Depends(get_social_service),
) -> SocialConnectionsResponse:
    return service.get_following(entity_id=entity_id, limit=limit)


@router.get("/{entity_id}/friends", response_model=SocialConnectionsResponse)
def get_friends(
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=250),
    service: SocialService = Depends(get_social_service),
) -> SocialConnectionsResponse:
    return service.get_friends(entity_id=entity_id, limit=limit)


@router.get("/{entity_id}/mutuals", response_model=MutualConnectionResponse)
def get_mutuals(
    entity_id: str,
    target: str = Query(..., description="Target Person canonical ID."),
    limit: int = Query(default=50, ge=1, le=250),
    service: SocialService = Depends(get_social_service),
) -> MutualConnectionResponse:
    return service.get_mutuals(source_id=entity_id, target_id=target, limit=limit)
