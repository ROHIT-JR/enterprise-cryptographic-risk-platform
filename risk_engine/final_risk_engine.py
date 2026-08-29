from __future__ import annotations

from pydantic import BaseModel, Field


class FinalRiskInput(BaseModel):
    asset: str
    quantum_vulnerability: float = Field(ge=0, le=100)
    hndl_exposure: float = Field(ge=0, le=100)
    dependency_centrality: float = Field(ge=0, le=100)
    business_criticality: float = Field(ge=0, le=100)
    migration_complexity: float = Field(ge=0, le=100)
    evidence_confidence: float = Field(ge=0, le=100)
    explanations: list[str] = Field(default_factory=list)


class FinalRiskAssessment(BaseModel):
    asset: str
    score: int = Field(ge=0, le=100)
    severity: str
    explanation: list[str]
    components: dict[str, float]


class FinalRiskEngine:
    WEIGHTS = {
        "quantum_vulnerability": 0.30,
        "hndl_exposure": 0.20,
        "dependency_centrality": 0.15,
        "business_criticality": 0.15,
        "migration_complexity": 0.10,
        "evidence_confidence": 0.10,
    }

    def assess(self, value: FinalRiskInput) -> FinalRiskAssessment:
        components = {
            name: round(getattr(value, name) * weight, 2)
            for name, weight in self.WEIGHTS.items()
        }
        score = min(round(sum(components.values())), 100)
        severity = (
            "low"
            if score <= 30
            else "medium"
            if score <= 60
            else "high"
            if score <= 80
            else "critical"
        )
        return FinalRiskAssessment(
            asset=value.asset,
            score=score,
            severity=severity,
            explanation=list(dict.fromkeys(value.explanations)),
            components=components,
        )
