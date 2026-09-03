from risk_engine.evidence_fusion import EvidenceFusionEngine
from typing import Dict, Any

def run_fusion_validation(dataset: Dict[str, Any]) -> Dict[str, Any]:
    engine = EvidenceFusionEngine()

    # 1. Strongly agreeing evidence
    agreeing = [
        {"True": 0.8, "False": 0.1, "Both": 0.1},
        {"True": 0.7, "False": 0.1, "Both": 0.2},
        {"True": 0.9, "False": 0.0, "Both": 0.1}
    ]

    # 2. Weak evidence
    weak = [
        {"True": 0.4, "False": 0.3, "Both": 0.3},
        {"True": 0.3, "False": 0.2, "Both": 0.5}
    ]

    # 3. Conflicting evidence
    conflicting = [
        {"True": 0.8, "False": 0.1, "Both": 0.1},
        {"True": 0.1, "False": 0.8, "Both": 0.1}
    ]

    # 4. Highly conflicting evidence
    highly_conflicting = [
        {"True": 0.99, "False": 0.0, "Both": 0.01},
        {"True": 0.0, "False": 0.99, "Both": 0.01}
    ]

    # 5. Missing evidence
    missing = []

    # 6. Single source
    single = [
        {"True": 0.6, "False": 0.2, "Both": 0.2}
    ]

    return {
        "agreeing": engine.fuse(agreeing),
        "weak": engine.fuse(weak),
        "conflicting": engine.fuse(conflicting),
        "highly_conflicting": engine.fuse(highly_conflicting),
        "missing": engine.fuse(missing),
        "single": engine.fuse(single)
    }
