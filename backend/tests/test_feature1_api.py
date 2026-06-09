from fastapi.testclient import TestClient

from app.api.deps import get_entity_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.entities import EntityDetail, EntitySearchResponse, EntitySummary
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStatistics


class FakeEntityService:
    def __init__(self) -> None:
        self.alice = EntityDetail(
            id="person:alice-chen",
            label="Person",
            display_name="Alice Chen",
            aliases=["A. Chen"],
            source_ids=["crm:1001"],
            properties={"name": "Alice Chen", "canonical_id": "person:alice-chen"},
        )

    def search_entities(self, query: str, limit: int = 25) -> EntitySearchResponse:
        if not query.strip() or "alice" not in query.lower():
            return EntitySearchResponse(query=query, count=0, results=[])
        result = EntitySummary(**self.alice.model_dump(exclude={"aliases", "source_ids"}))
        return EntitySearchResponse(query=query, count=1, results=[result])

    def get_entity(self, entity_id: str) -> EntityDetail:
        if entity_id != self.alice.id:
            raise DomainError(404, "entity_not_found", f"Entity '{entity_id}' was not found.", {"entity_id": entity_id})
        return self.alice

    def get_ego_graph(self, entity_id: str, depth: int = 1) -> GraphResponse:
        if entity_id != self.alice.id:
            raise DomainError(404, "entity_not_found", f"Entity '{entity_id}' was not found.", {"entity_id": entity_id})
        nodes = [
            GraphNode(id="person:alice-chen", label="Person", display_name="Alice Chen", properties={}),
            GraphNode(id="person:ben-ortiz", label="Person", display_name="Ben Ortiz", properties={}),
        ]
        edges = [
            GraphEdge(
                id="edge:1",
                source="person:alice-chen",
                target="person:ben-ortiz",
                type="FOLLOWS",
                directed=True,
                properties={"weight": 0.8},
            )
        ]
        return GraphResponse(
            center_id=entity_id,
            depth=depth,
            nodes=nodes,
            edges=edges,
            statistics=GraphStatistics(node_count=2, edge_count=1, depth=depth),
        )


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_entity_service] = lambda: FakeEntityService()
    return TestClient(app)


def test_health() -> None:
    client = make_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "test"


def test_settings_accept_comma_separated_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    settings = Settings()
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]


def test_entity_search_success() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/search", params={"q": "alice"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == "person:alice-chen"


def test_entity_search_empty() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/search", params={"q": "missing"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_entity_lookup_success() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen")
    assert response.status_code == 200
    assert response.json()["display_name"] == "Alice Chen"


def test_entity_lookup_missing_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_entity_graph_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/graph", params={"depth": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["center_id"] == "person:alice-chen"
    assert body["statistics"] == {"node_count": 2, "edge_count": 1, "depth": 1}
    assert body["nodes"][0].keys() >= {"id", "label", "display_name", "properties"}
    assert body["edges"][0].keys() >= {"id", "source", "target", "type", "directed", "properties"}


def test_validation_errors_use_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/graph", params={"depth": 2})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_includes_feature1_routes_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/search" in spec["paths"]
    assert "/api/v1/entities/{entity_id}" in spec["paths"]
    assert "/api/v1/entities/{entity_id}/graph" in spec["paths"]
    schemas = spec["components"]["schemas"]
    for name in ["EntitySummary", "GraphNode", "GraphEdge", "GraphResponse", "ApiError"]:
        assert name in schemas
