from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.api.serializers import serialize_asset
from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import Asset, RiskFinding, User
from backend.app.schemas.asset import AssetPage, AssetResponse

router = APIRouter(prefix="/assets", tags=["Discovery"])


@router.get("", response_model=AssetPage)
def list_assets(
    project_id: str | None = None,
    asset_type: str | None = None,
    severity: str | None = None,
    search: str | None = Query(default=None, max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetPage:
    """List discovered cryptographic assets, newest first.

    Filter by project, asset type or risk severity, and search `search` across asset name,
    algorithm, location and evidence. Results are paginated and scoped to the caller's organization.
    """
    filters = []
    if isinstance(user, User):
        filters.append(Asset.organization_id == user.organization_id)
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
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetResponse:
    """Return one asset with its project context and current risk finding."""
    asset = db.scalar(
        select(Asset)
        .where(Asset.id == asset_id)
        .options(joinedload(Asset.project), joinedload(Asset.risk))
    )
    if not asset or (isinstance(user, User) and asset.organization_id != user.organization_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return serialize_asset(asset)


class LifecycleTransitionBody(BaseModel):
    target_state: str | None = None
    target_governance_status: str | None = None
    reason: str | None = None
    force_override: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"target_state": "MIGRATION_PLANNED", "reason": "Approved in CR-1042"}]
        }
    )


@router.get(
    "/{asset_id}/lifecycle",
    responses={404: {"description": "No such asset in this organization."}},
)
def get_lifecycle(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return an asset's lifecycle state, governance status and full transition history.

    History is newest first and records who changed what, why, and whether the change was automated.
    """
    asset = db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.organization_id == user.organization_id)
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get history
    from backend.app.models.lifecycle import CryptoLifecycleEvent

    events = list(
        db.scalars(
            select(CryptoLifecycleEvent)
            .where(CryptoLifecycleEvent.asset_id == asset_id)
            .order_by(CryptoLifecycleEvent.created_at.desc())
        )
    )

    return {
        "lifecycle_state": asset.lifecycle_state,
        "governance_status": asset.governance_status,
        "lifecycle_updated_at": asset.lifecycle_updated_at,
        "history": [
            {
                "id": e.id,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "previous_governance_status": e.previous_governance_status,
                "new_governance_status": e.new_governance_status,
                "source": e.source,
                "reason": e.reason,
                "actor_role": e.actor_role,
                "migration_wave": e.migration_wave,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


@router.post(
    "/{asset_id}/lifecycle/transition",
    # Checked in LifecycleService rather than by a permission dependency, so it is declared here
    # for the docs; tests/test_api_docs.py proves it matches the real behaviour.
    openapi_extra={"x-minimum-role": "security_analyst"},
    responses={
        400: {
            "description": "Unknown state or status name, or a transition the state machine "
            "does not allow (for example skipping a state without `force_override`).",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid transition from DISCOVERED to RETIRED"}
                }
            },
        },
        403: {
            "description": "Viewers and auditors are read-only, and only administrators may "
            "use `force_override`.",
            "content": {
                "application/json": {
                    "example": {"detail": "Role not authorized to transition lifecycle state"}
                }
            },
        },
        404: {"description": "No such asset in this organization."},
    },
)
def transition_lifecycle(
    asset_id: str,
    body: LifecycleTransitionBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move an asset to a new lifecycle state or governance status.

    Lifecycle states are `DISCOVERED`, `ASSESSED`, `RECOMMENDED`, `MIGRATION_PLANNED`,
    `MIGRATING`, `REPLACED` and `RETIRED`; governance statuses are `ACTIVE`, `BLOCKED`,
    `DEFERRED` and `DEPRECATED`. Send either or both. Every change is validated against the
    state machine and recorded in the asset's history.

    Requires the `security_analyst` role or higher (`viewer` and `auditor` get `403`). A jump the
    state machine forbids is rejected with `400` unless `force_override` is set, which needs the
    `administrator` role and a `reason`.
    """
    asset = db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.organization_id == user.organization_id)
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    from backend.app.services.lifecycle_service import LifecycleService
    from lifecycle_engine import GovernanceStatus, LifecycleState, TransitionRequest

    svc = LifecycleService()
    try:
        t_state = LifecycleState(body.target_state.upper()) if body.target_state else None
        t_gov = (
            GovernanceStatus(body.target_governance_status.upper())
            if body.target_governance_status
            else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid state or status value") from exc

    try:
        asset = svc.process_transition(
            db=db,
            asset_id=asset_id,
            organization_id=asset.organization_id,
            project_id=asset.project_id,
            request=TransitionRequest(
                target_state=t_state,
                target_governance_status=t_gov,
                reason=body.reason,
                source="API",
                is_automated=False,
                actor_role=user.role,
                force_override=body.force_override,
            ),
            actor=user,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "lifecycle_state": asset.lifecycle_state,
        "governance_status": asset.governance_status,
        "lifecycle_updated_at": asset.lifecycle_updated_at,
    }
