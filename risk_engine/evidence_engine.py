from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceAssessment(BaseModel):
    asset: str
    confidence: int = Field(ge=0, le=100)
    evidence_sources: list[str]
    explanation: str


class EvidenceIntelligenceEngine:
    """Correlate independent discovery channels into an auditable confidence score."""

    SOURCE_ALIASES = {
        "repository": "source_code",
        "source": "source_code",
        "pattern": "source_code",
        "dependency-manifest": "source_code",
        "dockerfile-base-image": "docker",
        "dockerfile-package": "docker",
        "certificate": "certificate",
    }

    def assess(self, asset: str, evidence_sources: list[str] | set[str]) -> EvidenceAssessment:
        normalized = sorted(
            {
                self.SOURCE_ALIASES.get(source.strip().lower(), source.strip().lower())
                for source in evidence_sources
                if source and source.strip()
            }
        )
        count = len(normalized)
        confidence = (
            0
            if count == 0
            else 50
            if count == 1
            else 75
            if count == 2
            else min(95 + count - 3, 99)
        )
        label = "channel" if count == 1 else "channels"
        return EvidenceAssessment(
            asset=asset,
            confidence=confidence,
            evidence_sources=normalized,
            explanation=f"Corroborated by {count} independent evidence {label}",
        )
