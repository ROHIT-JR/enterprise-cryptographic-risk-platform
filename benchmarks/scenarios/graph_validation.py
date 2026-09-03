import time
import networkx as nx
from typing import Dict, Any
from knowledge_graph.models import GraphPayload, GraphNode, GraphEdge
from graph_analysis.networkx_layer import NetworkXGraphLayer

def run_graph_validation(dataset: Any) -> Dict[str, Any]:
    layer = NetworkXGraphLayer()

    nodes = [GraphNode(id=a.id, label=a.name, type=a.asset_type) for a in dataset.assets]
    edges = [GraphEdge(id=r.id, source=r.source_asset_id, target=r.target_asset_id, type=r.relationship_type) for r in dataset.relationships]

    payload = GraphPayload(nodes=nodes, edges=edges)

    # Build graph
    t0 = time.perf_counter()
    G = layer.build_graph(payload)
    t_build = time.perf_counter() - t0

    # Compute metrics
    t1 = time.perf_counter()
    metrics = layer.compute_metrics(G, project_id=dataset.project_id, organization_id=dataset.organization_id)
    t_compute = time.perf_counter() - t1

    # Isolate expensive routines (betweenness, pagerank) for measurement
    t2 = time.perf_counter()
    if G.number_of_nodes() < 5000:
        nx.betweenness_centrality(G)
        t_betweenness = (time.perf_counter() - t2) * 1000
        betweenness_stage = {"status": "measured", "duration_ms": round(t_betweenness, 2)}
    else:
        betweenness_stage = {
            "status": "skipped",
            "reason": "Exact betweenness benchmark disabled above configured node threshold to avoid excessive benchmark cost."
        }

    t3 = time.perf_counter()
    nx.pagerank(G)
    t_pagerank = (time.perf_counter() - t3) * 1000
    pagerank_stage = {"status": "measured", "duration_ms": round(t_pagerank, 2)}

    # Simulate dependency topological sort
    t4 = time.perf_counter()
    list(nx.topological_sort(nx.DiGraph([(u,v) for u,v in G.edges() if u != v and not nx.has_path(G, v, u)])))
    t_topo = (time.perf_counter() - t4) * 1000
    topo_stage = {"status": "measured", "duration_ms": round(t_topo, 2)}

    # Analyze components and blast-radius ranges
    t_scc_start = time.perf_counter()
    scc = list(nx.strongly_connected_components(G))
    t_scc = time.perf_counter() - t_scc_start
    wcc = list(nx.weakly_connected_components(G))

    blast_radii = [m["blast_radius"] for m in metrics.values()]
    avg_blast_radius = sum(blast_radii) / len(blast_radii) if blast_radii else 0
    max_blast_radius = max(blast_radii) if blast_radii else 0

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "scc_count": len(scc),
        "stages": {
            "betweenness_centrality": betweenness_stage,
            "pagerank": pagerank_stage,
            "topological_sort": topo_stage
        },
        "timings_ms": {
            "build_graph": round(t_build * 1000, 2),
            "compute_metrics": round(t_compute * 1000, 2),
            "scc_detection": round(t_scc * 1000, 2)
        },
        "structural_metrics": {
            "scc_count": len(scc),
            "wcc_count": len(wcc),
            "avg_blast_radius": round(avg_blast_radius, 4),
            "max_blast_radius": round(max_blast_radius, 4)
        }
    }
