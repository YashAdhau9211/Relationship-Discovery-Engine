import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_connection_discovery_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.connections import ConnectionDiscoveryResponse, IntermediateNode, ThirdDegreeConnectionResult
from app.schemas.entities import EntitySummary


def person(entity_id: str, name: str) -> EntitySummary:
    return EntitySummary(id=entity_id, label="Person", display_name=name, properties={"canonical_id": entity_id, "name": name})


class FakeThirdDegreeService:
    def discover_connections(self, entity_id: str, degree: int = 2, limit: int = 50) -> ConnectionDiscoveryResponse:
        result = ThirdDegreeConnectionResult(
            entity=person("person:david-kim", "David Kim"),
            score=0.71,
            path_count=1,
            katz_score=0.005**3,
            paths=[["person:alice-chen", "person:ben-ortiz", "person:carla-singh", "person:david-kim"]],
            intermediate_nodes=[
                IntermediateNode(id="person:ben-ortiz", label="Person", display_name="Ben Ortiz", centrality_rank=1, social_degree=4, properties={}),
                IntermediateNode(id="person:carla-singh", label="Person", display_name="Carla Singh", centrality_rank=2, social_degree=3, properties={}),
            ],
            explanation=Explanation(
                summary="Alice Chen is connected to David Kim through Ben Ortiz and Carla Singh.",
                algorithms=["bounded_bfs_depth_3", "katz_beta_0.005", "path_diversity"],
                evidence=[
                    {
                        "type": "third_degree_social_path",
                        "path_count": 1,
                        "sample_path": ["person:alice-chen", "person:ben-ortiz", "person:carla-singh", "person:david-kim"],
                    }
                ],
            ),
        )
        return ConnectionDiscoveryResponse(entity_id=entity_id, degree=degree, count=1, results=[result])


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_connection_discovery_service] = lambda: FakeThirdDegreeService()
    return TestClient(app)


def test_third_degree_connections_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/connections", params={"degree": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == "person:alice-chen"
    assert body["degree"] == 3
    result = body["results"][0]
    assert result["entity"]["id"] == "person:david-kim"
    assert result["path_count"] == 1
    assert result["katz_score"] == 0.005**3
    assert result["paths"] == [["person:alice-chen", "person:ben-ortiz", "person:carla-singh", "person:david-kim"]]
    assert result["intermediate_nodes"][0]["id"] == "person:ben-ortiz"
    assert "bounded_bfs_depth_3" in result["explanation"]["algorithms"]


def test_openapi_includes_feature4_schema() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "ThirdDegreeConnectionResult" in schemas
    assert "IntermediateNode" in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
