from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.graph import GraphEdge, GraphNode


class ConnectionResult(BaseModel):
    entity: EntitySummary
    score: float
    paths: list[list[str]] = Field(default_factory=list)
    explanation: Explanation


class RelationshipScoreResponse(BaseModel):
    source_id: str
    target_id: str
    rs_score: float
    components: dict[str, float]
    explanation: Explanation
    top_paths: list[list[str]] = Field(default_factory=list)


class PathResult(BaseModel):
    node_sequence: list[GraphNode]
    edge_sequence: list[GraphEdge]
    hop_count: int
    path_score: float
    explanation: Explanation
    metadata: dict[str, Any] = Field(default_factory=dict)
