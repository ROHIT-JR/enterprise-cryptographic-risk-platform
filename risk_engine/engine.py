from __future__ import annotations

import re

from risk_engine.models import RiskAssessment, RiskFactor, RiskInput
from risk_engine.rules import ALGORITHM_PROFILES, CRITICALITY_POINTS, AlgorithmProfile


class RiskEngine:
    """Deterministic, explainable Phase 1 risk scorer."""

    def assess(self, value: RiskInput) -> RiskAssessment:
        factors: list[RiskFactor] = []
        subject = " ".join(filter(None, (value.name, value.algorithm))).upper()
        algorithm_profile = self._algorithm_profile(subject)
        if algorithm_profile:
            factors.append(
                RiskFactor(
                    category="algorithm_security",
                    points=algorithm_profile.points,
                    explanation=algorithm_profile.reason,
                    rule_id=algorithm_profile.rule_id,
                )
            )
        elif value.asset_type in {"algorithm", "protocol", "certificate"}:
            factors.append(
                RiskFactor(
                    category="algorithm_security",
                    points=20,
                    explanation=(
                        "Cryptographic primitive has not yet been mapped to an approved profile"
                    ),
                    rule_id="ALG-UNKNOWN",
                )
            )

        if value.asset_type == "library":
            library_factor = self._library_factor(value)
            if library_factor:
                factors.append(library_factor)

        certificate_factor = self._certificate_factor(value)
        if certificate_factor:
            factors.append(certificate_factor)

        evidence_factor = self._evidence_factor(value)
        if evidence_factor:
            factors.append(evidence_factor)

        dependency_points = min(value.dependency_count * 5, 20)
        if dependency_points:
            factors.append(
                RiskFactor(
                    category="dependency_impact",
                    points=dependency_points,
                    explanation=f"Used by {value.dependency_count} dependent asset(s)",
                    rule_id="IMPACT-DEPENDENCIES",
                )
            )

        criticality = value.criticality.lower()
        criticality_points = CRITICALITY_POINTS.get(criticality, 10)
        if criticality_points:
            factors.append(
                RiskFactor(
                    category="asset_criticality",
                    points=criticality_points,
                    explanation=f"Project criticality is {criticality}",
                    rule_id="IMPACT-CRITICALITY",
                )
            )

        score = min(sum(factor.points for factor in factors), 100)
        severity = self.severity(score)
        reasons = [factor.explanation for factor in factors if factor.points > 0]
        if not reasons:
            reasons = ["No elevated Phase 1 risk rule matched this asset"]
        return RiskAssessment(
            asset=value.name,
            score=score,
            severity=severity,
            reasons=reasons,
            factors=factors,
        )

    @staticmethod
    def severity(score: int) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"

    @staticmethod
    def _algorithm_profile(subject: str) -> AlgorithmProfile | None:
        normalized = re.sub(r"[_/]", "-", subject)
        for aliases, profile in ALGORITHM_PROFILES:
            if any(alias in normalized for alias in aliases):
                return profile
        return None

    @staticmethod
    def _library_factor(value: RiskInput) -> RiskFactor | None:
        if "OPENSSL" not in value.name.upper():
            return None
        version = str(value.details.get("version") or value.details.get("library_version") or "")
        if not version and value.algorithm:
            version = value.algorithm
        if version.startswith(("0.", "1.0", "1.1")):
            return RiskFactor(
                category="library_lifecycle",
                points=35,
                explanation=f"OpenSSL {version} is outside the current major release line",
                rule_id="LIB-OPENSSL-LEGACY",
            )
        return RiskFactor(
            category="library_lifecycle",
            points=5,
            explanation="Cryptographic library requires version and patch governance",
            rule_id="LIB-GOVERNANCE",
        )

    @staticmethod
    def _certificate_factor(value: RiskInput) -> RiskFactor | None:
        if value.asset_type != "certificate":
            return None
        status = str(value.details.get("status", "")).lower()
        verification_error = value.details.get("verification_error")
        if status and status != "valid":
            return RiskFactor(
                category="certificate_validity",
                points=30,
                explanation="Certificate is expired or not yet valid",
                rule_id="CERT-VALIDITY",
            )
        if verification_error:
            return RiskFactor(
                category="certificate_trust",
                points=15,
                explanation="Certificate chain or hostname verification failed",
                rule_id="CERT-TRUST",
            )
        return None

    @staticmethod
    def _evidence_factor(value: RiskInput) -> RiskFactor | None:
        if value.asset_type not in {"algorithm", "library", "certificate", "protocol"}:
            return None
        confidence_points = 3 if value.confidence >= 0.95 else 2 if value.confidence >= 0.85 else 0
        corroboration_points = min(max(value.evidence_count - 1, 0), 2)
        points = min(confidence_points + corroboration_points, 5)
        if not points:
            return None
        source_label = "source" if value.evidence_count == 1 else "sources"
        return RiskFactor(
            category="evidence_confidence",
            points=points,
            explanation=(
                f"Finding confidence is {value.confidence:.0%} across "
                f"{value.evidence_count} evidence {source_label}"
            ),
            rule_id="EVIDENCE-CONFIDENCE",
        )
