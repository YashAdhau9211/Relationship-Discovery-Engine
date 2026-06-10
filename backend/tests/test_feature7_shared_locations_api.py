import sys
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_location_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.locations import SharedLocationResult, SharedLocationsResponse
from app.services.locations import LocationService


class FakeLocationService:
    def get_shared_locations(self, source_id: str, target_id: str) -> SharedLocationsResponse:
        if source_id == "person:missing" or target_id == "person:missing":
            missing_id = "person:missing"
            raise DomainError(404, "entity_not_found", f"Person '{missing_id}' was not found.", {"entity_id": missing_id})
        if target_id == "person:no-shared-location":
            return SharedLocationsResponse(source_id=source_id, target_id=target_id, count=0, locations=[])
        result = SharedLocationResult(
            location=EntitySummary(
                id="loc:asn-64512",
                label="Location",
                display_name="ASN 64512 Cloud Relay",
                properties={"type": "ip_asn", "country_code": "ZZ"},
            ),
            source_location_type="ip_login",
            target_location_type="ip_login",
            source_start_ts="2026-03-04T21:00:00Z",
            source_end_ts="2026-03-04T23:00:00Z",
            target_start_ts="2026-03-04T21:00:00Z",
            target_end_ts="2026-03-04T23:00:00Z",
            overlap_hours=2.0,
            spatial_distance_km=0.0,
            source_frequency=2,
            target_frequency=2,
            combined_frequency=4,
            source_recency=0.93,
            target_recency=0.93,
            co_presence_score=0.347667,
            score=0.347667,
            explanation=Explanation(
                summary="Both people share ASN 64512 Cloud Relay with 2 overlapping hour(s).",
                algorithms=["shared_location_common_neighbor", "temporal_overlap_hours", "spatial_proximity", "co_presence_score"],
                evidence=[{"type": "shared_location", "location_id": "loc:asn-64512"}],
            ),
        )
        return SharedLocationsResponse(source_id=source_id, target_id=target_id, count=1, locations=[result])


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_location_service] = lambda: FakeLocationService()
    return TestClient(app)


def test_shared_locations_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/shared-locations", params={"target": "person:elena-petrova"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "person:alice-chen"
    assert body["target_id"] == "person:elena-petrova"
    assert body["count"] == 1
    location = body["locations"][0]
    assert location["location"]["id"] == "loc:asn-64512"
    assert location["overlap_hours"] == 2.0
    assert location["combined_frequency"] == 4
    assert location["co_presence_score"] == 0.347667
    assert "co_presence_score" in location["explanation"]["algorithms"]


def test_shared_locations_empty_result() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/shared-locations", params={"target": "person:no-shared-location"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["locations"] == []


def test_shared_locations_missing_person_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/shared-locations", params={"target": "person:elena-petrova"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_overlap_hours_for_bounded_location_windows() -> None:
    overlap = LocationService._overlap_hours(
        "2026-03-04T21:00:00Z",
        "2026-03-04T23:00:00Z",
        "2026-03-04T22:00:00Z",
        "2026-03-05T01:00:00Z",
    )
    assert overlap == 1.0


def test_overlap_hours_returns_zero_for_open_ended_different_starts() -> None:
    overlap = LocationService._overlap_hours(
        "2026-01-01T08:00:00Z",
        None,
        "2026-02-01T08:00:00Z",
        None,
    )
    assert overlap == 0.0


def test_co_presence_score_uses_overlap_frequency_and_recency() -> None:
    score = LocationService._co_presence_score(overlap_hours=2.0, combined_frequency=4, source_recency=0.93, target_recency=0.93)
    assert round(score, 6) == 0.347667


def test_openapi_includes_feature7_route_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/shared-locations" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "SharedLocationsResponse" in schemas
    assert "SharedLocationResult" in schemas


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
