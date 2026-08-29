from migration_engine import (
    MigrationRoadmapEngine,
    PQCRecommendationEngine,
    PQCRecommendationInput,
)
from risk_engine.dependency_centrality import DependencyCentralityEngine
from risk_engine.evidence_engine import EvidenceIntelligenceEngine
from risk_engine.final_risk_engine import FinalRiskEngine, FinalRiskInput
from risk_engine.hndl_analysis import HNDLAnalysisEngine, HNDLInput
from risk_engine.quantum_risk import QuantumRiskEngine


def test_evidence_confidence_uses_independent_source_count():
    engine = EvidenceIntelligenceEngine()

    assert engine.assess("RSA", ["source_code"]).confidence == 50
    assert engine.assess("RSA", ["source_code", "docker"]).confidence == 75
    result = engine.assess("RSA", ["source_code", "docker", "tls"])
    assert result.confidence == 95
    assert result.evidence_sources == ["docker", "source_code", "tls"]


def test_quantum_and_hndl_scoring_for_long_lived_financial_data():
    quantum = QuantumRiskEngine().assess("RSA-2048")
    hndl = HNDLAnalysisEngine().assess(
        HNDLInput(
            asset="Customer Database",
            data_sensitivity="financial",
            data_lifetime_years=20,
            encryption_algorithm="RSA-2048",
            quantum_vulnerable=quantum.quantum_vulnerable,
        )
    )

    assert quantum.classification == "critical"
    assert quantum.score == 100
    assert hndl.score == 100
    assert hndl.hndl_risk == "critical"
    assert "Long-lived" in hndl.reason
    assert QuantumRiskEngine().assess("ML-KEM-768").classification == "secure"


def test_dependency_centrality_counts_affected_critical_applications():
    nodes = {
        "rsa": {"name": "RSA certificate", "asset_type": "certificate"},
        "pay": {
            "name": "Payment API",
            "asset_type": "application",
            "criticality": "critical",
        },
        "auth": {
            "name": "Authentication API",
            "asset_type": "application",
            "criticality": "critical",
        },
        "portal": {
            "name": "Customer Portal",
            "asset_type": "application",
            "criticality": "high",
        },
    }
    result = DependencyCentralityEngine().analyze_all(
        nodes=nodes,
        edges=[("rsa", "pay"), ("rsa", "auth"), ("rsa", "portal")],
    )["rsa"]

    assert result.dependent_systems == 3
    assert result.degree_centrality == 1
    assert result.critical_path_impact == 1
    assert result.centrality_score == 1


def test_final_phase2_score_normalizes_six_factors_to_94():
    result = FinalRiskEngine().assess(
        FinalRiskInput(
            asset="RSA-2048 Certificate",
            quantum_vulnerability=100,
            hndl_exposure=100,
            dependency_centrality=90,
            business_criticality=100,
            migration_complexity=60,
            evidence_confidence=95,
            explanations=["Quantum vulnerable algorithm"],
        )
    )

    assert result.score == 94
    assert result.severity == "critical"


def test_pqc_recommendation_respects_low_memory_constraint():
    result = PQCRecommendationEngine().recommend(
        PQCRecommendationInput(
            asset="IoT Gateway",
            current_algorithm="RSA-2048",
            use_case="iot",
            memory_constraint="low",
        )
    )

    assert result.recommended_algorithm == "ML-KEM-512"
    assert "lower" in result.reason.lower()


def test_ecdh_recommendation_uses_key_encapsulation():
    result = PQCRecommendationEngine().recommend(
        PQCRecommendationInput(asset="Gateway", current_algorithm="ECDH")
    )

    assert result.recommended_algorithm == "ML-KEM-768"


def test_migration_roadmap_orders_algorithm_library_then_application():
    roadmap = MigrationRoadmapEngine().generate(
        assets={
            "rsa": {"name": "RSA", "asset_type": "algorithm"},
            "openssl": {"name": "OpenSSL", "asset_type": "library"},
            "payment": {"name": "Payment Service", "asset_type": "application"},
        },
        dependencies=[("payment", "openssl"), ("openssl", "rsa")],
    )

    assert {item.asset: item.wave for item in roadmap} == {
        "RSA": 1,
        "OpenSSL": 2,
        "Payment Service": 3,
    }
