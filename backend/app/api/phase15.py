from __future__ import annotations

from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.assets import list_assets
from backend.app.api.graph import get_graph
from backend.app.api.serializers import serialize_risk
from backend.app.api.upload import scan_repository
from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import Asset, Project, RiskFinding, Scan, User
from backend.app.schemas.asset import AssetPage
from backend.app.schemas.common import DistributionItem
from backend.app.schemas.graph import GraphResponse
from backend.app.schemas.risk import RiskSummaryResponse
from backend.app.schemas.scan import CBOMResponse, ScanResponse

router = APIRouter(prefix="/api", tags=["Compatibility"])


@router.post(
    "/upload/repository",
    response_model=ScanResponse,
    status_code=202,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
async def upload_repository(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(..., min_length=2, max_length=160),
    criticality: Literal["low", "medium", "high", "critical"] = Form("medium"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compatibility alias for the versioned repository discovery endpoint."""
    return await scan_repository(background_tasks, file, project_name, criticality, db, user)


@router.get("/assets", response_model=AssetPage)
def get_assets(
    project_id: str | None = None,
    asset_type: str | None = None,
    severity: str | None = None,
    search: str | None = Query(default=None, max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetPage:
    """Compatibility alias for `GET /api/v1/assets`. Prefer the versioned endpoint."""
    return list_assets(project_id, asset_type, severity, search, page, page_size, db, user)


@router.get("/cbom/{project_id}", response_model=CBOMResponse)
def get_project_cbom(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CBOMResponse:
    """Return the combined CBOM for every completed scan in a project.

    Compatibility endpoint; `GET /api/v1/scans/{scan_id}/cbom` returns the per-scan document.
    """
    project = db.get(Project, project_id)
    if not project or (
        isinstance(user, User) and project.organization_id != user.organization_id
    ):
        raise HTTPException(status_code=404, detail="Project not found")

    scan = db.scalar(
        select(Scan)
        .where(Scan.project_id == project_id, Scan.status == "completed")
        .order_by(Scan.completed_at.desc(), Scan.created_at.desc())
        .limit(1)
    )
    if not scan or not scan.cbom:
        raise HTTPException(
            status_code=409,
            detail="No completed CBOM is available for this project",
        )
    return CBOMResponse(scan_id=scan.id, document=scan.cbom)


@router.get("/risk", response_model=RiskSummaryResponse)
def get_risk_summary(
    project_id: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RiskSummaryResponse:
    """Compatibility alias for the risk summary. Prefer `GET /api/v1/risks`."""
    filters = [RiskFinding.project_id == project_id] if project_id else []
    if isinstance(user, User):
        filters.append(RiskFinding.organization_id == user.organization_id)
    total_statement = select(func.count(RiskFinding.id))
    distribution_statement = select(
        RiskFinding.severity, func.count(RiskFinding.id)
    ).group_by(RiskFinding.severity)
    risks_statement = (
        select(RiskFinding, Asset, Project)
        .join(Asset, RiskFinding.asset_id == Asset.id)
        .join(Project, RiskFinding.project_id == Project.id)
    )
    if filters:
        total_statement = total_statement.where(*filters)
        distribution_statement = distribution_statement.where(*filters)
        risks_statement = risks_statement.where(*filters)

    counts = dict(db.execute(distribution_statement).all())
    rows = db.execute(
        risks_statement.order_by(RiskFinding.score.desc(), RiskFinding.created_at.desc()).limit(
            limit
        )
    ).all()
    return RiskSummaryResponse(
        total=db.scalar(total_statement) or 0,
        severity_distribution=[
            DistributionItem(name=severity, value=counts.get(severity, 0))
            for severity in ("critical", "high", "medium", "low")
        ],
        highest_risks=[
            serialize_risk(risk, asset, project) for risk, asset, project in rows
        ],
    )


@router.get("/graph", response_model=GraphResponse)
def get_compatibility_graph(
    project_id: str | None = None,
    limit: int = Query(500, ge=1, le=2_000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GraphResponse:
    """Compatibility alias for `GET /api/v1/graph`. Prefer the versioned endpoint."""
    return get_graph(project_id, limit, db, user)
