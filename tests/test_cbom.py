import json

import pytest

from cbom_engine import CBOMGenerator

PROJECT = {"id": "p1", "name": "Payments", "criticality": "critical"}
SCAN = {"id": "s1", "source_type": "repository", "target": "payments.zip"}


def _asset(asset_id, asset_type, name, **extra):
    return {
        "id": asset_id,
        "asset_type": asset_type,
        "name": name,
        "location": f"{name}.py:1",
        "evidence": name,
        "confidence": 0.9,
        **extra,
    }


def _document():
    return CBOMGenerator().generate(
        project=PROJECT,
        scan=SCAN,
        assets=[
            _asset("a1", "library", "OpenSSL", version="3.0.13", location="requirements.txt"),
            _asset(
                "a2",
                "algorithm",
                "RSA-2048",
                algorithm="RSA-2048",
                risk_score=85,
                risk_severity="critical",
            ),
            _asset("a3", "algorithm", "AES-256-GCM", algorithm="AES-256-GCM"),
            _asset("a4", "algorithm", "SHA-256", algorithm="SHA-256"),
            _asset("a5", "algorithm", "ECC P-256", algorithm="ECC P-256"),
            _asset("a6", "algorithm", "HMAC-SHA256", algorithm="HMAC-SHA256"),
            _asset("a7", "algorithm", "Diffie-Hellman", algorithm="Diffie-Hellman"),
            _asset("a8", "algorithm", "Mystery-Cipher", algorithm="Mystery-Cipher"),
            _asset("a9", "protocol", "TLS 1.3", algorithm="TLS 1.3"),
            _asset("a10", "certificate", "portal cert", algorithm="ECC P-256"),
            _asset("a11", "application", "Payment Service"),
            _asset("a12", "configuration", "tls.conf"),
        ],
        relationships=[
            {"source_asset_id": "a1", "target_asset_id": "a2", "relationship_type": "CONTAINS"},
            {"source_asset_id": "a10", "target_asset_id": "a11", "relationship_type": "PROTECTS"},
        ],
    )


def _component(document, name):
    return next(item for item in document["components"] if item["name"] == name)


def test_cbom_is_cyclonedx_1_6_with_components_and_dependencies():
    document = _document()

    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.6"
    assert document["serialNumber"].startswith("urn:uuid:")
    assert len(document["components"]) == 12
    dependencies = {item["ref"]: item["dependsOn"] for item in document["dependencies"]}
    assert dependencies["urn:ecdat:asset:a1"] == ["urn:ecdat:asset:a2"]
    # "certificate PROTECTS application" means the application depends on the certificate.
    assert dependencies["urn:ecdat:asset:a11"] == ["urn:ecdat:asset:a10"]
    assert dependencies["urn:ecdat:asset:a10"] == []


def test_cbom_maps_algorithms_to_spec_primitives_and_security_levels():
    document = _document()

    rsa = _component(document, "RSA-2048")["cryptoProperties"]["algorithmProperties"]
    assert rsa["primitive"] == "pke"
    assert rsa["parameterSetIdentifier"] == "2048"
    assert rsa["classicalSecurityLevel"] == 112
    assert rsa["nistQuantumSecurityLevel"] == 0  # broken by Shor

    aes = _component(document, "AES-256-GCM")["cryptoProperties"]["algorithmProperties"]
    assert (aes["primitive"], aes["mode"], aes["nistQuantumSecurityLevel"]) == ("ae", "gcm", 5)

    sha = _component(document, "SHA-256")["cryptoProperties"]["algorithmProperties"]
    assert (sha["primitive"], sha["nistQuantumSecurityLevel"]) == ("hash", 2)

    ecc = _component(document, "ECC P-256")["cryptoProperties"]["algorithmProperties"]
    assert (ecc["primitive"], ecc["curve"]) == ("signature", "secp256r1")

    assert (
        _component(document, "HMAC-SHA256")["cryptoProperties"]["algorithmProperties"]["primitive"]
        == "mac"
    )
    assert (
        _component(document, "Diffie-Hellman")["cryptoProperties"]["algorithmProperties"][
            "primitive"
        ]
        == "key-agree"
    )
    # Unrecognised algorithms fall back to the spec's "unknown" instead of inventing a value.
    assert (
        _component(document, "Mystery-Cipher")["cryptoProperties"]["algorithmProperties"][
            "primitive"
        ]
        == "unknown"
    )


def test_cbom_covers_protocols_certificates_and_non_crypto_components():
    document = _document()

    tls = _component(document, "TLS 1.3")["cryptoProperties"]
    assert tls["assetType"] == "protocol"
    assert tls["protocolProperties"] == {"type": "tls", "version": "1.3"}
    assert _component(document, "portal cert")["cryptoProperties"]["assetType"] == "certificate"
    assert _component(document, "OpenSSL")["type"] == "library"
    assert _component(document, "Payment Service")["type"] == "application"
    assert _component(document, "tls.conf")["type"] == "file"
    assert "cryptoProperties" not in _component(document, "Payment Service")


def test_cbom_carries_risk_scores_in_component_and_metadata_properties():
    document = _document()

    properties = {
        item["name"]: item["value"] for item in _component(document, "RSA-2048")["properties"]
    }
    assert properties["ecdat:risk-score"] == "85"
    assert properties["ecdat:risk-severity"] == "critical"
    metadata = {item["name"]: item["value"] for item in document["metadata"]["properties"]}
    assert metadata["ecdat:risk-score-max"] == "85.0"
    assert metadata["ecdat:risk-count-critical"] == "1"
    assert metadata["ecdat:components-risk-scored"] == "1"


def test_cbom_validates_against_the_official_cyclonedx_1_6_schema():
    cyclonedx = pytest.importorskip("cyclonedx.validation.json")
    from cyclonedx.schema import SchemaVersion

    validator = cyclonedx.JsonStrictValidator(SchemaVersion.V1_6)
    assert validator.validate_str(json.dumps(_document())) is None

    # Negative control: prove the validator would actually catch a bad document.
    broken = _document()
    broken["components"][1]["cryptoProperties"]["algorithmProperties"]["primitive"] = "RSA-2048"
    assert validator.validate_str(json.dumps(broken)) is not None
