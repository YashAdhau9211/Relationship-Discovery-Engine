from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    display_name: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    directed: bool = True
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphStatistics(BaseModel):
    node_count: int
    edge_count: int
    depth: int


class GraphResponse(BaseModel):
    center_id: str
    depth: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    statistics: GraphStatistics
