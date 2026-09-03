from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OptimizerInput(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    
    # Raw factors to prevent double-counting. Nullable to represent missing data.
    quantum_score: float | None = Field(default=None, ge=0.0, le=100.0)
    hndl_score: float | None = Field(default=None, ge=0.0, le=100.0)
    blast_radius: float | None = Field(default=None, ge=0.0, le=100.0)
    business_criticality: float | None = Field(default=None, ge=0.0, le=100.0)
    migration_complexity: float | None = Field(default=None, ge=0.0, le=100.0)
    
    recommended_algorithm: str = "TBD"
    dependencies: list[str] = Field(default_factory=list)  # asset_ids this asset depends on
    
    # Hard constraints
    vendor_ready: bool = True
    compatibility_blocked: bool = False
    
    # To carry over legacy plan data
    legacy_reasons: list[str] = Field(default_factory=list)
    recommendation_metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizedAsset(BaseModel):
    asset_id: str
    asset_name: str
    wave: int | None
    priority_score: float | None
    confidence: float
    recommended_algorithm: str
    constraints: list[str]
    rationale: list[str]


class OptimizationResult(BaseModel):
    waves: dict[int, list[OptimizedAsset]]
    assets: dict[str, OptimizedAsset]
    optimizer_version: str
    configuration: dict[str, float]
