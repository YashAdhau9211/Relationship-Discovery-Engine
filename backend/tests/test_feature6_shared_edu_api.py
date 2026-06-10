import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.api.deps import get_education_service
from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.schemas.common import Explanation
from app.schemas.education import SharedEducationResponse, SharedEducationResult
from app.schemas.entities import EntitySummary
from app.services.education import EducationService


class FakeEducationService:
    def get_shared_education(self, source_id: str, target_id: str) -> SharedEducationResponse:
        if source_id == "person:missing" or target_id == "person:missing":
            missing_id = "person:missing"
            raise DomainError(404, "entity_not_found", f"Person '{missing_id}' was not found.", {"entity_id": missing_id})
        if target_id == "person:no-shared-edu":
            return SharedEducationResponse(source_id=source_id, target_id=target_id, count=0, institutions=[])
        result = SharedEducationResult(
            institution=EntitySummary(
                id="edu:stanford",
                label="EducationInstitution",
                display_name="Stanford University",
                properties={"country": "US"},
            ),
            source_degree="MS",
            target_degree="MS",
            source_field="Computer Science",
            target_field="Data Science",
            source_start_year=2010,
            source_end_year=2012,
            target_start_year=2011,
            target_end_year=2013,
            attendance_overlap_years=1,
            field_of_study_match=False,
            degree_level_match=True,
            co_attendance_probability=0.768525,
            score=0.803894,
            explanation=Explanation(
                summary="Both people studied at Stanford University with 1 overlapping attendance year(s).",
                algorithms=["education_common_neighbor", "attendance_year_overlap", "degree_field_similarity", "co_attendance_probability"],
                evidence=[{"type": "shared_education", "institution_id": "edu:stanford"}],
            ),
        )
        return SharedEducationResponse(source_id=source_id, target_id=target_id, count=1, institutions=[result])


def make_client() -> TestClient:
    app = create_app(Settings(bootstrap_schema=False, app_env="test"))
    app.dependency_overrides[get_education_service] = lambda: FakeEducationService()
    return TestClient(app)


def test_shared_education_endpoint() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/shared-edu", params={"target": "person:david-kim"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "person:alice-chen"
    assert body["target_id"] == "person:david-kim"
    assert body["count"] == 1
    institution = body["institutions"][0]
    assert institution["institution"]["id"] == "edu:stanford"
    assert institution["attendance_overlap_years"] == 1
    assert institution["field_of_study_match"] is False
    assert institution["degree_level_match"] is True
    assert institution["co_attendance_probability"] == 0.768525
    assert "attendance_year_overlap" in institution["explanation"]["algorithms"]


def test_shared_education_empty_result() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:alice-chen/shared-edu", params={"target": "person:no-shared-edu"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["institutions"] == []


def test_shared_education_missing_person_uses_api_error_shape() -> None:
    client = make_client()
    response = client.get("/api/v1/entities/person:missing/shared-edu", params={"target": "person:david-kim"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_overlap_years_uses_half_open_attendance_windows() -> None:
    overlap = EducationService._overlap_years(2010, 2012, 2011, 2013)
    assert overlap == 1


def test_overlap_years_returns_zero_for_non_overlapping_attendance() -> None:
    overlap = EducationService._overlap_years(2008, 2010, 2011, 2013)
    assert overlap == 0


def test_co_attendance_probability_uses_degree_and_field_signals() -> None:
    probability = EducationService._co_attendance_probability(1, field_match=False, degree_match=True)
    assert round(probability, 6) == 0.768525


def test_result_score_includes_seed_edge_confidence() -> None:
    service = EducationService(repository=None)
    result = service._result_from_row(
        {
            "institution_id": "edu:stanford",
            "institution_label": "EducationInstitution",
            "institution_display_name": "Stanford University",
            "institution_properties": {"country": "US"},
            "source_degree": "MS",
            "target_degree": "MS",
            "source_field": "Computer Science",
            "target_field": "Data Science",
            "source_start_year": 2010,
            "source_end_year": 2012,
            "target_start_year": 2011,
            "target_end_year": 2013,
            "source_overlap_score": 1.0,
            "target_overlap_score": 0.82,
        }
    )
    assert result.score == 0.803894


def test_openapi_includes_feature6_route_and_schemas() -> None:
    client = make_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/entities/{entity_id}/shared-edu" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "SharedEducationResponse" in schemas
    assert "SharedEducationResult" in schemas


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
