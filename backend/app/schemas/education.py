from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary


class SharedEducationResult(BaseModel):
    institution: EntitySummary
    source_degree: str | None = None
    target_degree: str | None = None
    source_field: str | None = None
    target_field: str | None = None
    source_start_year: int | None = None
    source_end_year: int | None = None
    target_start_year: int | None = None
    target_end_year: int | None = None
    attendance_overlap_years: int
    field_of_study_match: bool
    degree_level_match: bool
    co_attendance_probability: float
    score: float
    explanation: Explanation


class SharedEducationResponse(BaseModel):
    source_id: str
    target_id: str
    count: int
    institutions: list[SharedEducationResult] = Field(default_factory=list)
