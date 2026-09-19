"""TOPSIS-based PQC recommendation engine.

Orchestrates:
    1. Cryptographic function classification and confidence scoring
    2. Hard eligibility filtering (e.g. minimum NIST security category)
    3. PQC candidate selection from the knowledge base
    4. TOPSIS multi-criteria ranking on eligible candidates
    5. Explainable output with provenance

The existing ``PQCRecommendationEngine`` remains as a fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from migration_engine.crypto_function_classifier import (
    DIGITAL_SIGNATURE,
    HASH_CRYPTO,
    KEY_ESTABLISHMENT,
    SYMMETRIC_CRYPTO,
    UNKNOWN_FUNCTION,
    classify_crypto_function,
)
from migration_engine.pqc_knowledge_base import PQCCandidate, PQCKnowledgeBase
from migration_engine.topsis_engine import (
    TOPSISSolution,
    validate_weights,
)
from migration_engine.topsis_engine import (
    solve as topsis_solve,
)

logger = logging.getLogger(__name__)

_HYBRID_TEMPLATES: dict[str, str] = {
    KEY_ESTABLISHMENT: "Classical KE + {alg} hybrid during transition",
    DIGITAL_SIGNATURE: "Classical signature + {alg} dual-sign during transition",
}


class RankedCandidate(BaseModel):
    algorithm: str
    closeness_coefficient: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    scores: dict[str, float]
    nist_level: int
    source: str
    family: str


class FunctionRecommendation(BaseModel):
    function: str
    candidates: list[RankedCandidate]
    primary_recommendation: str


class TOPSISRecommendation(BaseModel):
    """Full TOPSIS-based recommendation with explainability."""
    asset: str
    current_algorithm: str
    detected_functions: list[str]
    classification_confidence: float
    recommendations: list[FunctionRecommendation]
    hybrid_strategy: str
    reason: str
    criteria_weights: dict[str, float]
    provenance: dict[str, str]
    topsis_details: dict[str, Any] = Field(default_factory=dict)
    
    # Legacy-compatible fields (expected by existing pipeline)
    recommended_algorithm: str
    metrics: dict[str, str]
    constraints: list[str] = Field(default_factory=list)


class TOPSISRecommendationEngine:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        knowledge_base: PQCKnowledgeBase | None = None,
    ) -> None:
        self.weights = validate_weights(weights)
        self.kb = knowledge_base or PQCKnowledgeBase()

    def recommend(self, value: Any) -> TOPSISRecommendation:
        algorithm = value.current_algorithm
        use_case = getattr(value, "use_case", None)
        asset_type = getattr(value, "asset_type", None)
        memory_constraint = getattr(value, "memory_constraint", "standard")
        
        # Determine the required security level (default 1, but configurable via inputs)
        required_security = getattr(value, "required_security_level", 1)

        # 1. Classify cryptographic function
        detected_funcs, confidence = classify_crypto_function(
            algorithm=algorithm,
            use_case=use_case if use_case and use_case != "general" else None,
            asset_type=asset_type,
        )

        # 2. Collect constraints
        constraints: list[str] = []
        if memory_constraint and memory_constraint.lower() in {"low", "constrained", "iot"}:
            constraints.append("low-memory environment")
            
        if required_security > 1:
            constraints.append(f"required security level >= {required_security}")

        # 3. Non-vulnerable primitives get no PQC recommendation
        if SYMMETRIC_CRYPTO in detected_funcs or HASH_CRYPTO in detected_funcs:
            return self._no_replacement(value, detected_funcs, confidence, constraints)
            
        if UNKNOWN_FUNCTION in detected_funcs:
            return self._no_replacement(value, detected_funcs, confidence, constraints)

        # 4. Perform TOPSIS for each detected function separately
        recommendations = []
        topsis_details = {}
        primary_names = []
        hybrid_strats = []
        
        for func in detected_funcs:
            # Hard Constraint: Filter by function and minimum security level
            all_func_cands = self.kb.candidates_for_function(func)
            eligible = [c for c in all_func_cands if c.nist_level >= required_security]
            
            if not eligible:
                continue
                
            solution = self._run_topsis(eligible, self.weights)
            
            if not solution.rankings:
                continue
                
            top = solution.rankings[0]
            primary_names.append(top.name)
            topsis_details[f"{func}_ideal"] = solution.ideal

            hybrid_strats.append(
                _HYBRID_TEMPLATES.get(func, "Hybrid transition").format(alg=top.name)
            )

            ranked = [
                RankedCandidate(
                    algorithm=r.name,
                    closeness_coefficient=r.closeness,
                    rank=r.rank,
                    scores=r.scores,
                    nist_level=self.kb.get(r.name).nist_level if self.kb.get(r.name) else 0,
                    source=self.kb.get(r.name).source if self.kb.get(r.name) else "",
                    family=self.kb.get(r.name).family if self.kb.get(r.name) else "",
                )
                for r in solution.rankings
            ]
            
            recommendations.append(
                FunctionRecommendation(
                    function=func,
                    candidates=ranked,
                    primary_recommendation=top.name
                )
            )

        if not recommendations:
            return self._no_replacement(value, detected_funcs, confidence, constraints)

        reason = (
            f"TOPSIS analysis selected optimal replacements for {value.current_algorithm} "
            f"based on {len(detected_funcs)} detected cryptographic function(s). "
            f"Filtered by minimum security level {required_security}."
        )

        return TOPSISRecommendation(
            asset=value.asset,
            current_algorithm=value.current_algorithm,
            detected_functions=detected_funcs,
            classification_confidence=confidence,
            recommendations=recommendations,
            primary_recommendation=" + ".join(primary_names),
            hybrid_strategy=" and ".join(hybrid_strats),
            reason=reason,
            criteria_weights=self.weights,
            provenance={
                "method": "TOPSIS",
                "version": "1.0.0",
                "knowledge_base": "NIST FIPS 203/204/205",
            },
            topsis_details=topsis_details,
            recommended_algorithm=" + ".join(primary_names),
            metrics={
                "confidence": f"{confidence:.2f}",
                "functions": str(len(detected_funcs)),
                "required_security_level": str(required_security),
            },
            constraints=constraints,
        )

    def _run_topsis(
        self, candidates: list[PQCCandidate], weights: dict[str, float]
    ) -> TOPSISSolution:
        names = [c.name for c in candidates]
        matrix: list[list[float]] = []
        for c in candidates:
            row = [
                float(c.performance_rank),
                float(c.public_key_bytes),
                float(c.sig_or_ct_bytes),
                c.maturity,
                c.compatibility,
                c.migration_complexity,
            ]
            matrix.append(row)
        return topsis_solve(names, matrix, weights=weights)

    @staticmethod
    def _no_replacement(
        value: Any, funcs: list[str], confidence: float, constraints: list[str]
    ) -> TOPSISRecommendation:
        func_str = funcs[0]
        if func_str == SYMMETRIC_CRYPTO:
            reason = (
                "Symmetric algorithms require key length verification, "
                "but no direct asymmetric PQC replacement is required."
            )
        elif func_str == HASH_CRYPTO:
            reason = (
                "Hash algorithms require digest size verification, "
                "but no direct PQC migration recommendation is required."
            )
        else:
            reason = "No suitable PQC candidates available or algorithm is not quantum-vulnerable."
            
        return TOPSISRecommendation(
            asset=value.asset,
            current_algorithm=value.current_algorithm,
            detected_functions=funcs,
            classification_confidence=confidence,
            recommendations=[],
            primary_recommendation="No direct replacement",
            hybrid_strategy="Maintain crypto-agility",
            reason=reason,
            criteria_weights={},
            provenance={"method": "classification", "version": "1.0.0"},
            recommended_algorithm="No direct replacement",
            metrics={"security": "reviewed", "confidence": f"{confidence:.2f}"},
            constraints=constraints,
        )
