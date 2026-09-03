from lifecycle_engine.engine import LifecycleEngine
from lifecycle_engine.models import TransitionRequest, LifecycleState, GovernanceStatus
from typing import Dict, Any

def run_lifecycle_validation(dataset: Any) -> Dict[str, Any]:

    # 1. Idempotency Check
    req_same = TransitionRequest(
        target_state=LifecycleState.DISCOVERED,
        target_governance_status=GovernanceStatus.ACTIVE,
        source="benchmark",
        is_automated=True
    )
    res_same = LifecycleEngine.evaluate(LifecycleState.DISCOVERED, GovernanceStatus.ACTIVE, req_same)

    # 2. Blocked Path: RECOMMENDED -> Blocked
    req_block = TransitionRequest(
        target_state=LifecycleState.RECOMMENDED,
        target_governance_status=GovernanceStatus.BLOCKED,
        source="benchmark",
        is_automated=True
    )
    res_block = LifecycleEngine.evaluate(LifecycleState.RECOMMENDED, GovernanceStatus.ACTIVE, req_block)

    # 3. Normal Path: RECOMMENDED -> MIGRATION_PLANNED
    req_plan = TransitionRequest(
        target_state=LifecycleState.MIGRATION_PLANNED,
        target_governance_status=GovernanceStatus.ACTIVE,
        source="benchmark",
        is_automated=True
    )
    res_plan = LifecycleEngine.evaluate(LifecycleState.RECOMMENDED, GovernanceStatus.ACTIVE, req_plan)

    return {
        "idempotency": {
            "was_idempotent": res_same.was_idempotent
        },
        "blocked_path": {
            "new_state": res_block.new_state,
            "new_governance": res_block.new_governance_status,
            "success": res_block.success
        },
        "normal_path": {
            "new_state": res_plan.new_state,
            "new_governance": res_plan.new_governance_status,
            "success": res_plan.success
        }
    }
