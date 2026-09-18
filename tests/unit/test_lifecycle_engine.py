from pathlib import Path

from lifecycle_engine.engine import LifecycleEngine
from lifecycle_engine.models import GovernanceStatus, LifecycleState, TransitionRequest


def test_lifecycle_engine_is_packaged_for_docker():
    dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "COPY lifecycle_engine /app/lifecycle_engine" in dockerfile
    assert "./lifecycle_engine:/app/lifecycle_engine" in compose


def test_default_state_initialization():
    req = TransitionRequest(
        target_state=LifecycleState.ASSESSED,
        source="system",
        is_automated=True,
    )
    # The database initializes assets as DISCOVERED + ACTIVE.
    res = LifecycleEngine.evaluate("DISCOVERED", "ACTIVE", req)
    assert res.success
    assert res.new_state == LifecycleState.ASSESSED
    assert res.new_governance_status == GovernanceStatus.ACTIVE


def test_invalid_automated_transition():
    req = TransitionRequest(
        target_state=LifecycleState.MIGRATING,
        source="system",
        is_automated=True,
    )
    res = LifecycleEngine.evaluate(LifecycleState.MIGRATION_PLANNED, GovernanceStatus.ACTIVE, req)
    assert not res.success
    assert "Automated pipelines cannot transition to MIGRATING" in res.error


def test_manual_transition_authorization():
    req = TransitionRequest(
        target_state=LifecycleState.MIGRATING,
        source="user",
        is_automated=False,
    )
    res = LifecycleEngine.evaluate(LifecycleState.MIGRATION_PLANNED, GovernanceStatus.ACTIVE, req)
    # The engine evaluates state graph validity. Service layer evaluates RBAC.
    assert res.success
    assert res.new_state == LifecycleState.MIGRATING


def test_administrator_force_override():
    req = TransitionRequest(
        target_state=LifecycleState.RETIRED,
        source="user",
        is_automated=False,
        force_override=True,
        actor_role="administrator",
    )
    res = LifecycleEngine.evaluate(LifecycleState.DISCOVERED, GovernanceStatus.ACTIVE, req)
    assert res.success
    assert res.new_state == LifecycleState.RETIRED


def test_force_override_denied_for_non_admin():
    req = TransitionRequest(
        target_state=LifecycleState.RETIRED,
        source="user",
        is_automated=False,
        force_override=True,
        actor_role="security_analyst",
    )
    res = LifecycleEngine.evaluate(LifecycleState.DISCOVERED, GovernanceStatus.ACTIVE, req)
    assert not res.success
    assert "Only administrators can force override" in res.error


def test_idempotent_repeated_transition():
    req = TransitionRequest(
        target_state=LifecycleState.ASSESSED,
        target_governance_status=GovernanceStatus.ACTIVE,
        source="system",
        is_automated=True,
    )
    res = LifecycleEngine.evaluate(LifecycleState.ASSESSED, GovernanceStatus.ACTIVE, req)
    assert res.success
    assert res.was_idempotent


def test_blocked_governance_status():
    req = TransitionRequest(
        target_state=LifecycleState.RECOMMENDED,
        target_governance_status=GovernanceStatus.BLOCKED,
        source="optimizer",
        is_automated=True,
    )
    res = LifecycleEngine.evaluate(LifecycleState.RECOMMENDED, GovernanceStatus.ACTIVE, req)
    assert res.success
    assert res.new_state == LifecycleState.RECOMMENDED
    assert res.new_governance_status == GovernanceStatus.BLOCKED


def test_deferred_status():
    req = TransitionRequest(
        target_governance_status=GovernanceStatus.DEFERRED,
        source="user",
        is_automated=False,
    )
    res = LifecycleEngine.evaluate(LifecycleState.RECOMMENDED, GovernanceStatus.ACTIVE, req)
    assert res.success
    assert res.new_governance_status == GovernanceStatus.DEFERRED
    assert res.new_state == LifecycleState.RECOMMENDED


def test_valid_m4_wave_to_migration_planned():
    req = TransitionRequest(
        target_state=LifecycleState.MIGRATION_PLANNED,
        source="optimizer",
        is_automated=True,
    )
    res = LifecycleEngine.evaluate(LifecycleState.RECOMMENDED, GovernanceStatus.ACTIVE, req)
    assert res.success
    assert res.new_state == LifecycleState.MIGRATION_PLANNED


def test_migration_planned_to_migrating():
    req = TransitionRequest(target_state=LifecycleState.MIGRATING, source="user")
    res = LifecycleEngine.evaluate(LifecycleState.MIGRATION_PLANNED, GovernanceStatus.ACTIVE, req)
    assert res.success


def test_migrating_to_replaced():
    req = TransitionRequest(target_state=LifecycleState.REPLACED, source="user")
    res = LifecycleEngine.evaluate(LifecycleState.MIGRATING, GovernanceStatus.ACTIVE, req)
    assert res.success


def test_replaced_to_retired():
    req = TransitionRequest(target_state=LifecycleState.RETIRED, source="user")
    res = LifecycleEngine.evaluate(LifecycleState.REPLACED, GovernanceStatus.ACTIVE, req)
    assert res.success
