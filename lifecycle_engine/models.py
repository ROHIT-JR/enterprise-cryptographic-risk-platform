from enum import Enum
from pydantic import BaseModel
from typing import Any

class LifecycleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    ASSESSED = "ASSESSED"
    RECOMMENDED = "RECOMMENDED"
    MIGRATION_PLANNED = "MIGRATION_PLANNED"
    MIGRATING = "MIGRATING"
    REPLACED = "REPLACED"
    RETIRED = "RETIRED"

class GovernanceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    DEPRECATED = "DEPRECATED"

class TransitionRequest(BaseModel):
    target_state: LifecycleState | None = None
    target_governance_status: GovernanceStatus | None = None
    reason: str | None = None
    source: str
    metadata: dict[str, Any] = {}
    is_automated: bool = False
    actor_role: str | None = None
    force_override: bool = False

class TransitionResult(BaseModel):
    success: bool
    new_state: LifecycleState
    new_governance_status: GovernanceStatus
    error: str | None = None
    was_idempotent: bool = False
