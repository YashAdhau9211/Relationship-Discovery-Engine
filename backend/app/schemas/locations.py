from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary


class SharedLocationResult(BaseModel):
    location: EntitySummary
    source_location_type: str | None = None
    target_location_type: str | None = None
    source_start_ts: str | None = None
    source_end_ts: str | None = None
    target_start_ts: str | None = None
    target_end_ts: str | None = None
    overlap_hours: float
    spatial_distance_km: float
    source_frequency: int
    target_frequency: int
    combined_frequency: int
    source_recency: float
    target_recency: float
    co_presence_score: float
    score: float
    explanation: Explanation


class SharedLocationsResponse(BaseModel):
    source_id: str
    target_id: str
    count: int
    locations: list[SharedLocationResult] = Field(default_factory=list)
