from app.core.errors import DomainError
from app.schemas.connections import ConnectionDiscoveryResponse


class ConnectionDiscoveryService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def discover_connections(self, entity_id: str, degree: int = 2, limit: int = 50) -> ConnectionDiscoveryResponse:
        if degree == 2:
            results = self.repository.discover_second_degree(entity_id=entity_id, limit=limit)
        elif degree == 3:
            results = self.repository.discover_third_degree(entity_id=entity_id, limit=limit)
        else:
            raise DomainError(
                status_code=400,
                code="unsupported_connection_degree",
                message="Connection discovery supports degree=2 or degree=3.",
                details={"requested_degree": degree, "supported_degrees": [2, 3]},
            )
        return ConnectionDiscoveryResponse(entity_id=entity_id, degree=degree, count=len(results), results=results)
