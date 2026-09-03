import os
import time
import json
import platform
os.environ["NEO4J_ENABLED"] = "false"

from benchmarks.framework import run_benchmark
from benchmarks.datasets.generator import generate_topology
from benchmarks.scenarios.mosca_validation import run_mosca_validation
from benchmarks.scenarios.graph_validation import run_graph_validation
from benchmarks.scenarios.topsis_validation import run_topsis_validation
from benchmarks.scenarios.optimizer_validation import run_optimizer_validation
from benchmarks.scenarios.fusion_validation import run_fusion_validation
from benchmarks.scenarios.lifecycle_validation import run_lifecycle_validation

def run_all(sizes: list[int]):
    topologies = ["chain", "star", "scc", "scale_free"]

    # We will build a canonical structure
    canonical = {
        "benchmark_version": "1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu": platform.processor() or "Unknown CPU"
        },
        "experiments": []
    }

    for size in sizes:
        for topology in topologies:
            print(f"Running benchmark size {size} topology {topology}")
            def gen(): return generate_topology(42, size, topology)

            res_mosca = run_benchmark(f"Mosca_{topology}_{size}", gen, run_mosca_validation, 42, size, topology)
            res_graph = run_benchmark(f"Graph_{topology}_{size}", gen, run_graph_validation, 42, size, topology)
            res_topsis = run_benchmark(f"TOPSIS_{topology}_{size}", gen, run_topsis_validation, 42, size, topology)
            res_optimizer = run_benchmark(f"Optimizer_{topology}_{size}", gen, run_optimizer_validation, 42, size, topology)
            res_fusion = run_benchmark(f"Fusion_{topology}_{size}", gen, run_fusion_validation, 42, size, topology)
            res_lifecycle = run_benchmark(f"Lifecycle_{topology}_{size}", gen, run_lifecycle_validation, 42, size, topology)

            # Extract just the stages from the Graph validation to be clean
            graph_stages = res_graph.get("result_summary", {}).get("stages", {})
            if not graph_stages:
                # Mock if missing for whatever reason
                graph_stages = {
                    "betweenness_centrality": {"status": "skipped", "reason": "Not measured"}
                }

            canonical["experiments"].append({
                "nodes": size,
                "topology": topology,
                "dataset_seed": 42,
                "graph_nodes": res_graph["graph_nodes"],
                "graph_edges": res_graph["graph_edges"],
                "total_duration_ms": round(sum(d.get("total_duration_ms", 0) for d in [res_mosca, res_graph, res_topsis, res_optimizer, res_fusion, res_lifecycle]), 2),
                "stages": graph_stages,
                "scenarios": {
                    "mosca": res_mosca["result_summary"],
                    "graph": res_graph["result_summary"],
                    "topsis": res_topsis["result_summary"],
                    "optimizer": res_optimizer["result_summary"],
                    "fusion": res_fusion["result_summary"],
                    "lifecycle": res_lifecycle["result_summary"]
                }
            })

    os.makedirs("benchmarks/results", exist_ok=True)
    with open("benchmarks/results/validation_baseline.json", "w") as f:
        json.dump(canonical, f, indent=2)
    print("Canonical benchmark artifact written to benchmarks/results/validation_baseline.json")

if __name__ == "__main__":
    run_all([100, 1000, 5000, 10000])
