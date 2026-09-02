"""NetworkX based graph intelligence layer.

Converts the Neo4j project graph into a NetworkX directed graph and
calculates centrality metrics, community detection, and a derived
blast‑radius score.
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from backend.app.services.neo4j_service import create_graph_store
from knowledge_graph.models import GraphPayload

logger = logging.getLogger(__name__)

# Default weight configuration – can be overridden at init time.
DEFAULT_WEIGHTS = {
    "degree": 0.25,
    "betweenness": 0.25,
    "pagerank": 0.25,
    "dependency": 0.25,
}

SUPPORTED_RELATIONSHIPS = frozenset({"USES", "CONTAINS", "DEPENDS_ON", "PROTECTS"})


def _validate_weights(weights: dict[str, float] | None) -> dict[str, float]:
    """Validate and normalize configurable centrality weights.

    Rejects unknown keys and negative values. Falls back safely to DEFAULT_WEIGHTS
    if invalid, and normalizes valid weights so their sum equals 1.0.
    """
    if not weights:
        return dict(DEFAULT_WEIGHTS)
    allowed_keys = set(DEFAULT_WEIGHTS.keys())
    if not set(weights.keys()).issubset(allowed_keys):
        logger.warning("Unknown weight keys in %s; using default weights", weights)
        return dict(DEFAULT_WEIGHTS)
    if any(v < 0 for v in weights.values()):
        logger.warning("Negative weight values in %s; using default weights", weights)
        return dict(DEFAULT_WEIGHTS)
    total = sum(weights.get(k, 0.0) for k in allowed_keys)
    if total <= 0:
        logger.warning("Zero sum weights in %s; using default weights", weights)
        return dict(DEFAULT_WEIGHTS)
    return {k: weights.get(k, 0.0) / total for k in allowed_keys}


class NetworkXGraphLayer:
    """Encapsulates conversion and analytics on the Neo4j graph.

    The class is deliberately lightweight – it fetches the Neo4j payload,
    builds a ``networkx.DiGraph`` and computes a set of metrics. All methods
    are tolerant of failures; on error an empty mapping is returned so the
    intelligence pipeline can fall back to the existing ``DependencyCentralityEngine``.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = _validate_weights(weights)

    # ---------------------------------------------------------------------
    # Neo4j → NetworkX conversion
    # ---------------------------------------------------------------------
    def fetch_payload(
        self, project_id: str, organization_id: str | None = None
    ) -> GraphPayload | None:
        """Retrieve the Neo4j project sub‑graph.

        Returns ``None`` if the Neo4j store is disabled or the query fails.
        Guarantees that the Neo4j store is reliably closed.
        """
        store = create_graph_store()
        try:
            if not store.enabled:
                logger.warning("Neo4j integration is disabled – NetworkX layer will be a no‑op")
                return None
            return store.query(project_id=project_id, organization_id=organization_id)
        except Exception as exc:  # defensive
            logger.exception("Failed to query Neo4j for project %s: %s", project_id, exc)
            return None
        finally:
            if hasattr(store, "close"):
                store.close()

    def build_graph(self, payload: GraphPayload) -> nx.DiGraph:
        """Build a directed NetworkX graph from a ``GraphPayload``.

        Excludes the project node and project-membership edges so that
        centrality calculations are not artificially distorted.
        Only supported asset-to-asset relationships are included.
        """
        G = nx.DiGraph()
        asset_ids: set[str] = set()
        for node in payload.nodes:
            if node.type == "project" or node.label == "Project" or node.id.startswith("project:"):
                continue
            asset_ids.add(node.id)
            G.add_node(
                node.id,
                label=node.label,
                type=node.type,
                **node.properties,
            )
        for edge in payload.edges:
            rel_type = edge.type.upper()
            if rel_type not in SUPPORTED_RELATIONSHIPS:
                continue
            # Ensure both endpoints are asset nodes (excludes Project->Asset edges)
            if edge.source in asset_ids and edge.target in asset_ids:
                G.add_edge(
                    edge.source,
                    edge.target,
                    type=rel_type,
                    **edge.properties,
                )
        return G

    # ---------------------------------------------------------------------
    # Metric calculation
    # ---------------------------------------------------------------------
    def _community_assignments(self, G: nx.DiGraph) -> dict[str, int]:
        """Detect communities using Louvain with a fixed seed if available.

        Returns a mapping node_id → community_id. If Louvain is unavailable, an
        empty dict is returned and callers can treat the node as having no
        community.
        """
        if G.number_of_nodes() == 0:
            return {}
        try:
            from networkx.algorithms.community import louvain_communities
        except Exception:
            logger.debug("Louvain community detection not available in this NetworkX version")
            return {}
        try:
            try:
                communities = list(louvain_communities(G, seed=42))
            except TypeError:
                communities = list(louvain_communities(G))
        except Exception as exc:  # defensive
            logger.exception("Louvain community detection failed: %s", exc)
            return {}
        node_to_comm: dict[str, int] = {}
        for idx, comm in enumerate(communities):
            for nid in comm:
                node_to_comm[nid] = idx
        return node_to_comm

    def compute_metrics(
        self,
        G: nx.DiGraph,
        project_id: str,
        organization_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Calculate all required metrics for each node.

        Handles empty and single-node graphs gracefully, clamps normalized scores to
        0.0-1.0, uses deterministic algorithms with fixed seeds, closes the Neo4j
        store reliably, and preserves computed NetworkX centralities even if Neo4j
        dependency metrics fail.
        """
        num_nodes = G.number_of_nodes()
        if num_nodes == 0:
            logger.warning("Empty graph for project %s – skipping NetworkX metrics", project_id)
            return {}

        try:
            # Basic centralities (NetworkX normalises automatically)
            degree = nx.degree_centrality(G)
            if num_nodes > 500:
                k = min(50, num_nodes)
                betweenness = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)
            else:
                betweenness = nx.betweenness_centrality(G, normalized=True)
            pagerank = nx.pagerank(G)
        except Exception as exc:
            logger.exception("Centrality calculation failed for project %s: %s", project_id, exc)
            return {}

        # Community detection (optional)
        community_map = self._community_assignments(G)

        # Dependency metrics from Neo4j (degree of neighbouring assets)
        dep_metrics: dict[str, dict[str, Any]] = {}
        store = create_graph_store()
        try:
            if store.enabled:
                dep_metrics = store.dependency_metrics(
                    project_id=project_id, organization_id=organization_id
                )
        except Exception as exc:  # defensive
            logger.exception("Failed to fetch Neo4j dependency metrics for %s: %s", project_id, exc)
            dep_metrics = {}
        finally:
            if hasattr(store, "close"):
                store.close()

        max_dep_degree = max((m.get("degree", 0) for m in dep_metrics.values()), default=1)

        results: dict[str, dict[str, Any]] = {}
        for node_id in G.nodes:
            d = min(max(float(degree.get(node_id, 0.0)), 0.0), 1.0)
            b = min(max(float(betweenness.get(node_id, 0.0)), 0.0), 1.0)
            p = min(max(float(pagerank.get(node_id, 0.0)), 0.0), 1.0)

            # Normalised dependency reach (fallback to 0 if not present)
            dep = dep_metrics.get(node_id, {})
            raw_dep_deg = dep.get("degree", 0)
            dep_norm = (raw_dep_deg / max_dep_degree) if max_dep_degree else 0.0
            dep_norm = min(max(float(dep_norm), 0.0), 1.0)

            dependent_ids = dep.get("dependent_ids", [])
            dependent_systems = len(dependent_ids)

            blast = (
                self.weights["degree"] * d
                + self.weights["betweenness"] * b
                + self.weights["pagerank"] * p
                + self.weights["dependency"] * dep_norm
            )
            blast = min(max(float(blast), 0.0), 1.0)

            results[node_id] = {
                "degree_centrality": round(d, 6),
                "betweenness_centrality": round(b, 6),
                "pagerank_score": round(p, 6),
                "community_id": community_map.get(node_id),
                "blast_radius": round(blast, 6),
                "dependent_systems": dependent_systems,
                "dependent_ids": dependent_ids,
                # Preserve legacy naming for compatibility with existing pipeline
                "centrality_score": round(blast, 6),
            }
        return results

    # ---------------------------------------------------------------------
    # Write‑back to Neo4j
    # ---------------------------------------------------------------------
    def write_back(
        self,
        project_id: str,
        metrics: dict[str, dict[str, Any]],
        organization_id: str,
    ) -> None:
        """Persist calculated metrics as node properties in Neo4j via public API.

        Requires organization_id to ensure tenant isolation.
        The method is tolerant of failures – any exception is logged and the
        function returns without raising. Guarantees that the Neo4j store is
        reliably closed.
        """
        if not metrics or not organization_id:
            return
        store = create_graph_store()
        try:
            if not store.enabled:
                logger.info("Neo4j disabled – skipping metric write‑back")
                return
            store.update_asset_metrics(
                project_id=project_id,
                organization_id=organization_id,
                metrics=metrics,
            )
        except Exception as exc:  # defensive
            logger.exception("Failed to write NetworkX metrics back to Neo4j: %s", exc)
        finally:
            if hasattr(store, "close"):
                store.close()
