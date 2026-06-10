from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary


class DirectInteraction(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    interaction_type: str | None = None
    count: int
    platform: str | None = None
    recency_score: float
    timestamps: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class SharedInteractionTarget(BaseModel):
    target: EntitySummary
    source_interaction_count: int
    target_interaction_count: int
    target_total_interactors: int
    resource_allocation_contribution: float
    interaction_types: list[str] = Field(default_factory=list)
    recency_score: float
    relationship_types: list[str] = Field(default_factory=list)


class CommonInteractionsResponse(BaseModel):
    source_id: str
    target_id: str
    direct_interaction_count: int
    shared_target_count: int
    resource_allocation_score: float
    recency_score: float
    composite_score: float
    direct_interactions: list[DirectInteraction] = Field(default_factory=list)
    shared_targets: list[SharedInteractionTarget] = Field(default_factory=list)
    explanation: Explanation
