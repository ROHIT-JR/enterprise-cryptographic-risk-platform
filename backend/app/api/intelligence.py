from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import Asset, BusinessContext, Project, RiskAnalysis, User
from backend.app.schemas.common import DistributionItem
from backend.app.schemas.graph import GraphEdgeResponse, GraphNodeResponse
from backend.app.schemas.intelligence import (
    BlastRadiusResponse,
    BusinessContextResponse,
    BusinessContextUpdate,
    HNDLResponse,
    IntelligenceItem,
    IntelligenceMetrics,
    IntelligenceRiskResponse,
)
from backend.app.services.audit_service import record_audit
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.neo4j_service import create_graph_store

router = APIRouter(prefix="/intelligence", tags=["phase-2 intelligence"])


def _item(analysis: RiskAnalysis, asset: Asset, project: Project) -> IntelligenceItem:
    return IntelligenceItem(
        asset_id=asset.id,
        asset_name=asset.name,
        asset_type=asset.asset_type,
        algorithm=asset.algorithm,
        project_id=project.id,
        project_name=project.name,
        quantum_score=analysis.quantum_score,
        quantum_classification=analysis.quantum_classification,
        hndl_score=analysis.hndl_score,
        hndl_risk=analysis.hndl_risk,
        centrality_score=analysis.centrality_score,
        dependent_systems=analysis.dependent_systems,
        business_score=analysis.business_score,
        migration_complexity_score=analysis.migration_complexity_score,
        evidence_confidence=analysis.evidence_confidence,
        evidence_sources=analysis.evidence_sources,
        final_score=analysis.final_score,
        severity=analysis.severity,
        explanations=analysis.explanations,
        factors=analysis.factors,
    )


def _rows(
    db: Session, project_id: str | None = None, organization_id: str | None = None
):
    statement = (
        select(RiskAnalysis, Asset, Project)
        .join(Asset, RiskAnalysis.asset_id == Asset.id)
        .join(Project, RiskAnalysis.project_id == Project.id)
    )
    if project_id:
        statement = statement.where(RiskAnalysis.project_id == project_id)
    if organization_id:
        statement = statement.where(RiskAnalysis.organization_id == organization_id)
    return db.execute(
        statement.order_by(RiskAnalysis.final_score.desc(), Asset.name)
    ).all()


@router.get("/risk", response_model=IntelligenceRiskResponse)
def get_intelligence_risk(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IntelligenceRiskResponse:
    organization_id = user.organization_id if isinstance(user, User) else None
    rows = _rows(db, project_id, organization_id)
    items = [_item(analysis, asset, project) for analysis, asset, project in rows]
    severities = Counter(item.severity for item in items)
    vulnerability = Counter(item.quantum_classification for item in items)
    return IntelligenceRiskResponse(
        metrics=IntelligenceMetrics(
            total_analyzed=len(items),
            vulnerable_assets=sum(item.quantum_score >= 50 for item in items),
            critical_quantum_risks=sum(
                item.quantum_classification == "critical" for item in items
            ),
            hndl_exposures=sum(item.hndl_risk in {"critical", "high"} for item in items),
            average_risk_score=round(
                sum(item.final_score for item in items) / max(len(items), 1), 1
            ),
        ),
        algorithm_vulnerability_distribution=[
            DistributionItem(name=name, value=count)
            for name, count in sorted(vulnerability.items())
        ],
        severity_distribution=[
            DistributionItem(name=name, value=severities.get(name, 0))
            for name in ("critical", "high", "medium", "low")
        ],
        items=items,
    )


@router.get("/hndl", response_model=HNDLResponse)
def get_hndl_analysis(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HNDLResponse:
    organization_id = user.organization_id if isinstance(user, User) else None
    items = [
        _item(analysis, asset, project)
        for analysis, asset, project in _rows(db, project_id, organization_id)
        if analysis.hndl_score > 0
    ]
    return HNDLResponse(total=len(items), items=items)


@router.get("/blast-radius", response_model=BlastRadiusResponse)
def get_blast_radius(
    asset_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlastRadiusResponse:
    statement = select(RiskAnalysis, Asset).join(Asset, RiskAnalysis.asset_id == Asset.id)
    if isinstance(user, User):
        statement = statement.where(RiskAnalysis.organization_id == user.organization_id)
    if asset_id:
        statement = statement.where(RiskAnalysis.asset_id == asset_id)
    elif project_id:
        statement = statement.where(RiskAnalysis.project_id == project_id)
    analysis_row = db.execute(
        statement.order_by(
            RiskAnalysis.dependent_systems.desc(),
            RiskAnalysis.final_score.desc(),
            Asset.name,
        ).limit(1)
    ).first()
    if not analysis_row:
        return BlastRadiusResponse(
            asset_id=None,
            asset_name=None,
            dependent_systems=0,
            centrality_score=0,
            nodes=[],
            edges=[],
        )
    analysis, asset = analysis_row
    dependent_ids = list(analysis.factors.get("dependent_ids", []))
    graph_store = create_graph_store()
    try:
        if graph_store.health():
            metrics = graph_store.dependency_metrics(project_id=asset.project_id).get(asset.id)
            if metrics:
                dependent_ids = metrics["dependent_ids"]
    except (Neo4jError, ServiceUnavailable, OSError):
        pass
    finally:
        graph_store.close()
    dependents = list(db.scalars(select(Asset).where(Asset.id.in_(dependent_ids))))
    nodes = [
        GraphNodeResponse(
            id=asset.id,
            label=asset.name,
            type=asset.asset_type,
            properties={
                "risk_score": analysis.final_score,
                "centrality_score": analysis.centrality_score,
            },
        ),
        *[
            GraphNodeResponse(
                id=dependent.id,
                label=dependent.name,
                type="application",
                properties={"location": dependent.location},
            )
            for dependent in dependents
        ],
    ]
    edges = [
        GraphEdgeResponse(
            id=f"{asset.id}:AFFECTS:{dependent.id}",
            source=asset.id,
            target=dependent.id,
            type="AFFECTS",
        )
        for dependent in dependents
    ]
    return BlastRadiusResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        dependent_systems=analysis.dependent_systems,
        centrality_score=analysis.centrality_score,
        nodes=nodes,
        edges=edges,
    )


@router.put(
    "/business-context/{asset_id}",
    response_model=BusinessContextResponse,
    dependencies=[Depends(require_permissions(Permission.ANALYZE_RISKS))],
)
def assign_business_context(
    asset_id: str,
    payload: BusinessContextUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BusinessContextResponse:
    asset = db.get(Asset, asset_id)
    if not asset or (
        isinstance(user, User) and asset.organization_id != user.organization_id
    ):
        raise HTTPException(status_code=404, detail="Asset not found")
    context = db.scalar(select(BusinessContext).where(BusinessContext.asset_id == asset_id))
    if context:
        for key, value in payload.model_dump().items():
            setattr(context, key, value)
    else:
        context = BusinessContext(asset_id=asset_id, **payload.model_dump())
        db.add(context)
    project = db.get(Project, asset.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.flush()
    IntelligenceService().analyze_project(db, project)
    record_audit(
        db,
        action="risk.business_context_updated",
        organization_id=asset.organization_id,
        user=user if isinstance(user, User) else None,
        metadata={"asset_id": asset.id, "criticality": payload.criticality},
    )
    db.commit()
    return BusinessContextResponse(asset_id=asset_id, **payload.model_dump())
