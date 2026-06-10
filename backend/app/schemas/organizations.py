from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary


class SharedOrganizationResult(BaseModel):
    organization: EntitySummary
    source_role: str | None = None
    target_role: str | None = None
    source_relationship_type: str
    target_relationship_type: str
    source_start_date: str | None = None
    source_end_date: str | None = None
    target_start_date: str | None = None
    target_end_date: str | None = None
    overlap_months: int
    concurrent: bool
    org_importance_score: float
    score: float
    explanation: Explanation


class SharedOrganizationsResponse(BaseModel):
    source_id: str
    target_id: str
    count: int
    organizations: list[SharedOrganizationResult] = Field(default_factory=list)
