import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_interaction_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.interactions import CommonInteractionsResponse, DirectInteraction, SharedInteractionTarget
from app.services.interactions import InteractionService


class FakeInteractionService:
    def get_common_interactions(self, source_id: str, target_id: str) -> CommonInteractionsResponse:
        if source_id == "person:missing" or target_id == "person:missing":
            missing_id = "person:missing"
            raise DomainError(404, "entity_not_found", f"Person '{missing_id}' was not found.", {"entity_id": missing_id})
        if target_id == "person:no-common-interactions":
            return CommonInteractionsResponse(
                source_id=source_id,
                target_id=target_id,
                direct_interaction_count=0,
                shared_target_count=0,
                resource_allocation_score=0.0,
                recency_score=0.0,
                composite_score=0.0,
                direct_interactions=[],
                shared_targets=[],
                explanation=Explanation(summary="No common interaction evidence.", algorithms=[], evidence=[]),
            )
        if target_id == "person:ben-ortiz":
            return CommonInteractionsResponse(
                source_id=source_id,
                target_id=target_id,
                direct_interaction_count=12,
                shared_target_count=0,
                resource_allocation_score=0.0,
                recency_score=0.94,
                composite_score=0.538,
                direct_interactions=[
                    DirectInteraction(
                        source_id="person:alice-chen",
                        target_id="person:ben-ortiz",
                        relationship_type="INTERACTED_WITH",
                        interaction_type="message",
                        count=12,
                        platform="synthetic-logs",
                        recency_score=0.94,
                        timestamps=["2026-04-20T10:00:00Z"],
                        properties={"count": 12},
                    )
                ],
                shared_targets=[],
                explanation=Explanation(
                    summary="Direct interaction evidence.",
                    algorithms=["direct_interaction_count", "recency_weighted_interaction_score"],
                    evidence=[],
                ),
            )
        shared_target = SharedInteractionTarget(
            target=EntitySummary(
                id="event:encrypted-call-alpha",
                label="Event",
                display_name="event:encrypted-call-alpha",
                properties={"type": "call", "platform": "signal"},
            ),
            source_interaction_count=2,
            target_interaction_count=2,
            target_total_interactors=4,
            resource_allocation_contribution=0.25,
            interaction_types=["call", "event_engagement"],
            recency_score=0.68,
            relationship_types=["CO_OCCURRED_IN", "INTERACTED_WITH"],
        )
        return CommonInteractionsResponse(
            source_id=source_id,
            target_id=target_id,
            direct_interaction_count=0,
            shared_target_count=1,
            resource_allocation_score=0.25,
            recency_score=0.68,
            composite_score=0.2385,
            direct_interactions=[],
            shared_targets=[shared_target],
            explanation=Explanation(
                summary="Shared common interaction targets.",
                algorithms=["common_interaction_targets", "resource_allocation_index", "recency_weighted_interaction_score"],
                evidence=[{"type": "common_interactions_summary"}],
            ),
        )


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_interaction_service] = lambda: FakeInteractionService()
    return TestClient(app)


def test_common_interactions_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/common-interactions", params={"target": "person:david-kim"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "person:alice-chen"
    assert body["target_id"] == "person:david-kim"
    assert body["direct_interaction_count"] == 0
    assert body["shared_target_count"] == 1
    assert body["resource_allocation_score"] == 0.25
    assert body["composite_score"] == 0.2385
    assert body["shared_targets"][0]["target"]["id"] == "event:encrypted-call-alpha"
    assert "resource_allocation_index" in body["explanation"]["algorithms"]


def test_direct_interaction_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/common-interactions", params={"target": "person:ben-ortiz"})
    assert response.status_code == 200
    body = response.json()
    assert body["direct_interaction_count"] == 12
    assert body["direct_interactions"][0]["interaction_type"] == "message"
    assert body["direct_interactions"][0]["recency_score"] == 0.94


def test_common_interactions_empty_result() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/common-interactions", params={"target": "person:no-common-interactions"})
    assert response.status_code == 200
    assert response.json()["shared_target_count"] == 0
    assert response.json()["direct_interaction_count"] == 0


def test_common_interactions_missing_person_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/common-interactions", params={"target": "person:david-kim"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_resource_allocation_contribution() -> None:
    assert InteractionService._resource_allocation_contribution(4) == 0.25
    assert InteractionService._resource_allocation_contribution(0) == 0.0


def test_composite_score_combines_direct_shared_ra_and_recency() -> None:
    score = InteractionService._composite_score(
        direct_interaction_count=0,
        shared_target_count=1,
        resource_allocation_score=0.25,
        recency_score=0.68,
    )
    assert round(score, 6) == 0.2385


def test_openapi_includes_feature8_route_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/common-interactions" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "CommonInteractionsResponse" in schemas
    assert "SharedInteractionTarget" in schemas
    assert "DirectInteraction" in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
