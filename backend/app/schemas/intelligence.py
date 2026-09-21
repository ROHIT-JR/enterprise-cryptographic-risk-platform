from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import DistributionItem
from backend.app.schemas.graph import GraphEdgeResponse, GraphNodeResponse


class BusinessContextUpdate(BaseModel):
    criticality: Literal["low", "medium", "high", "critical"]
    owner: str | None = Field(default=None, max_length=160)
    data_lifetime_years: int = Field(default=5, ge=0, le=100)
    data_sensitivity: Literal[
        "public", "internal", "confidential", "regulated", "financial", "restricted"
    ] = "internal"
    downtime_requirement: str = Field(default="standard", max_length=32)
    compatibility: str = Field(default="unknown", max_length=32)
    legacy_technology: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "criticality": "critical",
                    "owner": "Payments engineering",
                    "data_lifetime_years": 15,
                    "data_sensitivity": "financial",
                    "downtime_requirement": "zero",
                    "compatibility": "limited",
                    "legacy_technology": True,
                }
            ]
        }
    )


class BusinessContextResponse(BusinessContextUpdate):
    asset_id: str


class IntelligenceItem(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    algorithm: str | None
    project_id: str
    project_name: str
    quantum_score: float
    quantum_classification: str
    hndl_score: float
    hndl_risk: str
    centrality_score: float
    dependent_systems: int
    business_score: float
    migration_complexity_score: float
    evidence_confidence: float
    evidence_sources: list[str]
    final_score: float
    severity: str
    explanations: list[str]
    factors: dict[str, Any]


class IntelligenceMetrics(BaseModel):
    total_analyzed: int
    vulnerable_assets: int
    critical_quantum_risks: int
    hndl_exposures: int
    average_risk_score: float


class IntelligenceRiskResponse(BaseModel):
    metrics: IntelligenceMetrics
    algorithm_vulnerability_distribution: list[DistributionItem]
    severity_distribution: list[DistributionItem]
    items: list[IntelligenceItem]


class HNDLResponse(BaseModel):
    total: int
    items: list[IntelligenceItem]


class BlastRadiusImpactSummary(BaseModel):
    total_affected: int
    by_degree: dict[str, int]
    critical_systems: int
    estimated_effort_hours: int
    critical_path: list[str]


class BlastRadiusResponse(BaseModel):
    asset_id: str | None
    asset_name: str | None
    dependent_systems: int
    centrality_score: float
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    impact_summary: BlastRadiusImpactSummary


class MigrationRecommendationResponse(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    current_algorithm: str
    recommended_algorithm: str
    wave: int
    complexity: str
    risk_score: float | None
    reasons: list[str]
    recommendation: dict[str, Any]


class MigrationRoadmapWave(BaseModel):
    wave: int
    title: str
    reason: str
    items: list[MigrationRecommendationResponse]


class MigrationRoadmapResponse(BaseModel):
    total_assets: int
    waves: list[MigrationRoadmapWave]
