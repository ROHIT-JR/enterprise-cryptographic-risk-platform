from .models import LifecycleState, GovernanceStatus, TransitionRequest, TransitionResult
from .transitions import validate_transition

class LifecycleEngine:
    @staticmethod
    def evaluate(
        current_state: str,
        current_governance: str,
        request: TransitionRequest
    ) -> TransitionResult:
        try:
            cur_st = LifecycleState(current_state.upper())
        except ValueError:
            cur_st = LifecycleState.DISCOVERED
            
        try:
            cur_gov = GovernanceStatus(current_governance.upper())
        except ValueError:
            cur_gov = GovernanceStatus.ACTIVE
            
        return validate_transition(cur_st, cur_gov, request)
