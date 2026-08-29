from risk_engine import RiskEngine, RiskInput


def test_rsa_2048_critical_dependency_is_explainable():
    assessment = RiskEngine().assess(
        RiskInput(
            name="RSA-2048",
            algorithm="RSA-2048",
            asset_type="algorithm",
            dependency_count=1,
            criticality="critical",
        )
    )

    assert assessment.score == 85
    assert assessment.severity == "critical"
    assert {factor.category for factor in assessment.factors} == {
        "algorithm_security",
        "dependency_impact",
        "asset_criticality",
    }
    assert any("quantum" in reason.lower() for reason in assessment.reasons)


def test_aes_256_medium_project_remains_low_risk():
    assessment = RiskEngine().assess(
        RiskInput(
            name="AES-256-GCM",
            algorithm="AES-256-GCM",
            asset_type="algorithm",
            criticality="medium",
        )
    )
    assert assessment.score == 18
    assert assessment.severity == "low"


def test_corroborated_high_confidence_evidence_increases_explainable_score():
    assessment = RiskEngine().assess(
        RiskInput(
            name="RSA-2048",
            algorithm="RSA-2048",
            asset_type="algorithm",
            dependency_count=1,
            criticality="critical",
            confidence=0.96,
            evidence_count=3,
        )
    )

    assert assessment.score == 90
    assert assessment.severity == "critical"
    assert any(factor.rule_id == "EVIDENCE-CONFIDENCE" for factor in assessment.factors)
