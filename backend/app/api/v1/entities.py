from fastapi import APIRouter, Depends, Query

from app.api.deps import get_entity_service
from app.schemas.entities import EntityDetail, EntitySearchResponse
from app.schemas.graph import GraphResponse
from app.services.entities import EntityService

router = APIRouter()


@router.get("/search", response_model=EntitySearchResponse)
def search_entities(
    q: str = Query(default="", description="Case-insensitive entity name or ID search."),
    limit: int = Query(default=25, ge=1, le=100),
    service: EntityService = Depends(get_entity_service),
) -> EntitySearchResponse:
    return service.search_entities(query=q, limit=limit)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(
    entity_id: str,
    service: EntityService = Depends(get_entity_service),
) -> EntityDetail:
    return service.get_entity(entity_id)


@router.get("/{entity_id}/graph", response_model=GraphResponse)
def get_entity_graph(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=1, description="Feature 1 supports depth=1 only."),
    service: EntityService = Depends(get_entity_service),
) -> GraphResponse:
    return service.get_ego_graph(entity_id=entity_id, depth=depth)
