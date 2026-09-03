import json
import time
import platform
import os
import hashlib
from datetime import datetime, UTC
from typing import Dict, Any, Callable

def run_benchmark(
    name: str,
    dataset_generator: Callable[[], Dict[str, Any]],
    workload: Callable[[Dict[str, Any]], Dict[str, Any]],
    seed: int,
    dataset_size: int,
    topology: str
) -> Dict[str, Any]:

    t0 = time.perf_counter()
    dataset_metadata = dataset_generator()
    t_gen = time.perf_counter() - t0

    t1 = time.perf_counter()
    result = workload(dataset_metadata)
    t_work = time.perf_counter() - t1

    # Calculate deterministic hash of results to detect stability
    res_str = json.dumps(result, sort_keys=True, default=str)
    res_hash = hashlib.sha256(res_str.encode('utf-8')).hexdigest()

    output = {
        "benchmark_version": "1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "name": name,
        "dataset_seed": seed,
        "dataset_size": dataset_size,
        "topology": topology,
        "graph_nodes": dataset_metadata.get("graph_nodes", dataset_size) if isinstance(dataset_metadata, dict) else (len(dataset_metadata.assets) if hasattr(dataset_metadata, "assets") else dataset_size),
        "graph_edges": dataset_metadata.get("graph_edges", 0) if isinstance(dataset_metadata, dict) else (len(dataset_metadata.relationships) if hasattr(dataset_metadata, "relationships") else 0),
        "environment": {
            "os": platform.platform(),
            "python_version": platform.python_version(),
            "cpu": platform.processor() or "Unknown"
        },
        "stages": {
            "generation_ms": round(t_gen * 1000, 2),
            "execution_ms": round(t_work * 1000, 2)
        },
        "total_duration_ms": round((t_gen + t_work) * 1000, 2),
        "deterministic_hash": res_hash,
        "result_summary": result
    }
    return output

def save_result(result: Dict[str, Any], filename: str):
    os.makedirs("benchmarks/results", exist_ok=True)
    path = os.path.join("benchmarks/results", filename)
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
