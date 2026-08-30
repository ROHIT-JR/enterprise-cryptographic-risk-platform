import pytest
from risk_engine.evidence_fusion import EvidenceFusionEngine

def test_evidence_fusion_low_conflict():
    engine = EvidenceFusionEngine()
    sources = [
        {"True": 0.9, "False": 0.05, "Both": 0.05},
        {"True": 0.8, "False": 0.1, "Both": 0.1},
    ]
    result = engine.fuse(sources)
    assert result["conflict"] is False
    assert result["confidence"] >= 80
    assert result["evidence_strength"] in {"High", "Very High"}
