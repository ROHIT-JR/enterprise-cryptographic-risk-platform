from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.api.serializers import serialize_asset
from backend.app.database import get_db
from backend.app.models import Asset, RiskFinding
from backend.app.schemas.asset import AssetPage, AssetResponse

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetPage)
def list_assets(
    project_id: str | None = None,
    asset_type: str | None = None,
    severity: str | None = None,
    search: str | None = Query(default=None, max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AssetPage:
    filters = []
    if project_id:
        filters.append(Asset.project_id == project_id)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Asset.name.ilike(term),
                Asset.algorithm.ilike(term),
                Asset.location.ilike(term),
                Asset.evidence.ilike(term),
            )
        )

    statement = select(Asset).options(joinedload(Asset.project), joinedload(Asset.risk))
    count_statement = select(func.count(Asset.id))
    if severity:
        statement = statement.join(RiskFinding).where(RiskFinding.severity == severity)
        count_statement = count_statement.join(RiskFinding).where(RiskFinding.severity == severity)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(Asset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    return AssetPage(
        items=[serialize_asset(asset) for asset in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, db: Session = Depends(get_db)) -> AssetResponse:
    asset = db.scalar(
        select(Asset)
        .where(Asset.id == asset_id)
        .options(joinedload(Asset.project), joinedload(Asset.risk))
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return serialize_asset(asset)
