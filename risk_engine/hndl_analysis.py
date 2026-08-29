from __future__ import annotations

from pydantic import BaseModel, Field


class HNDLInput(BaseModel):
    asset: str
    data_sensitivity: str = "internal"
    data_lifetime_years: int = Field(default=5, ge=0, le=100)
    encryption_algorithm: str
    exposure_period_years: int = Field(default=0, ge=0, le=100)
    quantum_vulnerable: bool


class HNDLAssessment(BaseModel):
    asset: str
    hndl_risk: str
    score: int = Field(ge=0, le=100)
    reason: str


class HNDLAnalysisEngine:
    SENSITIVITY = {
        "public": 0,
        "internal": 30,
        "confidential": 70,
        "regulated": 100,
        "financial": 100,
        "restricted": 100,
    }

    def assess(self, value: HNDLInput) -> HNDLAssessment:
        sensitivity = self.SENSITIVITY.get(value.data_sensitivity.lower(), 50)
        lifetime = min((value.data_lifetime_years + value.exposure_period_years) * 5, 100)
        vulnerability = 100 if value.quantum_vulnerable else 0
        score = round(sensitivity * 0.4 + lifetime * 0.3 + vulnerability * 0.3)
        label = (
            "critical"
            if score >= 81
            else "high"
            if score >= 61
            else "medium"
            if score >= 31
            else "low"
        )
        if value.quantum_vulnerable and value.data_lifetime_years >= 10 and sensitivity >= 70:
            reason = "Long-lived sensitive data is protected by quantum-vulnerable cryptography."
        elif value.quantum_vulnerable:
            reason = (
                "Captured ciphertext may become decryptable when cryptographically relevant "
                "quantum computers emerge."
            )
        else:
            reason = "No elevated harvest-now-decrypt-later condition was identified."
        return HNDLAssessment(asset=value.asset, hndl_risk=label, score=score, reason=reason)
