from pydantic import BaseModel, Field

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary


class SecondDegreeConnectionResult(BaseModel):
    entity: EntitySummary
    degree: int = 2
    score: float
    shared_neighbor_count: int
    jaccard: float
    adamic_adar: float
    shared_neighbors: list[EntitySummary] = Field(default_factory=list)
    paths: list[list[str]] = Field(default_factory=list)
    explanation: Explanation


class IntermediateNode(BaseModel):
    id: str
    label: str
    display_name: str
    centrality_rank: int
    social_degree: int
    properties: dict = Field(default_factory=dict)


class ThirdDegreeConnectionResult(BaseModel):
    entity: EntitySummary
    degree: int = 3
    score: float
    path_count: int
    katz_score: float
    paths: list[list[str]] = Field(default_factory=list)
    intermediate_nodes: list[IntermediateNode] = Field(default_factory=list)
    explanation: Explanation


ConnectionDiscoveryResult = SecondDegreeConnectionResult | ThirdDegreeConnectionResult


class ConnectionDiscoveryResponse(BaseModel):
    entity_id: str
    degree: int
    count: int
    results: list[ConnectionDiscoveryResult]
