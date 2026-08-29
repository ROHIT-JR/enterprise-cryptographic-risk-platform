from __future__ import annotations

from pydantic import BaseModel, Field


class PQCRecommendationInput(BaseModel):
    asset: str
    current_algorithm: str
    use_case: str = "general"
    performance_priority: str = "balanced"
    compatibility: str = "unknown"
    memory_constraint: str = "standard"


class PQCRecommendation(BaseModel):
    asset: str
    current_algorithm: str
    recommended_algorithm: str
    hybrid_strategy: str
    reason: str
    metrics: dict[str, str]
    constraints: list[str] = Field(default_factory=list)


class PQCRecommendationEngine:
    """Deterministic Phase 2 recommendations based on standardized PQC families."""

    def recommend(self, value: PQCRecommendationInput) -> PQCRecommendation:
        subject = value.current_algorithm.upper().replace("_", "-")
        constraints: list[str] = []
        if value.memory_constraint.lower() in {"low", "constrained", "iot"}:
            constraints.append("low-memory environment")
        if value.compatibility.lower() in {"limited", "legacy-only"}:
            constraints.append("legacy compatibility")

        if "TLS" in subject and any(version in subject for version in ("1.0", "1.1", "1.2")):
            recommended = "TLS 1.3 Hybrid PQC"
            hybrid = "X25519 + ML-KEM-768 during transition"
            reason = "Upgrade legacy TLS first, then introduce hybrid post-quantum key exchange."
            metrics = {
                "security": "post-quantum hybrid",
                "latency": "medium",
                "compatibility": "high",
            }
        elif "ECDH" in subject or "DIFFIE" in subject:
            recommended = "ML-KEM-768"
            hybrid = "X25519 + ML-KEM-768"
            reason = "Replace classical key agreement with a standardized lattice-based KEM."
            metrics = {"security": "NIST level 3", "latency": "low", "compatibility": "hybrid"}
        elif any(token in subject for token in ("ECDSA", "ECC")):
            recommended = "ML-DSA-65"
            hybrid = "ECDSA + ML-DSA-65"
            reason = "Replace quantum-vulnerable elliptic-curve signatures with ML-DSA."
            metrics = {"security": "NIST level 3", "latency": "medium", "compatibility": "hybrid"}
        elif "RSA" in subject:
            low_memory = value.memory_constraint.lower() in {"low", "constrained", "iot"}
            encryption_use = value.use_case.lower() in {"encryption", "key_exchange", "kem", "iot"}
            if low_memory and encryption_use:
                recommended = "ML-KEM-512"
                hybrid = "RSA + ML-KEM-512 during transition"
                reason = (
                    "ML-KEM-512 provides lower key and computational overhead for "
                    "constrained devices."
                )
            else:
                recommended = "ML-KEM-768 + ML-DSA-65"
                hybrid = "RSA + ML-KEM/ML-DSA dual operation"
                reason = (
                    "RSA may serve encryption and signing, so migrate both capabilities "
                    "with a hybrid period."
                )
            metrics = {
                "security": "post-quantum",
                "latency": "low-to-medium",
                "compatibility": "hybrid transition required",
                "key_size": "larger than RSA wire formats",
            }
        else:
            recommended = "No immediate PQC replacement"
            hybrid = "Maintain crypto-agility and inventory monitoring"
            reason = "The current primitive is not an asymmetric quantum-vulnerable algorithm."
            metrics = {"security": "reviewed", "latency": "unchanged", "compatibility": "high"}

        return PQCRecommendation(
            asset=value.asset,
            current_algorithm=value.current_algorithm,
            recommended_algorithm=recommended,
            hybrid_strategy=hybrid,
            reason=reason,
            metrics=metrics,
            constraints=constraints,
        )
