import pytest

from risk_engine.engine import RiskEngine
from risk_engine.models import RiskInput
from risk_engine.quantum_risk import QuantumRiskEngine
from scanners.patterns import ALGORITHM_PATTERNS


def _matching_patterns(evidence: str) -> set[str]:
    return {pattern.name for pattern in ALGORITHM_PATTERNS if pattern.expression.search(evidence)}


@pytest.mark.parametrize(
    "evidence",
    [
        "cipher = ARC4.new(key)",
        "cipher = RC4.new(key)",
        "EVP_rc4()",
        'Cipher.getInstance("RC4")',
    ],
)
def test_rc4_is_detected(evidence):
    assert "RC4" in _matching_patterns(evidence)


@pytest.mark.parametrize(
    "evidence",
    [
        "digest = hashlib.md5(data).hexdigest()",
        'MessageDigest.getInstance("MD5")',
        'const hash = createHash("md5")',
        "EVP_md5()",
    ],
)
def test_md5_is_detected(evidence):
    assert "MD5" in _matching_patterns(evidence)


@pytest.mark.parametrize(
    "evidence",
    [
        'API_KEY = "AKIAIOSFODNN7EXAMPLEKEY123456"',
        'secret_key: "MyS3cretValueThatIsLongEnough"',
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_hardcoded_key_is_detected(evidence):
    assert "Hardcoded Key" in _matching_patterns(evidence)


@pytest.mark.parametrize(
    "evidence",
    [
        "password = getenv('DB_PASSWORD')",
        "normal_variable = 5",
        "api_key = load_from_vault()",
    ],
)
def test_hardcoded_key_does_not_false_positive_on_dynamic_lookups(evidence):
    assert "Hardcoded Key" not in _matching_patterns(evidence)


@pytest.mark.parametrize(
    ("algorithm", "expected_severity", "expected_quantum_classification"),
    [
        ("RC4", "critical", "critical"),
        ("MD5", "critical", "high"),
        ("Hardcoded Key", "critical", "unknown"),
    ],
)
def test_new_findings_score_the_expected_severity(
    algorithm, expected_severity, expected_quantum_classification
):
    risk = RiskEngine().assess(
        RiskInput(
            name=algorithm,
            algorithm=algorithm,
            asset_type="algorithm",
            criticality="medium",
            dependency_count=0,
            confidence=0.95,
            evidence_count=1,
            details={},
        )
    )
    assert risk.severity == expected_severity

    quantum = QuantumRiskEngine().assess(algorithm)
    assert quantum.classification == expected_quantum_classification


def test_hardcoded_key_is_not_treated_as_quantum_vulnerable():
    # A hardcoded secret is a key-management hygiene issue, not something
    # Shor's or Grover's algorithm makes worse - it should not be flagged
    # "quantum_vulnerable" even though it scores critical in the general
    # risk engine.
    quantum = QuantumRiskEngine().assess("Hardcoded Key")
    assert quantum.quantum_vulnerable is False


def test_algorithm_risks_database_has_the_new_entries():
    for algorithm in ("RC4", "MD5", "DES", "3DES", "SHA-1"):
        assessment = QuantumRiskEngine().assess(algorithm)
        assert assessment.classification != "unknown", f"{algorithm} should be mapped"
