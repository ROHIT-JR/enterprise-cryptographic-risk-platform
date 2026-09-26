import logging
from collections import Counter

import networkx as nx
from fastapi import APIRouter, Depends, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import Asset, AssetRelationship, Project, RiskFinding, User
from backend.app.schemas.graph import (
    GraphEdgeResponse,
    GraphNodeRef,
    GraphNodeResponse,
    GraphResponse,
    GraphStatsResponse,
)
from backend.app.services.neo4j_service import create_graph_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Discovery"])

_EMPTY_STATS = GraphStatsResponse(
    total_nodes=0,
    nodes_by_type={},
    total_edges=0,
    community_count=0,
    quantum_vulnerable_count=0,
    quantum_total_count=0,
)


def _compute_stats(
    nodes: list[GraphNodeResponse], edges: list[GraphEdgeResponse]
) -> GraphStatsResponse:
    """Degree, betweenness centrality, and community count via NetworkX,
    computed directly on whatever topology was actually returned (works for
    both the Neo4j and PostgreSQL data sources, unlike NetworkXGraphLayer
    which is Neo4j-only).
    """
    if not nodes:
        return _EMPTY_STATS

    labels_by_id = {node.id: node.label for node in nodes}
    graph = nx.Graph()
    graph.add_nodes_from(node.id for node in nodes)
    graph.add_edges_from(
        (edge.source, edge.target)
        for edge in edges
        if edge.source in labels_by_id and edge.target in labels_by_id
    )

    most_connected: GraphNodeRef | None = None
    most_connected_degree = 0
    if graph.number_of_edges() > 0:
        top_id, top_degree = max(graph.degree(), key=lambda pair: pair[1])
        if top_degree > 0:
            most_connected = GraphNodeRef(id=top_id, label=labels_by_id[top_id])
            most_connected_degree = top_degree

    top_centrality: GraphNodeRef | None = None
    top_centrality_score = 0.0
    community_count = 0
    if graph.number_of_nodes() > 1 and graph.number_of_edges() > 0:
        try:
            betweenness = nx.betweenness_centrality(graph)
            top_id = max(betweenness, key=lambda node_id: betweenness[node_id])
            if betweenness[top_id] > 0:
                top_centrality = GraphNodeRef(id=top_id, label=labels_by_id[top_id])
                top_centrality_score = round(betweenness[top_id], 4)
        except Exception:
            logger.exception(
                "Betweenness centrality failed for %s-node graph", graph.number_of_nodes()
            )
        try:
            from networkx.algorithms.community import louvain_communities

            community_count = len(list(louvain_communities(graph, seed=42)))
        except Exception:
            logger.debug("Louvain community detection unavailable or failed", exc_info=True)

    quantum_total = sum(1 for node in nodes if node.type == "algorithm")
    quantum_vulnerable = sum(
        1
        for node in nodes
        if node.type == "algorithm" and node.properties.get("risk_severity") in {"critical", "high"}
    )

    return GraphStatsResponse(
        total_nodes=len(nodes),
        nodes_by_type=dict(Counter(node.type for node in nodes)),
        total_edges=len(edges),
        most_connected=most_connected,
        most_connected_degree=most_connected_degree,
        top_centrality=top_centrality,
        top_centrality_score=top_centrality_score,
        community_count=community_count,
        quantum_vulnerable_count=quantum_vulnerable,
        quantum_total_count=quantum_total,
    )


@router.get("", response_model=GraphResponse)
def get_graph(
    project_id: str | None = None,
    limit: int = Query(500, ge=1, le=2_000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GraphResponse:
    """Return the cryptographic dependency graph as nodes and edges.

    Served from Neo4j when it is reachable and from PostgreSQL otherwise; the `source` field says
    which was used, so the graph stays available when Neo4j is down.
    """
    organization_id = user.organization_id if isinstance(user, User) else None
    if project_id and organization_id:
        owned = db.scalar(
            select(Project.id).where(
                Project.id == project_id, Project.organization_id == organization_id
            )
        )
        if not owned:
            return GraphResponse(nodes=[], edges=[], source="postgresql", stats=_EMPTY_STATS)
    store = create_graph_store()
    try:
        if store.health():
            payload = store.query(
                project_id=project_id, organization_id=organization_id, limit=limit
            )
            dumped = payload.model_dump()
            nodes = [GraphNodeResponse(**n) for n in dumped["nodes"]]
            edges = [GraphEdgeResponse(**e) for e in dumped["edges"]]
            return GraphResponse(
                nodes=nodes,
                edges=edges,
                source=dumped["source"],
                stats=_compute_stats(nodes, edges),
            )
    except (Neo4jError, ServiceUnavailable, OSError):
        pass
    finally:
        store.close()
    return _postgres_graph(
        db, project_id=project_id, organization_id=organization_id, limit=limit
    )


def _postgres_graph(
    db: Session,
    *,
    project_id: str | None,
    organization_id: str | None = None,
    limit: int,
) -> GraphResponse:
    project_statement = select(Project)
    if organization_id:
        project_statement = project_statement.where(Project.organization_id == organization_id)
    if project_id:
        project_statement = project_statement.where(Project.id == project_id)
    projects = list(db.scalars(project_statement.order_by(Project.name)))
    project_ids = [project.id for project in projects]
    if not project_ids:
        return GraphResponse(nodes=[], edges=[], source="postgresql", stats=_EMPTY_STATS)

    asset_rows = db.execute(
        select(Asset, RiskFinding)
        .outerjoin(RiskFinding, RiskFinding.asset_id == Asset.id)
        .where(Asset.project_id.in_(project_ids))
        .order_by(Asset.created_at.desc())
        .limit(limit)
    ).all()
    assets = [row[0] for row in asset_rows]
    risks = {row[0].id: row[1] for row in asset_rows if row[1]}
    asset_ids = {asset.id for asset in assets}

    nodes = [
        GraphNodeResponse(
            id=f"project:{project.id}",
            label=project.name,
            type="project",
            properties={"criticality": project.criticality},
        )
        for project in projects
    ]
    nodes.extend(
        GraphNodeResponse(
            id=asset.id,
            label=asset.name,
            type=asset.asset_type,
            properties={
                "algorithm": asset.algorithm,
                "version": asset.version,
                "location": asset.location,
                "risk_score": risks[asset.id].score if asset.id in risks else None,
                "risk_severity": risks[asset.id].severity if asset.id in risks else None,
            },
        )
        for asset in assets
    )
    edges = [
        GraphEdgeResponse(
            id=f"project:{asset.project_id}:CONTAINS:{asset.id}",
            source=f"project:{asset.project_id}",
            target=asset.id,
            type="CONTAINS",
        )
        for asset in assets
    ]
    if asset_ids:
        relationships = db.scalars(
            select(AssetRelationship).where(
                AssetRelationship.source_asset_id.in_(asset_ids),
                AssetRelationship.target_asset_id.in_(asset_ids),
            )
        )
        edges.extend(
            GraphEdgeResponse(
                id=relationship.id,
                source=relationship.source_asset_id,
                target=relationship.target_asset_id,
                type=relationship.relationship_type,
                properties={"evidence": relationship.evidence},
            )
            for relationship in relationships
        )
    return GraphResponse(
        nodes=nodes, edges=edges, source="postgresql", stats=_compute_stats(nodes, edges)
    )
