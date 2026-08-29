from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessCriticalityAssessment(BaseModel):
    criticality: str
    score: int = Field(ge=0, le=100)
    reason: str


class BusinessCriticalityEngine:
    SCORES = {"low": 20, "medium": 50, "high": 75, "critical": 100}

    def assess(self, criticality: str) -> BusinessCriticalityAssessment:
        normalized = criticality.lower()
        score = self.SCORES.get(normalized, 50)
        return BusinessCriticalityAssessment(
            criticality=normalized,
            score=score,
            reason=f"Business criticality is {normalized}.",
        )
