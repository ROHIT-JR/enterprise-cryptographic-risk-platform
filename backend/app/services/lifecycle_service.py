from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.asset import Asset
from backend.app.models.identity import User
from backend.app.models.lifecycle import CryptoLifecycleEvent
from backend.app.services.audit_service import record_audit
from lifecycle_engine import LifecycleEngine, TransitionRequest


class LifecycleService:
    def process_transition(
        self,
        db: Session,
        asset_id: str,
        organization_id: str,
        project_id: str,
        request: TransitionRequest,
        actor: User | None = None
    ) -> Asset:
        # Tenant Isolation enforcement
        asset = db.scalar(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.organization_id == organization_id,
                Asset.project_id == project_id
            )
        )
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Basic RBAC verification if actor exists
        if actor:
            if actor.role in ["viewer", "auditor"] and not request.is_automated:
                raise HTTPException(
                    status_code=403, detail="Role not authorized to transition lifecycle state"
                )

            if request.force_override and actor.role != "administrator":
                raise HTTPException(
                    status_code=403, detail="Only administrators can force transition overrides"
                )

        if request.force_override and not request.reason:
            raise ValueError("Admin override requires an explicit reason")

        # Validate through the engine
        result = LifecycleEngine.evaluate(
            current_state=asset.lifecycle_state,
            current_governance=asset.governance_status,
            request=request
        )

        if not result.success:
            raise ValueError(result.error)

        # Idempotency
        if result.was_idempotent:
            return asset

        # Apply changes
        previous_state = asset.lifecycle_state
        previous_governance = asset.governance_status
        
        asset.lifecycle_state = result.new_state.value
        asset.governance_status = result.new_governance_status.value
        asset.lifecycle_updated_at = datetime.now(UTC)
        
        # Determine engine_version or migration wave from metadata
        migration_wave = request.metadata.get("migration_wave")
        engine_version = request.metadata.get("optimizer_version")
        plan_id = request.metadata.get("migration_plan_id")
        
        # Persist immutable history
        event = CryptoLifecycleEvent(
            organization_id=organization_id,
            project_id=project_id,
            asset_id=asset.id,
            previous_state=previous_state,
            new_state=result.new_state.value,
            previous_governance_status=previous_governance,
            new_governance_status=result.new_governance_status.value,
            source=request.source,
            reason=request.reason,
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            related_plan_id=plan_id,
            migration_wave=migration_wave,
            engine_version=engine_version,
            metadata_json=request.metadata
        )
        db.add(event)
        
        # Audit Logging
        record_audit(
            db=db,
            action="crypto.lifecycle.transition",
            organization_id=organization_id,
            user=actor,
            metadata={
                "asset_id": asset.id,
                "from_state": previous_state,
                "to_state": result.new_state.value,
                "from_governance_status": previous_governance,
                "to_governance_status": result.new_governance_status.value,
                "reason": request.reason,
                "source": request.source,
                "migration_wave": migration_wave,
            }
        )
        
        db.flush()
        return asset
