from migration_engine.optimizer import DependencyAwareOptimizer
from migration_engine.optimizer_models import OptimizerInput


def test_empty_input():
    optimizer = DependencyAwareOptimizer()
    result = optimizer.optimize([])
    assert not result.waves
    assert not result.assets

def test_single_asset():
    optimizer = DependencyAwareOptimizer()
    result = optimizer.optimize([
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", quantum_score=100)
    ])
    assert len(result.waves) == 1
    assert result.assets["a1"].wave == 1

def test_independent_assets():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="a1",
            asset_name="A1",
            asset_type="app",
            quantum_score=100,
            migration_complexity=0,
        ),
        OptimizerInput(
            asset_id="a2",
            asset_name="A2",
            asset_type="app",
            quantum_score=50,
            migration_complexity=50,
        ),
    ]
    result = optimizer.optimize(inputs)
    assert len(result.waves) == 1
    assert result.assets["a1"].priority_score > result.assets["a2"].priority_score

def test_simple_dependency_chain():
    optimizer = DependencyAwareOptimizer()
    # a3 -> a2 -> a1
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app"),
        OptimizerInput(asset_id="a2", asset_name="A2", asset_type="app", dependencies=["a1"]),
        OptimizerInput(asset_id="a3", asset_name="A3", asset_type="app", dependencies=["a2"]),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a1"].wave == 1
    assert result.assets["a2"].wave == 2
    assert result.assets["a3"].wave == 3

def test_verified_dependency_direction():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="consumer", asset_name="Consumer", asset_type="app", dependencies=["library"]
        ),
        OptimizerInput(asset_id="library", asset_name="Library", asset_type="app"),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["library"].wave == 1
    assert result.assets["consumer"].wave == 2

def test_dependency_overrides_raw_priority():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="consumer",
            asset_name="Consumer",
            asset_type="app",
            quantum_score=100,
            dependencies=["library"],
        ),
        OptimizerInput(
            asset_id="library", asset_name="Library", asset_type="app", quantum_score=10
        ),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["library"].wave == 1
    assert result.assets["consumer"].wave == 2

def test_high_risk_asset_prioritization():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="high", asset_name="High", asset_type="app", quantum_score=100),
        OptimizerInput(asset_id="low", asset_name="Low", asset_type="app", quantum_score=10)
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["high"].priority_score > result.assets["low"].priority_score
    assert result.waves[1][0].asset_id == "high"

def test_blast_radius_influence():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", blast_radius=100),
        OptimizerInput(asset_id="a2", asset_name="A2", asset_type="app", blast_radius=10)
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a1"].priority_score > result.assets["a2"].priority_score

def test_business_criticality_influence():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", business_criticality=100),
        OptimizerInput(asset_id="a2", asset_name="A2", asset_type="app", business_criticality=10)
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a1"].priority_score > result.assets["a2"].priority_score

def test_migration_complexity_penalty():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="hard", asset_name="Hard", asset_type="app", migration_complexity=100
        ),
        OptimizerInput(
            asset_id="easy", asset_name="Easy", asset_type="app", migration_complexity=0
        ),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["easy"].priority_score > result.assets["hard"].priority_score

def test_missing_factor_excluded_rather_than_half():
    optimizer = DependencyAwareOptimizer()
    item_full = OptimizerInput(
        asset_id="full",
        asset_name="Full",
        asset_type="app",
        quantum_score=100,
        migration_complexity=0,
        hndl_score=100,
        blast_radius=100,
        business_criticality=100,
    )
    item_missing = OptimizerInput(
        asset_id="missing",
        asset_name="Missing",
        asset_type="app",
        quantum_score=100,
        migration_complexity=0,
        hndl_score=100,
        blast_radius=100,
        business_criticality=None,
    )

    result = optimizer.optimize([item_full, item_missing])
    assert result.assets["full"].priority_score == 1.0
    assert result.assets["missing"].priority_score == 1.0

def test_active_weights_renormalized():
    optimizer = DependencyAwareOptimizer(weights={"quantum_score": 0.5, "hndl_score": 0.5})
    inputs = [
        OptimizerInput(
            asset_id="a1", asset_name="A1", asset_type="app", quantum_score=50, hndl_score=None
        )
    ]
    result = optimizer.optimize(inputs)
    # quantum 50/100 = 0.5. With hndl missing the active weight is 0.5, so the weighted
    # sum (0.5 * 0.5 = 0.25) is renormalised by 0.5, giving a priority score of 0.5.
    assert result.assets["a1"].priority_score == 0.5

def test_missing_factors_reduce_confidence():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="full",
            asset_name="Full",
            asset_type="app",
            quantum_score=100,
            hndl_score=100,
            blast_radius=100,
            business_criticality=100,
            migration_complexity=100,
        ),
        OptimizerInput(
            asset_id="missing", asset_name="Missing", asset_type="app", quantum_score=100
        ),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["full"].confidence == 1.0
    assert result.assets["missing"].confidence < 1.0

def test_deterministic_output():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", quantum_score=10),
        OptimizerInput(asset_id="a2", asset_name="A2", asset_type="app", quantum_score=10)
    ]
    r1 = optimizer.optimize(inputs)
    r2 = optimizer.optimize(inputs)
    assert r1.waves[1][0].asset_id == r2.waves[1][0].asset_id
    assert r1.waves[1][1].asset_id == r2.waves[1][1].asset_id

def test_hard_vendor_blocker_produces_no_executable_wave():
    optimizer = DependencyAwareOptimizer()
    inputs = [OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", vendor_ready=False)]
    result = optimizer.optimize(inputs)
    assert result.assets["a1"].wave is None
    assert "Vendor not ready" in result.assets["a1"].constraints

def test_unsupported_compatibility_produces_blocker():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app", compatibility_blocked=True)
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a1"].wave is None
    assert "Compatibility blocked" in result.assets["a1"].constraints

def test_blocked_prerequisite_propagates_to_dependent():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="dep", asset_name="Dep", asset_type="app", vendor_ready=False),
        OptimizerInput(
            asset_id="consumer", asset_name="Consumer", asset_type="app", dependencies=["dep"]
        ),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["dep"].wave is None
    assert result.assets["consumer"].wave is None
    assert "Blocked by prerequisites: dep" in result.assets["consumer"].constraints

def test_scc_two_node_cycle():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a", asset_name="A", asset_type="app", dependencies=["b"]),
        OptimizerInput(asset_id="b", asset_name="B", asset_type="app", dependencies=["a"])
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a"].wave == result.assets["b"].wave
    assert result.assets["a"].wave == 1

def test_scc_multi_node_cycle():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a", asset_name="A", asset_type="app", dependencies=["b"]),
        OptimizerInput(asset_id="b", asset_name="B", asset_type="app", dependencies=["c"]),
        OptimizerInput(asset_id="c", asset_name="C", asset_type="app", dependencies=["a"])
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a"].wave == result.assets["b"].wave == result.assets["c"].wave

def test_scc_members_share_coordinated_assignment():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a", asset_name="A", asset_type="app", dependencies=["b"]),
        OptimizerInput(asset_id="b", asset_name="B", asset_type="app", dependencies=["a"])
    ]
    result = optimizer.optimize(inputs)
    assert "cycle" in result.assets["a"].rationale[0].lower()

def test_multiple_migration_waves():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(asset_id="a1", asset_name="A1", asset_type="app"),
        OptimizerInput(asset_id="a2", asset_name="A2", asset_type="app", dependencies=["a1"]),
        OptimizerInput(asset_id="a3", asset_name="A3", asset_type="app", dependencies=["a2"])
    ]
    result = optimizer.optimize(inputs)
    assert len(result.waves) == 3

def test_scc_and_blocker_interaction():
    optimizer = DependencyAwareOptimizer()
    inputs = [
        OptimizerInput(
            asset_id="a", asset_name="A", asset_type="app", dependencies=["b"], vendor_ready=False
        ),
        OptimizerInput(asset_id="b", asset_name="B", asset_type="app", dependencies=["a"]),
    ]
    result = optimizer.optimize(inputs)
    assert result.assets["a"].wave is None
    assert result.assets["b"].wave is None
    assert any("Blocked" in c for c in result.assets["b"].constraints)
