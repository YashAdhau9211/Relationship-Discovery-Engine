import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_organization_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.organizations import SharedOrganizationResult, SharedOrganizationsResponse
from app.services.organizations import OrganizationService


class FakeOrganizationService:
    def get_shared_organizations(self, source_id: str, target_id: str) -> SharedOrganizationsResponse:
        if source_id == "person:missing" or target_id == "person:missing":
            missing_id = "person:missing"
            raise DomainError(404, "entity_not_found", f"Person '{missing_id}' was not found.", {"entity_id": missing_id})
        if target_id == "person:no-shared-org":
            return SharedOrganizationsResponse(source_id=source_id, target_id=target_id, count=0, organizations=[])
        result = SharedOrganizationResult(
            organization=EntitySummary(id="org:atlas-logistics", label="Organization", display_name="Atlas Logistics", properties={"pagerank_score": 0.63}),
            source_role="Regional Manager",
            target_role="External Broker",
            source_relationship_type="WORKS_AT",
            target_relationship_type="WORKS_AT",
            source_start_date="2021-03-01",
            source_end_date=None,
            target_start_date="2022-11-01",
            target_end_date=None,
            overlap_months=43,
            concurrent=True,
            org_importance_score=0.63,
            score=0.63,
            explanation=Explanation(
                summary="Farah Al Mansour and Boris Volkov share Atlas Logistics with overlapping tenure.",
                algorithms=["bipartite_common_neighbor", "temporal_overlap", "organization_pagerank_weight"],
                evidence=[{"type": "shared_organization", "organization_id": "org:atlas-logistics"}],
            ),
        )
        return SharedOrganizationsResponse(source_id=source_id, target_id=target_id, count=1, organizations=[result])


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_organization_service] = lambda: FakeOrganizationService()
    return TestClient(app)


def test_shared_orgs_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:farah-al-mansour/shared-orgs", params={"target": "person:boris-volkov"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "person:farah-al-mansour"
    assert body["target_id"] == "person:boris-volkov"
    assert body["count"] == 1
    org = body["organizations"][0]
    assert org["organization"]["id"] == "org:atlas-logistics"
    assert org["source_role"] == "Regional Manager"
    assert org["target_role"] == "External Broker"
    assert org["concurrent"] is True
    assert org["score"] == 0.63
    assert "temporal_overlap" in org["explanation"]["algorithms"]


def test_shared_orgs_empty_result() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:farah-al-mansour/shared-orgs", params={"target": "person:no-shared-org"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["organizations"] == []


def test_shared_orgs_missing_person_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/shared-orgs", params={"target": "person:boris-volkov"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_overlap_months_handles_open_ended_tenure() -> None:
    overlap = OrganizationService._overlap_months(
        "2021-03-01",
        None,
        "2022-11-01",
        None,
        reference_date=date(2026, 6, 10),
    )
    assert overlap == 43


def test_overlap_months_returns_zero_for_non_overlapping_tenure() -> None:
    overlap = OrganizationService._overlap_months(
        "2020-01-01",
        "2020-12-31",
        "2021-01-01",
        None,
        reference_date=date(2026, 6, 10),
    )
    assert overlap == 0


def test_openapi_includes_feature5_route_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/shared-orgs" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "SharedOrganizationsResponse" in schemas
    assert "SharedOrganizationResult" in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
