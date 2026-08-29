from __future__ import annotations

from pydantic import BaseModel, Field


class MigrationComplexityInput(BaseModel):
    dependency_count: int = Field(default=0, ge=0)
    legacy_technology: bool = False
    application_criticality: str = "medium"
    downtime_requirement: str = "standard"
    compatibility: str = "unknown"


class MigrationComplexityAssessment(BaseModel):
    migration_complexity: str
    score: int = Field(ge=0, le=100)
    reasons: list[str]


class MigrationComplexityEngine:
    def assess(self, value: MigrationComplexityInput) -> MigrationComplexityAssessment:
        score = 0
        reasons: list[str] = []
        if value.dependency_count >= 25:
            score += 30
            reasons.append(f"{value.dependency_count} dependent applications")
        elif value.dependency_count >= 10:
            score += 20
            reasons.append(f"{value.dependency_count} dependent applications")
        elif value.dependency_count:
            score += 10
            reasons.append(f"{value.dependency_count} dependent applications")
        if value.legacy_technology:
            score += 15
            reasons.append("Legacy cryptographic technology")
        criticality = value.application_criticality.lower()
        if criticality == "critical":
            score += 15
            reasons.append("Critical business service")
        elif criticality == "high":
            score += 10
            reasons.append("High-importance business service")
        if value.downtime_requirement.lower() in {"zero", "none", "continuous"}:
            score += 20
            reasons.append("Zero-downtime migration required")
        if value.compatibility.lower() in {"limited", "legacy-only", "incompatible"}:
            score += 20
            reasons.append("Limited post-quantum compatibility")
        score = min(score, 100)
        label = (
            "critical"
            if score >= 81
            else "high"
            if score >= 55
            else "medium"
            if score >= 25
            else "low"
        )
        return MigrationComplexityAssessment(
            migration_complexity=label,
            score=score,
            reasons=reasons or ["No material migration constraint was identified"],
        )
