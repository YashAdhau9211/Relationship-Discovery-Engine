import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_social_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.entities import EntitySummary
from app.schemas.social import MutualConnectionResponse, SocialConnection, SocialConnectionsResponse, SocialProfileResponse


def person(entity_id: str, name: str) -> EntitySummary:
    return EntitySummary(id=entity_id, label="Person", display_name=name, properties={"canonical_id": entity_id, "name": name})


class FakeSocialService:
    def __init__(self, zero_following: bool = False) -> None:
        self.zero_following = zero_following
        self.alice = "person:alice-chen"
        self.ben = SocialConnection(
            entity=person("person:ben-ortiz", "Ben Ortiz"),
            relationship_type="FOLLOWS",
            direction="outgoing",
            weight=0.88,
            platform="bridge-follow",
            timestamp="2026-02-01T00:00:00Z",
            properties={"weight": 0.88, "platform": "bridge-follow"},
        )
        self.kavya = SocialConnection(
            entity=person("person:kavya-raman", "Kavya Raman"),
            relationship_type="FRIENDS_WITH",
            direction="undirected",
            weight=0.72,
            platform="synthetic-social",
            timestamp="2026-01-10T00:00:00Z",
            properties={"mutual": True},
        )

    def _missing(self, entity_id: str) -> None:
        if entity_id == "person:missing":
            raise DomainError(404, "entity_not_found", f"Person '{entity_id}' was not found.", {"entity_id": entity_id})

    def get_social_profile(self, entity_id: str, limit: int = 10) -> SocialProfileResponse:
        self._missing(entity_id)
        following = [] if self.zero_following else [self.ben]
        return SocialProfileResponse(
            entity_id=entity_id,
            follower_count=2,
            following_count=0 if self.zero_following else 1,
            friend_count=1,
            mutual_count=1,
            follow_ratio=None if self.zero_following else 2.0,
            platform_distribution={"synthetic-social": 2, "bridge-follow": 1},
            top_followers=[self.ben],
            top_following=following,
            friends=[self.kavya],
        )

    def get_followers(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        self._missing(entity_id)
        return SocialConnectionsResponse(entity_id=entity_id, relationship_type="FOLLOWS", direction="incoming", count=1, results=[self.ben])

    def get_following(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        self._missing(entity_id)
        return SocialConnectionsResponse(entity_id=entity_id, relationship_type="FOLLOWS", direction="outgoing", count=1, results=[self.ben])

    def get_friends(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        self._missing(entity_id)
        return SocialConnectionsResponse(entity_id=entity_id, relationship_type="FRIENDS_WITH", direction="undirected", count=1, results=[self.kavya])

    def get_mutuals(self, source_id: str, target_id: str, limit: int = 50) -> MutualConnectionResponse:
        self._missing(source_id)
        return MutualConnectionResponse(source_id=source_id, target_id=target_id, count=1, mutuals=[self.kavya])


def make_client(service=None) -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_social_service] = lambda: service or FakeSocialService()
    return TestClient(app)


def test_social_profile_summary() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/social")
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == "person:alice-chen"
    assert body["follower_count"] == 2
    assert body["following_count"] == 1
    assert body["friend_count"] == 1
    assert body["mutual_count"] == 1
    assert body["follow_ratio"] == 2.0
    assert body["platform_distribution"]["bridge-follow"] == 1


def test_followers_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/followers")
    assert response.status_code == 200
    assert response.json()["direction"] == "incoming"


def test_following_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/following")
    assert response.status_code == 200
    assert response.json()["direction"] == "outgoing"


def test_friends_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/friends")
    assert response.status_code == 200
    body = response.json()
    assert body["relationship_type"] == "FRIENDS_WITH"
    assert body["direction"] == "undirected"


def test_mutuals_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/mutuals", params={"target": "person:david-kim"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "person:alice-chen"
    assert body["target_id"] == "person:david-kim"
    assert body["count"] == 1


def test_social_missing_entity_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/social")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_zero_following_count_has_null_ratio() -> None:
    client = make_client(FakeSocialService(zero_following=True))
    response = client.get("/api/v1/entities/person:alice-chen/social")
    assert response.status_code == 200
    assert response.json()["following_count"] == 0
    assert response.json()["follow_ratio"] is None


def test_openapi_includes_feature2_routes_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/social" in spec["paths"]
    assert "/api/v1/entities/{entity_id}/followers" in spec["paths"]
    assert "/api/v1/entities/{entity_id}/following" in spec["paths"]
    assert "/api/v1/entities/{entity_id}/friends" in spec["paths"]
    assert "/api/v1/entities/{entity_id}/mutuals" in spec["paths"]
    schemas = spec["components"]["schemas"]
    for name in ["SocialProfileResponse", "SocialConnection", "SocialConnectionsResponse", "MutualConnectionResponse"]:
        assert name in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
