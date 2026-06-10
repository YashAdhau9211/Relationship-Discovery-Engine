from fastapi import APIRouter, Depends, Query

from app.api.deps import get_connection_discovery_service
from app.schemas.connections import ConnectionDiscoveryResponse
from app.services.connections import ConnectionDiscoveryService

router = APIRouter()


@router.get("/{entity_id}/connections", response_model=ConnectionDiscoveryResponse)
def discover_connections(
    entity_id: str,
    degree: int = Query(default=2, ge=2, le=3, description="Use degree=2 for second-degree discovery or degree=3 for third-degree discovery."),
    limit: int = Query(default=50, ge=1, le=250),
    service: ConnectionDiscoveryService = Depends(get_connection_discovery_service),
) -> ConnectionDiscoveryResponse:
    return service.discover_connections(entity_id=entity_id, degree=degree, limit=limit)
