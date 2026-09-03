from migration_engine.optimizer import DependencyAwareOptimizer
from migration_engine.optimizer_models import OptimizerInput
from typing import Dict, Any

def run_optimizer_validation(dataset: Any) -> Dict[str, Any]:
    optimizer = DependencyAwareOptimizer()

    # We will build a controlled scenario to test dependency chains, blockages, and SCC coordination.
    # We manually construct OptimizerInputs instead of using the full dataset to ensure structure.

    # 1. Dependency chain: A -> B -> C
    # Expected: C should be in earlier wave than B, and B earlier than A
    chain_inputs = [
        OptimizerInput(asset_id="A", asset_name="A", asset_type="app", dependencies=["B"], vendor_ready=True, compatibility_blocked=False),
        OptimizerInput(asset_id="B", asset_name="B", asset_type="service", dependencies=["C"], vendor_ready=True, compatibility_blocked=False),
        OptimizerInput(asset_id="C", asset_name="C", asset_type="library", dependencies=[], vendor_ready=True, compatibility_blocked=False)
    ]
    chain_result = optimizer.optimize(chain_inputs)

    # 2. Blocked prerequisite
    # D -> E (blocked) -> F
    blocked_inputs = [
        OptimizerInput(asset_id="D", asset_name="D", asset_type="app", dependencies=["E"], vendor_ready=True, compatibility_blocked=False),
        OptimizerInput(asset_id="E", asset_name="E", asset_type="service", dependencies=["F"], vendor_ready=False, compatibility_blocked=False),
        OptimizerInput(asset_id="F", asset_name="F", asset_type="library", dependencies=[], vendor_ready=True, compatibility_blocked=False)
    ]
    blocked_result = optimizer.optimize(blocked_inputs)

    # 3. SCC: G <-> H
    scc_inputs = [
        OptimizerInput(asset_id="G", asset_name="G", asset_type="service", dependencies=["H"], vendor_ready=True, compatibility_blocked=False),
        OptimizerInput(asset_id="H", asset_name="H", asset_type="service", dependencies=["G"], vendor_ready=True, compatibility_blocked=False)
    ]
    scc_result = optimizer.optimize(scc_inputs)

    return {
        "chain_waves": {
            "A_wave": chain_result.assets["A"].wave,
            "B_wave": chain_result.assets["B"].wave,
            "C_wave": chain_result.assets["C"].wave
        },
        "blocked_waves": {
            "D_wave": blocked_result.assets["D"].wave,
            "E_wave": blocked_result.assets["E"].wave,
            "F_wave": blocked_result.assets["F"].wave
        },
        "scc_waves": {
            "G_wave": scc_result.assets["G"].wave,
            "H_wave": scc_result.assets["H"].wave
        }
    }
