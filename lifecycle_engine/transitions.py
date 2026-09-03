from .models import LifecycleState, GovernanceStatus, TransitionRequest, TransitionResult

# Defined valid transitions
VALID_STATE_TRANSITIONS = {
    LifecycleState.DISCOVERED: {LifecycleState.ASSESSED},
    LifecycleState.ASSESSED: {LifecycleState.RECOMMENDED},
    LifecycleState.RECOMMENDED: {LifecycleState.MIGRATION_PLANNED},
    LifecycleState.MIGRATION_PLANNED: {LifecycleState.MIGRATING},
    LifecycleState.MIGRATING: {LifecycleState.REPLACED},
    LifecycleState.REPLACED: {LifecycleState.RETIRED},
    LifecycleState.RETIRED: set(),
}

# The automated pipeline only allows these forward transitions
AUTOMATED_ALLOWED_TRANSITIONS = {
    (LifecycleState.DISCOVERED, LifecycleState.ASSESSED),
    (LifecycleState.ASSESSED, LifecycleState.RECOMMENDED),
    (LifecycleState.RECOMMENDED, LifecycleState.MIGRATION_PLANNED),
}

def validate_transition(
    current_state: LifecycleState,
    current_governance: GovernanceStatus,
    request: TransitionRequest
) -> TransitionResult:
    target_state = request.target_state or current_state
    target_governance = request.target_governance_status or current_governance
    
    # Check for idempotency
    if target_state == current_state and target_governance == current_governance:
        return TransitionResult(
            success=True,
            new_state=current_state,
            new_governance_status=current_governance,
            was_idempotent=True
        )

    if target_state != current_state:
        # Check if valid jump
        if target_state not in VALID_STATE_TRANSITIONS.get(current_state, set()):
            if not request.force_override:
                return TransitionResult(
                    success=False,
                    new_state=current_state,
                    new_governance_status=current_governance,
                    error=f"Invalid transition from {current_state.value} to {target_state.value}"
                )
            # If force_override is True, we allow invalid jumps (must be administrator)
            if request.actor_role != "administrator":
                return TransitionResult(
                    success=False,
                    new_state=current_state,
                    new_governance_status=current_governance,
                    error="Only administrators can force override transitions."
                )

        # Check automated restrictions
        if request.is_automated:
            if (current_state, target_state) not in AUTOMATED_ALLOWED_TRANSITIONS:
                return TransitionResult(
                    success=False,
                    new_state=current_state,
                    new_governance_status=current_governance,
                    error=f"Automated pipelines cannot transition to {target_state.value}"
                )

    # All checks passed
    return TransitionResult(
        success=True,
        new_state=target_state,
        new_governance_status=target_governance
    )
