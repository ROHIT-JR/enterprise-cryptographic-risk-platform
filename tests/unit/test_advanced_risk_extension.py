from risk_engine.advanced_risk_extension import AdvancedRiskExtension


def test_advanced_risk_extension_enhance():
    ext = AdvancedRiskExtension()
    final_result = {
        "score": 75,
        "severity": "high",
        "explanation": ["reason1", "reason2"],
        "components": {"quantum_vulnerability": 20, "hndl_exposure": 15},
    }
    mosca = {
        "deadline_risk": "Critical",
        "formula": "10 + 5 > 2035",
        "explanation": "Migration must begin immediately",
    }
    evidence = {
        "confidence": 92,
        "evidence_strength": "High",
        "conflict": False,
    }
    enhanced = ext.enhance(final_result, mosca, evidence)
    assert enhanced["model"] == "AdvancedRiskExtension"
    assert enhanced["version"] == "1.0.0"
    assert enhanced["result"]["score"] == 75
    assert enhanced["result"]["mosca_deadline_risk"] == "Critical"
    assert enhanced["result"]["evidence_confidence"] == 92
    assert enhanced["parameters"]["evidence_strength"] == "High"
