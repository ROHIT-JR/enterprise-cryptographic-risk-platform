from cbom_engine import CBOMGenerator


def test_cbom_contains_components_and_dependencies():
    document = CBOMGenerator().generate(
        project={"id": "p1", "name": "Payments", "criticality": "critical"},
        scan={"id": "s1", "source_type": "repository", "target": "payments.zip"},
        assets=[
            {
                "id": "a1",
                "asset_type": "library",
                "name": "OpenSSL",
                "location": "requirements.txt",
                "evidence": "openssl",
                "confidence": 1,
            },
            {
                "id": "a2",
                "asset_type": "algorithm",
                "name": "RSA-2048",
                "algorithm": "RSA-2048",
                "location": "auth.py:4",
                "evidence": "RSA.generate",
                "confidence": 0.99,
                "risk_score": 85,
                "risk_severity": "critical",
            },
        ],
        relationships=[
            {"source_asset_id": "a1", "target_asset_id": "a2", "relationship_type": "CONTAINS"}
        ],
    )

    assert document["bomFormat"] == "ECDAT-CBOM"
    assert len(document["components"]) == 2
    assert document["dependencies"][0]["dependsOn"] == ["urn:ecdat:asset:a2"]
    assert (
        document["components"][1]["cryptoProperties"]["algorithmProperties"]["primitive"]
        == "RSA-2048"
    )
