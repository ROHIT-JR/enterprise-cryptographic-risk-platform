from fastapi import APIRouter, Depends, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Asset, AssetRelationship, Project, RiskFinding
from backend.app.schemas.graph import GraphEdgeResponse, GraphNodeResponse, GraphResponse
from backend.app.services.neo4j_service import create_graph_store

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def get_graph(
    project_id: str | None = None,
    limit: int = Query(500, ge=1, le=2_000),
    db: Session = Depends(get_db),
) -> GraphResponse:
    store = create_graph_store()
    try:
        if store.health():
            payload = store.query(project_id=project_id, limit=limit)
            return GraphResponse(**payload.model_dump())
    except (Neo4jError, ServiceUnavailable, OSError):
        pass
    finally:
        store.close()
    return _postgres_graph(db, project_id=project_id, limit=limit)


def _postgres_graph(db: Session, *, project_id: str | None, limit: int) -> GraphResponse:
    project_statement = select(Project)
    if project_id:
        project_statement = project_statement.where(Project.id == project_id)
    projects = list(db.scalars(project_statement.order_by(Project.name)))
    project_ids = [project.id for project in projects]
    if not project_ids:
        return GraphResponse(nodes=[], edges=[], source="postgresql")

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
    return GraphResponse(nodes=nodes, edges=edges, source="postgresql")
