import pytest
from pydantic import BaseModel

from migration_engine.crypto_function_classifier import (
    DIGITAL_SIGNATURE,
    DUAL_PUBLIC_KEY,
    HASH_CRYPTO,
    KEY_ESTABLISHMENT,
    SYMMETRIC_CRYPTO,
    UNKNOWN_FUNCTION,
    classify_crypto_function,
)
from migration_engine.pqc_knowledge_base import PQCKnowledgeBase
from migration_engine.topsis_engine import solve, validate_weights
from migration_engine.topsis_recommendation import TOPSISRecommendationEngine


class DummyInput(BaseModel):
    asset: str
    current_algorithm: str
    use_case: str = "general"
    asset_type: str = "algorithm"
    memory_constraint: str = "standard"
    required_security_level: int = 1


def test_security_level_is_hard_constraint():
    engine = TOPSISRecommendationEngine()
    req = DummyInput(
        asset="app",
        current_algorithm="ECDH",
        required_security_level=3,
    )
    res = engine.recommend(req)
    
    # ML-KEM-512 has nist_level=1, so it MUST be excluded.
    # ML-KEM-768 (level 3) and ML-KEM-1024 (level 5) are eligible.
    candidates = res.recommendations[0].candidates
    names = [c.algorithm for c in candidates]
    
    assert "ML-KEM-512" not in names
    assert "ML-KEM-768" in names
    assert "ML-KEM-1024" in names
    assert res.recommendations[0].primary_recommendation == "ML-KEM-768"


def test_candidate_below_required_security_is_excluded():
    engine = TOPSISRecommendationEngine()
    req = DummyInput(
        asset="app",
        current_algorithm="ECDSA",
        required_security_level=5,
    )
    res = engine.recommend(req)
    
    candidates = res.recommendations[0].candidates
    # Only nist_level 5 algorithms should remain
    assert all(c.nist_level >= 5 for c in candidates)
    # ML-DSA-87 should be present
    assert any(c.algorithm == "ML-DSA-87" for c in candidates)
    # ML-DSA-44 and 65 should be excluded
    assert not any(c.algorithm in ["ML-DSA-44", "ML-DSA-65"] for c in candidates)


def test_certificate_key_usage_drives_function():
    # Ambiguous RSA + certificate asset type
    funcs, conf = classify_crypto_function(
        algorithm="RSA-2048",
        asset_type="certificate",
    )
    assert KEY_ESTABLISHMENT in funcs
    assert DIGITAL_SIGNATURE in funcs
    assert conf == 0.60  # Updated: RSA matches name heuristic first with 0.60


def test_unknown_rsa_has_lower_classification_confidence():
    funcs, conf = classify_crypto_function(algorithm="RSA-2048")
    assert KEY_ESTABLISHMENT in funcs
    assert DIGITAL_SIGNATURE in funcs
    assert conf == 0.50


def test_symmetric_algorithm_returns_no_direct_pqc_replacement():
    engine = TOPSISRecommendationEngine()
    req = DummyInput(asset="db", current_algorithm="AES-256")
    res = engine.recommend(req)
    
    assert res.detected_functions == [SYMMETRIC_CRYPTO]
    assert "no direct asymmetric pqc replacement" in res.reason.lower()
    assert res.recommendations == []
    assert res.classification_confidence == 0.99


def test_hash_returns_no_direct_pqc_replacement():
    engine = TOPSISRecommendationEngine()
    req = DummyInput(asset="db", current_algorithm="SHA-256")
    res = engine.recommend(req)
    
    assert res.detected_functions == [HASH_CRYPTO]
    assert "no direct pqc migration" in res.reason.lower()
    assert res.recommendations == []
    assert res.classification_confidence == 0.99


def test_all_knowledge_base_metadata_has_provenance():
    kb = PQCKnowledgeBase()
    for cand in kb.all_candidates:
        assert cand.source.startswith("FIPS")
        assert cand.family in {"ML-KEM", "ML-DSA", "SLH-DSA"}
        assert cand.performance_rank >= 1
        assert cand.sig_or_ct_bytes > 0


def test_all_slh_dsa_standard_names_are_valid():
    kb = PQCKnowledgeBase()
    dsa_cands = kb.candidates_by_family("SLH-DSA")
    assert len(dsa_cands) == 12
    # Ensure standard names exist
    names = {c.name for c in dsa_cands}
    assert "SLH-DSA-SHA2-128s" in names
    assert "SLH-DSA-SHAKE-256f" in names


def test_topsis_equal_candidates_no_nan():
    # If matrix has identical rows, TOPSIS should not divide by zero or NaN
    matrix = [[1.0] * 6, [1.0] * 6]
    res = solve(["A", "B"], matrix, weights=None)
    assert len(res.rankings) == 2
    for r in res.rankings:
        assert not isinstance(r.closeness, complex)
        assert r.closeness >= 0.0


def test_topsis_zero_distance_no_nan():
    # If matrix has identical columns, col norm is handled without zero division
    matrix = [[0.0] * 6, [0.0] * 6]
    res = solve(["A", "B"], matrix, weights=None)
    assert len(res.rankings) == 2
    for r in res.rankings:
        assert not isinstance(r.closeness, complex)


def test_weight_override_normalization():
    weights = {"performance_rank": 10.0, "public_key_bytes": 10.0}
    w = validate_weights(weights)
    assert w["performance_rank"] == 0.5
    assert w["public_key_bytes"] == 0.5
    assert sum(w.values()) == 1.0


def test_recommendation_low_memory_constraint_does_not_override_security():
    engine = TOPSISRecommendationEngine()
    req = DummyInput(
        asset="app",
        current_algorithm="ECDH",
        required_security_level=3,
        memory_constraint="low",
    )
    res = engine.recommend(req)
    
    # Even though memory is low, ML-KEM-512 (level 1) MUST be excluded because of security 3
    names = [c.algorithm for c in res.recommendations[0].candidates]
    assert "ML-KEM-512" not in names
    assert "ML-KEM-768" in names
