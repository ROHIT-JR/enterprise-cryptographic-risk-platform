from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import (
    Asset,
    AssetRelationship,
    BusinessContext,
    Project,
    RiskAnalysis,
    RiskFinding,
    User,
)
from backend.app.schemas.common import DistributionItem
from backend.app.schemas.graph import GraphEdgeResponse, GraphNodeResponse
from backend.app.schemas.intelligence import (
    BlastRadiusImpactSummary,
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
from risk_engine.crypto_agility import (
    AgilityAssetEvidence,
    CryptoAgilityAssessment,
    CryptoAgilityEngine,
    CryptoAgilityInput,
)

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
    depth: int = Query(
        default=1,
        ge=1,
        le=3,
        description="Blast radius hops to traverse beyond the direct (degree-1) dependents.",
    ),
) -> BlastRadiusResponse:
    if not isinstance(depth, int):
        depth = 1
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
            impact_summary=BlastRadiusImpactSummary(
                total_affected=0,
                by_degree={},
                critical_systems=0,
                estimated_effort_hours=0,
                critical_path=[],
            ),
        )
    analysis, asset = analysis_row
    dependent_ids = list(analysis.factors.get("dependent_ids", []))
    org_id = (
        user.organization_id
        if isinstance(user, User)
        else getattr(asset, "organization_id", None)
    )
    graph_store = create_graph_store()
    try:
        if graph_store.health():
            metrics = graph_store.dependency_metrics(
                project_id=asset.project_id,
                organization_id=org_id,
            ).get(asset.id)
            if metrics:
                dependent_ids = metrics["dependent_ids"]
    except (Neo4jError, ServiceUnavailable, OSError):
        pass
    finally:
        graph_store.close()
    if dependent_ids:
        dep_query = select(Asset).where(
            Asset.id.in_(dependent_ids),
            Asset.project_id == asset.project_id,
        )
        if org_id:
            dep_query = dep_query.where(Asset.organization_id == org_id)
        direct_dependents = list(db.scalars(dep_query))
    else:
        direct_dependents = []

    degree_by_id: dict[str, int] = {dependent.id: 1 for dependent in direct_dependents}
    parent_by_id: dict[str, str] = {dependent.id: asset.id for dependent in direct_dependents}
    assets_by_id: dict[str, Asset] = {dependent.id: dependent for dependent in direct_dependents}

    if depth > 1 and direct_dependents:
        # Undirected adjacency across the project, matching the Neo4j blast-radius
        # traversal semantics: a degree-N hop means "reachable within N relationship
        # edges", regardless of which side of USES/CONTAINS/DEPENDS_ON/PROTECTS the
        # asset sits on.
        rel_rows = db.execute(
            select(AssetRelationship.source_asset_id, AssetRelationship.target_asset_id).where(
                AssetRelationship.project_id == asset.project_id
            )
        ).all()
        adjacency: dict[str, set[str]] = defaultdict(set)
        for source_id, target_id in rel_rows:
            adjacency[source_id].add(target_id)
            adjacency[target_id].add(source_id)

        visited = {asset.id, *degree_by_id}
        current_frontier = list(degree_by_id)
        for level in range(2, depth + 1):
            next_frontier: list[str] = []
            for node_id in current_frontier:
                for neighbor_id in adjacency.get(node_id, ()):
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    degree_by_id[neighbor_id] = level
                    parent_by_id[neighbor_id] = node_id
                    next_frontier.append(neighbor_id)
            if not next_frontier:
                break
            extra_query = select(Asset).where(
                Asset.id.in_(next_frontier), Asset.project_id == asset.project_id
            )
            if org_id:
                extra_query = extra_query.where(Asset.organization_id == org_id)
            for extra_asset in db.scalars(extra_query):
                assets_by_id[extra_asset.id] = extra_asset
            current_frontier = next_frontier

    dependents = [assets_by_id[node_id] for node_id in degree_by_id if node_id in assets_by_id]

    severity_by_id = (
        {
            row.asset_id: row.severity
            for row in db.scalars(
                select(RiskFinding).where(RiskFinding.asset_id.in_(degree_by_id.keys()))
            )
        }
        if degree_by_id
        else {}
    )
    criticality_by_id = (
        {
            row.asset_id: row.criticality
            for row in db.scalars(
                select(BusinessContext).where(BusinessContext.asset_id.in_(degree_by_id.keys()))
            )
        }
        if degree_by_id
        else {}
    )

    nodes = [
        GraphNodeResponse(
            id=asset.id,
            label=asset.name,
            type=asset.asset_type,
            properties={
                "risk_score": analysis.final_score,
                "centrality_score": analysis.centrality_score,
                "degree": 0,
            },
        ),
        *[
            GraphNodeResponse(
                id=dependent.id,
                label=dependent.name,
                type=dependent.asset_type,
                properties={
                    "location": dependent.location,
                    "degree": degree_by_id.get(dependent.id, 1),
                    "severity": severity_by_id.get(dependent.id),
                    "criticality": criticality_by_id.get(dependent.id),
                },
            )
            for dependent in dependents
        ],
    ]
    edges = [
        GraphEdgeResponse(
            id=f"{parent_by_id.get(dependent.id, asset.id)}:AFFECTS:{dependent.id}",
            source=parent_by_id.get(dependent.id, asset.id),
            target=dependent.id,
            type="AFFECTS",
            properties={"degree": degree_by_id.get(dependent.id, 1)},
        )
        for dependent in dependents
    ]

    by_degree = Counter(degree_by_id.values())
    critical_systems = sum(
        1
        for node_id in degree_by_id
        if severity_by_id.get(node_id) in {"critical", "high"}
        or criticality_by_id.get(node_id) in {"critical", "high"}
    )
    # Heuristic: roughly 6 engineering hours to re-point trust, retest, and redeploy
    # each affected system once the shared cryptographic asset migrates.
    estimated_effort_hours = len(dependents) * 6
    critical_path: list[str] = []
    if degree_by_id:
        farthest_id = max(degree_by_id, key=lambda node_id: degree_by_id[node_id])
        chain: list[str] = []
        cursor: str | None = farthest_id
        while cursor is not None:
            node_asset = asset if cursor == asset.id else assets_by_id.get(cursor)
            if node_asset is None:
                break
            chain.append(node_asset.name)
            cursor = parent_by_id.get(cursor)
        critical_path = list(reversed(chain))

    return BlastRadiusResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        dependent_systems=analysis.dependent_systems,
        centrality_score=analysis.centrality_score,
        nodes=nodes,
        edges=edges,
        impact_summary=BlastRadiusImpactSummary(
            total_affected=len(dependents),
            by_degree={str(level): count for level, count in sorted(by_degree.items())},
            critical_systems=critical_systems,
            estimated_effort_hours=estimated_effort_hours,
            critical_path=critical_path,
        ),
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


@router.get("/agility", response_model=CryptoAgilityAssessment)
def get_crypto_agility_score(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CryptoAgilityAssessment:
    """Crypto-Agility Score: how easily this organization can swap algorithms.

    Computed from the same evidence lines and file locations the scanners
    already captured for algorithm, library, and protocol assets.
    """
    organization_id = user.organization_id if isinstance(user, User) else None
    statement = select(Asset)
    if organization_id:
        statement = statement.where(Asset.organization_id == organization_id)
    if project_id:
        statement = statement.where(Asset.project_id == project_id)
    assets = list(db.scalars(statement))

    algorithm_assets = [
        AgilityAssetEvidence(evidence=asset.evidence, location=asset.location)
        for asset in assets
        if asset.asset_type == "algorithm"
    ]
    library_names = [asset.name for asset in assets if asset.asset_type == "library"]
    protocol_names = [asset.name for asset in assets if asset.asset_type == "protocol"]

    return CryptoAgilityEngine().assess(
        CryptoAgilityInput(
            algorithm_assets=algorithm_assets,
            library_names=library_names,
            protocol_names=protocol_names,
        )
    )
