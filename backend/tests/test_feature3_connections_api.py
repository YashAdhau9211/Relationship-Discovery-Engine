import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_connection_discovery_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.connections import ConnectionDiscoveryResponse, SecondDegreeConnectionResult
from app.schemas.entities import EntitySummary


def person(entity_id: str, name: str) -> EntitySummary:
    return EntitySummary(id=entity_id, label="Person", display_name=name, properties={"canonical_id": entity_id, "name": name})


class FakeConnectionDiscoveryService:
    def discover_connections(self, entity_id: str, degree: int = 2, limit: int = 50) -> ConnectionDiscoveryResponse:
        if entity_id == "person:missing":
            raise DomainError(404, "entity_not_found", f"Person '{entity_id}' was not found.", {"entity_id": entity_id})
        if degree != 2:
            raise DomainError(
                400,
                "unsupported_connection_degree",
                "Feature 3 supports degree=2 only.",
                {"requested_degree": degree, "supported_degree": 2},
            )
        result = SecondDegreeConnectionResult(
            entity=person("person:carla-singh", "Carla Singh"),
            score=0.83,
            shared_neighbor_count=1,
            jaccard=0.2,
            adamic_adar=0.721348,
            shared_neighbors=[person("person:ben-ortiz", "Ben Ortiz")],
            paths=[["person:alice-chen", "person:ben-ortiz", "person:carla-singh"]],
            explanation=Explanation(
                summary="Alice Chen is connected to Carla Singh through Ben Ortiz.",
                algorithms=["bounded_bfs_depth_2", "jaccard_coefficient", "adamic_adar"],
                evidence=[{"type": "shared_social_neighbor", "shared_neighbor_ids": ["person:ben-ortiz"], "path_count": 1}],
            ),
        )
        return ConnectionDiscoveryResponse(entity_id=entity_id, degree=degree, count=1, results=[result])


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_connection_discovery_service] = lambda: FakeConnectionDiscoveryService()
    return TestClient(app)


def test_second_degree_connections_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/connections", params={"degree": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == "person:alice-chen"
    assert body["degree"] == 2
    assert body["count"] == 1
    result = body["results"][0]
    assert result["entity"]["id"] == "person:carla-singh"
    assert result["shared_neighbor_count"] == 1
    assert result["shared_neighbors"][0]["id"] == "person:ben-ortiz"
    assert result["paths"] == [["person:alice-chen", "person:ben-ortiz", "person:carla-singh"]]
    assert "adamic_adar" in result
    assert "jaccard" in result
    assert "bounded_bfs_depth_2" in result["explanation"]["algorithms"]


def test_connections_missing_entity_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/connections", params={"degree": 2})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_connections_rejects_unsupported_degree_with_validation_error() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/connections", params={"degree": 4})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_includes_feature3_routes_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/connections" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "ConnectionDiscoveryResponse" in schemas
    assert "SecondDegreeConnectionResult" in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
