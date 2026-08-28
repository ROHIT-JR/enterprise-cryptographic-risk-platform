from typing import Any

from pydantic import BaseModel, Field


class RiskInput(BaseModel):
    name: str
    algorithm: str | None = None
    asset_type: str
    dependency_count: int = Field(default=0, ge=0)
    criticality: str = "medium"
    details: dict[str, Any] = Field(default_factory=dict)


class RiskFactor(BaseModel):
    category: str
    points: int = Field(ge=0)
    explanation: str
    rule_id: str


class RiskAssessment(BaseModel):
    asset: str
    score: int = Field(ge=0, le=100)
    severity: str
    reasons: list[str]
    factors: list[RiskFactor]
