from typing import Any

from pydantic import BaseModel, Field


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphNodeRef(BaseModel):
    id: str
    label: str


class GraphStatsResponse(BaseModel):
    total_nodes: int
    nodes_by_type: dict[str, int]
    total_edges: int
    most_connected: GraphNodeRef | None = None
    most_connected_degree: int = 0
    top_centrality: GraphNodeRef | None = None
    top_centrality_score: float = 0.0
    community_count: int
    quantum_vulnerable_count: int
    quantum_total_count: int


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    source: str
    stats: GraphStatsResponse
