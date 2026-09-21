from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field


class QuantumRiskAssessment(BaseModel):
    algorithm: str
    classification: str
    score: int = Field(ge=0, le=100)
    quantum_vulnerable: bool
    reason: str


class QuantumRiskEngine:
    def __init__(self, database_path: str | Path | None = None) -> None:
        path = (
            Path(database_path)
            if database_path
            else Path(__file__).with_name("algorithm_risks.json")
        )
        self.database = json.loads(path.read_text(encoding="utf-8"))

    def assess(self, algorithm: str | None) -> QuantumRiskAssessment:
        subject = (algorithm or "unknown").upper().replace("_", "-")
        key = self._match(subject)
        if not key:
            return QuantumRiskAssessment(
                algorithm=algorithm or "Unknown",
                classification="unknown",
                score=25,
                quantum_vulnerable=False,
                reason="Algorithm is not mapped in the configurable quantum-risk database.",
            )
        profile = self.database[key]
        return QuantumRiskAssessment(algorithm=algorithm or key, **profile)

    def _match(self, subject: str) -> str | None:
        if "ML-KEM" in subject:
            return "ML-KEM"
        if "ML-DSA" in subject:
            return "ML-DSA"
        if "AES" in subject:
            size = re.search(r"AES[^0-9]*(128|256)", subject)
            return f"AES-{size.group(1)}" if size else "AES-128"
        if "SHA-256" in subject or "SHA256" in subject:
            return "SHA-256"
        if "SHA-384" in subject or "SHA384" in subject:
            return "SHA-384"
        if "SHA-512" in subject or "SHA512" in subject:
            return "SHA-512"
        if "SHA-3" in subject or "SHA3" in subject:
            return "SHA-3"
        if "HMAC" in subject:
            return "HMAC"
        if "ECDH" in subject:
            return "ECDH"
        if any(token in subject for token in ("DIFFIE-HELLMAN", "DIFFIE HELLMAN")):
            return "DIFFIE-HELLMAN"
        if any(token in subject for token in ("ECC", "ECDSA", "P-256", "SECP")):
            return "ECC"
        if "RSA" in subject:
            return "RSA"
        return None
