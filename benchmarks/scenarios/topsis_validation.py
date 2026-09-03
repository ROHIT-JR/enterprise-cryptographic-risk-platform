from migration_engine.topsis_recommendation import TOPSISRecommendationEngine
from migration_engine.pqc_recommendation import PQCRecommendationInput
from typing import Dict, Any

def run_topsis_validation(dataset: Any) -> Dict[str, Any]:
    engine = TOPSISRecommendationEngine()

    # 1. Deterministic ranking on standard ML-KEM use case
    req_kem = PQCRecommendationInput(
        asset="benchmark_asset_1",
        current_algorithm="RSA-2048",
        use_case="encryption",
        compatibility="standard",
        memory_constraint="standard"
    )
    res_kem = engine.recommend(req_kem)

    # 2. Hard security filter (e.g. demanding high security)
    req_high_sec = PQCRecommendationInput(
        asset="benchmark_asset_2",
        current_algorithm="RSA-4096",
        use_case="encryption",
        compatibility="standard",
        memory_constraint="standard"
    )
    res_high_sec = engine.recommend(req_high_sec)

    # 3. Sensitivity Analysis
    # Vary weights by +/- 10%
    base_weights = engine.weights.copy()
    perturbed_weights = base_weights.copy()
    perturbed_weights["performance_rank"] *= 1.10
    perturbed_weights["compatibility"] *= 0.90

    engine_perturbed = TOPSISRecommendationEngine(weights=perturbed_weights)
    res_perturbed = engine_perturbed.recommend(req_kem)

    # Check ranking changes
    base_winner = res_kem.recommended_algorithm
    perturbed_winner = res_perturbed.recommended_algorithm
    stability = 100 if base_winner == perturbed_winner else 0

    return {
        "baseline_ml_kem_winner": res_kem.recommended_algorithm,
        "high_security_winner": res_high_sec.recommended_algorithm,
        "sensitivity": {
            "base_winner": base_winner,
            "perturbed_winner": perturbed_winner,
            "stability_percentage": stability
        }
    }
