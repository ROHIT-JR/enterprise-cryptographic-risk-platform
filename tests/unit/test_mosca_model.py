from risk_engine.mosca_model import MoscaModel


def test_mosca_critical_deadline():
    model = MoscaModel()
    # Override config for deterministic test
    model.quantum_year = 10
    model.confidence = "medium"
    result = model.evaluate(data_lifetime=20, migration_time=5)
    assert result["deadline_risk"] == "Critical"
    assert result["formula"] == "20 + 5 > 10"
    assert "Migration must begin immediately" in result["explanation"]
