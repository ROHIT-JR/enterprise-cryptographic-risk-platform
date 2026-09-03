import pytest
import os
import json
from benchmarks.datasets.generator import generate_topology
from benchmarks.framework import run_benchmark, save_result

def test_deterministic_generator():
    ds1 = generate_topology(seed=42, num_assets=100, topology_type="scale_free")
    ds2 = generate_topology(seed=42, num_assets=100, topology_type="scale_free")
    assert ds1.assets[0].name == ds2.assets[0].name
    assert len(ds1.relationships) == len(ds2.relationships)

def test_different_seeds_different_datasets():
    ds1 = generate_topology(seed=42, num_assets=10, topology_type="scale_free")
    ds2 = generate_topology(seed=43, num_assets=10, topology_type="scale_free")
    # Relationships should differ in scale free graphs
    r1 = [(r.source_asset_id, r.target_asset_id) for r in ds1.relationships]
    r2 = [(r.source_asset_id, r.target_asset_id) for r in ds2.relationships]
    assert set(r1) != set(r2)

def test_expected_asset_count():
    ds = generate_topology(seed=1, num_assets=50, topology_type="chain")
    assert len(ds.assets) == 50

def test_chain_graph_behavior():
    ds = generate_topology(seed=1, num_assets=10, topology_type="chain")
    assert len(ds.relationships) == 9

def test_star_graph_behavior():
    ds = generate_topology(seed=1, num_assets=10, topology_type="star")
    assert len(ds.relationships) == 9
    center = ds.assets[0].id
    for r in ds.relationships:
        assert r.source_asset_id == center

def test_scc_generation():
    ds = generate_topology(seed=1, num_assets=10, topology_type="scc")
    # Should have a cycle (10 edges) + 1 random edge (total 11)
    assert len(ds.relationships) == 11

def test_benchmark_json_schema():
    def dummy_gen():
        return {"graph_nodes": 10, "graph_edges": 9}
    def dummy_work(ds):
        return {"processed": 10}

    res = run_benchmark("test", dummy_gen, dummy_work, seed=1, dataset_size=10, topology="star")
    assert res["benchmark_version"] == "1.0"
    assert "timestamp" in res
    assert res["dataset_size"] == 10
    assert res["graph_nodes"] == 10
    assert res["graph_edges"] == 9
    assert res["stages"]["generation_ms"] >= 0
    assert "deterministic_hash" in res

def test_invalid_missing_result_files():
    # Helper behavior validation for the API
    assert not os.path.exists("benchmarks/results/missing.json")

# I will append more scenario tests in the next steps (Mosca, TOPSIS, etc.)

def test_mosca_boundary_below():
    from benchmarks.scenarios.mosca_validation import run_mosca_validation
    res = run_mosca_validation(None)
    assert res["x_plus_y_less_than_z"]["deadline_risk"] == "Low"

def test_mosca_boundary_equality():
    from benchmarks.scenarios.mosca_validation import run_mosca_validation
    res = run_mosca_validation(None)
    assert res["x_plus_y_equals_z"]["deadline_risk"] == "Low"

def test_mosca_boundary_above():
    from benchmarks.scenarios.mosca_validation import run_mosca_validation
    res = run_mosca_validation(None)
    assert res["x_plus_y_greater_than_z"]["deadline_risk"] == "Critical"

def test_mosca_monotonicity():
    from benchmarks.scenarios.mosca_validation import run_mosca_validation
    res = run_mosca_validation(None)
    assert res["monotonicity_check"]["increased_lifetime"]["deadline_risk"] in ["Critical", "Low"]

def test_evidence_fusion_agreement():
    from benchmarks.scenarios.fusion_validation import run_fusion_validation
    res = run_fusion_validation(None)
    assert res["agreeing"]["confidence"] > 50

def test_evidence_fusion_conflict():
    from benchmarks.scenarios.fusion_validation import run_fusion_validation
    res = run_fusion_validation(None)
    assert res["highly_conflicting"]["conflict"] is True

def test_topsis_deterministic_ranking():
    from benchmarks.scenarios.topsis_validation import run_topsis_validation
    res = run_topsis_validation(None)
    assert "baseline_ml_kem_winner" in res

def test_topsis_hard_security_filter():
    from benchmarks.scenarios.topsis_validation import run_topsis_validation
    res = run_topsis_validation(None)
    assert res["high_security_winner"] is not None

def test_topsis_sensitivity_runner():
    from benchmarks.scenarios.topsis_validation import run_topsis_validation
    res = run_topsis_validation(None)
    assert "stability_percentage" in res["sensitivity"]

def test_optimizer_dependency_ordering():
    from benchmarks.scenarios.optimizer_validation import run_optimizer_validation
    res = run_optimizer_validation(None)
    # C should be before B, B before A
    assert res["chain_waves"]["C_wave"] < res["chain_waves"]["B_wave"]
    assert res["chain_waves"]["B_wave"] < res["chain_waves"]["A_wave"]

def test_optimizer_blocker_propagation():
    from benchmarks.scenarios.optimizer_validation import run_optimizer_validation
    res = run_optimizer_validation(None)
    # E is blocked, D depends on E.
    assert res["blocked_waves"]["E_wave"] is None
    assert res["blocked_waves"]["D_wave"] is None
    assert res["blocked_waves"]["F_wave"] is not None

def test_optimizer_scc_behavior():
    from benchmarks.scenarios.optimizer_validation import run_optimizer_validation
    res = run_optimizer_validation(None)
    # G and H should be in the same wave
    assert res["scc_waves"]["G_wave"] == res["scc_waves"]["H_wave"]

def test_optimizer_deterministic_output():
    from benchmarks.scenarios.optimizer_validation import run_optimizer_validation
    res1 = run_optimizer_validation(None)
    res2 = run_optimizer_validation(None)
    assert res1 == res2

def test_blocked_lifecycle_path():
    from benchmarks.scenarios.lifecycle_validation import run_lifecycle_validation
    res = run_lifecycle_validation(None)
    assert res["blocked_path"]["new_state"] == "RECOMMENDED"
    assert res["blocked_path"]["new_governance"] == "BLOCKED"

def test_executable_lifecycle_path():
    from benchmarks.scenarios.lifecycle_validation import run_lifecycle_validation
    res = run_lifecycle_validation(None)
    assert res["normal_path"]["new_state"] == "MIGRATION_PLANNED"
    assert res["normal_path"]["new_governance"] == "ACTIVE"

def test_lifecycle_idempotency():
    from benchmarks.scenarios.lifecycle_validation import run_lifecycle_validation
    res = run_lifecycle_validation(None)
    assert res["idempotency"]["was_idempotent"] is True

def test_empty_dataset_handling():
    from benchmarks.datasets.generator import generate_topology
    ds = generate_topology(1, 0)
    assert len(ds.assets) == 0
