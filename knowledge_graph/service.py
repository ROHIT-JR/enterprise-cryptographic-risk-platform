from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from knowledge_graph.models import GraphEdge, GraphNode, GraphPayload

logger = logging.getLogger(__name__)

LABELS = {
    "application": "Application",
    "library": "Library",
    "algorithm": "Algorithm",
    "certificate": "Certificate",
    "protocol": "Protocol",
    "configuration": "Configuration",
}
RELATIONSHIPS = {"USES", "CONTAINS", "DEPENDS_ON", "PROTECTS"}
ALLOWED_METRIC_PROPERTIES = {
    "degree_centrality": "degreeCentrality",
    "betweenness_centrality": "betweennessCentrality",
    "pagerank_score": "pageRankScore",
    "community_id": "communityId",
    "blast_radius": "blastRadius",
    "centrality_score": "centralityScore",
}


class Neo4jGraphStore:
    """Optional Neo4j projection of the authoritative PostgreSQL inventory."""

    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled and bool(password)
        self._driver = (
            GraphDatabase.driver(uri, auth=(user, password), connection_timeout=3)
            if self.enabled
            else None
        )

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def __enter__(self) -> Neo4jGraphStore:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def health(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except (ServiceUnavailable, Neo4jError, OSError):
            return False

    def ensure_schema(self) -> None:
        if not self._driver:
            return
        statements = (
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (n:Project) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT scan_id IF NOT EXISTS FOR (n:Scan) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (n:Asset) REQUIRE n.id IS UNIQUE",
        )
        with self._driver.session() as session:
            for statement in statements:
                session.run(statement).consume()

    def sync_scan(
        self,
        *,
        project: Mapping[str, Any],
        scan: Mapping[str, Any],
        assets: Iterable[Mapping[str, Any]],
        relationships: Iterable[Mapping[str, Any]],
    ) -> None:
        if not self._driver:
            return
        self.ensure_schema()
        with self._driver.session() as session:
            session.execute_write(self._write_project_and_scan, dict(project), dict(scan))
            for asset in assets:
                session.execute_write(
                    self._write_asset, dict(asset), str(project["id"]), str(scan["id"])
                )
            for relationship in relationships:
                session.execute_write(self._write_relationship, dict(relationship))

    @staticmethod
    def _write_project_and_scan(tx: Any, project: dict[str, Any], scan: dict[str, Any]) -> None:
        tx.run(
            """
            MERGE (p:Project {id: $project_id})
            SET p.name = $project_name, p.criticality = $criticality
            SET p.organization_id = $organization_id
            MERGE (s:Scan {id: $scan_id})
            SET s.source_type = $source_type, s.target = $target, s.status = $status
            MERGE (p)-[:CONTAINS]->(s)
            """,
            project_id=str(project["id"]),
            project_name=project["name"],
            criticality=project.get("criticality", "medium"),
            organization_id=project.get("organization_id"),
            scan_id=str(scan["id"]),
            source_type=scan.get("source_type"),
            target=scan.get("target"),
            status=scan.get("status"),
        ).consume()

    @staticmethod
    def _write_asset(tx: Any, asset: dict[str, Any], project_id: str, scan_id: str) -> None:
        label = LABELS.get(str(asset.get("asset_type")), "CryptoAsset")
        query = f"""
            MATCH (p:Project {{id: $project_id}}), (s:Scan {{id: $scan_id}})
            MERGE (a:Asset:{label} {{id: $asset_id}})
            SET a.name = $name,
                a.asset_type = $asset_type,
                a.algorithm = $algorithm,
                a.version = $version,
                a.location = $location,
                a.risk_score = $risk_score,
                a.risk_severity = $risk_severity
            MERGE (p)-[:CONTAINS]->(a)
            MERGE (s)-[:DISCOVERED]->(a)
        """
        tx.run(
            query,
            project_id=project_id,
            scan_id=scan_id,
            asset_id=str(asset["id"]),
            name=asset["name"],
            asset_type=asset.get("asset_type"),
            algorithm=asset.get("algorithm"),
            version=asset.get("version"),
            location=asset.get("location"),
            risk_score=asset.get("risk_score"),
            risk_severity=asset.get("risk_severity"),
        ).consume()

    @staticmethod
    def _write_relationship(tx: Any, relationship: dict[str, Any]) -> None:
        relationship_type = str(relationship.get("relationship_type", "DEPENDS_ON")).upper()
        if relationship_type not in RELATIONSHIPS:
            relationship_type = "DEPENDS_ON"
        query = f"""
            MATCH (source:Asset {{id: $source_id}}), (target:Asset {{id: $target_id}})
            MERGE (source)-[r:{relationship_type}]->(target)
            SET r.evidence = $evidence
        """
        tx.run(
            query,
            source_id=str(relationship["source_asset_id"]),
            target_id=str(relationship["target_asset_id"]),
            evidence=relationship.get("evidence"),
        ).consume()

    def query(
        self,
        *,
        project_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 500,
    ) -> GraphPayload:
        if not self._driver:
            raise ServiceUnavailable("Neo4j is not configured")
        node_limit = max(1, min(limit, 2_000))
        query = """
            MATCH (p:Project)
            WHERE ($project_id IS NULL OR p.id = $project_id)
              AND ($organization_id IS NULL OR p.organization_id = $organization_id)
            MATCH (p)-[:CONTAINS]->(a:Asset)
            WITH p, collect(DISTINCT a)[..$limit] AS assets
            UNWIND assets AS a
            OPTIONAL MATCH (a)-[r:USES|CONTAINS|DEPENDS_ON|PROTECTS]->(b:Asset)
            WHERE b IN assets
            RETURN p, a, r, b
        """
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        with self._driver.session() as session:
            for record in session.run(
                query,
                project_id=project_id,
                organization_id=organization_id,
                limit=node_limit,
            ):
                project = record["p"]
                asset = record["a"]
                project_key = f"project:{project['id']}"
                nodes[project_key] = GraphNode(
                    id=project_key,
                    label=project.get("name", "Project"),
                    type="project",
                    properties=dict(project),
                )
                asset_key = str(asset["id"])
                nodes[asset_key] = GraphNode(
                    id=asset_key,
                    label=asset.get("name", "Asset"),
                    type=asset.get("asset_type", "asset"),
                    properties=dict(asset),
                )
                contains_key = f"{project_key}:CONTAINS:{asset_key}"
                edges[contains_key] = GraphEdge(
                    id=contains_key,
                    source=project_key,
                    target=asset_key,
                    type="CONTAINS",
                )
                relationship, target = record["r"], record["b"]
                if relationship is not None and target is not None:
                    target_key = str(target["id"])
                    nodes[target_key] = GraphNode(
                        id=target_key,
                        label=target.get("name", "Asset"),
                        type=target.get("asset_type", "asset"),
                        properties=dict(target),
                    )
                    edge_key = f"{asset_key}:{relationship.type}:{target_key}"
                    edges[edge_key] = GraphEdge(
                        id=edge_key,
                        source=asset_key,
                        target=target_key,
                        type=relationship.type,
                        properties=dict(relationship),
                    )
        return GraphPayload(nodes=list(nodes.values()), edges=list(edges.values()), source="neo4j")

    def dependency_metrics(
        self, *, project_id: str, organization_id: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Return Neo4j-backed degree and application blast-radius metrics by asset."""
        if not self._driver:
            raise ServiceUnavailable("Neo4j is not configured")
        query = """
            MATCH (p:Project {id: $project_id})
            WHERE ($organization_id IS NULL OR p.organization_id = $organization_id)
            MATCH (p)-[:CONTAINS]->(a:Asset)
            OPTIONAL MATCH (a)-[]-(neighbor:Asset)
            WITH p, a, count(DISTINCT neighbor) AS degree
            OPTIONAL MATCH path =
                (a)-[:USES|CONTAINS|DEPENDS_ON|PROTECTS*1..4]-(application:Asset:Application)
            WHERE all(node IN nodes(path) WHERE node:Asset)
              AND EXISTS { MATCH (p)-[:CONTAINS]->(application) }
            RETURN a.id AS asset_id,
                   degree,
                   collect(DISTINCT application.id) AS dependent_ids
        """
        metrics: dict[str, dict[str, Any]] = {}
        with self._driver.session() as session:
            for record in session.run(
                query, project_id=project_id, organization_id=organization_id
            ):
                metrics[str(record["asset_id"])] = {
                    "degree": int(record["degree"] or 0),
                    "dependent_ids": [str(item) for item in record["dependent_ids"] if item],
                }
        return metrics

    def update_asset_metrics(
        self,
        *,
        project_id: str,
        organization_id: str,
        metrics: Mapping[str, Mapping[str, Any]],
    ) -> None:
        """Safely write computed graph metrics back to Neo4j nodes.

        Requires both project_id and organization_id to enforce tenant isolation.
        Parameterizes all values and writes only whitelisted metric properties.
        """
        if not self._driver:
            raise ServiceUnavailable("Neo4j is not configured")
        if not organization_id:
            raise ValueError("organization_id is required for tenant isolation")
        if not metrics:
            return

        updates = []
        for asset_id, data in metrics.items():
            props: dict[str, Any] = {}
            for metric_key, prop_name in ALLOWED_METRIC_PROPERTIES.items():
                if (val := data.get(metric_key)) is not None:
                    props[prop_name] = val
            if props:
                updates.append({"asset_id": str(asset_id), "properties": props})

        if not updates:
            return

        query = """
            UNWIND $updates AS u
            MATCH (p:Project {id: $project_id, organization_id: $organization_id})
            MATCH (p)-[:CONTAINS]->(a:Asset {id: u.asset_id})
            SET a += u.properties
        """
        with self._driver.session() as session:
            session.run(
                query,
                project_id=project_id,
                organization_id=organization_id,
                updates=updates,
            ).consume()
