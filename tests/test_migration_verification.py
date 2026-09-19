import copy
import secrets

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.service import AuthenticationService
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.schemas.auth import LoginRequest, RegisterRequest
from backend.app.seed import seed_securebank_demo
from benchmarks import pqc_benchmarks
from migration_engine.verification import (
    CHECK_IDS,
    MigrationVerifier,
    PlanView,
    TestResult,
    load_policy,
    summarize,
)

KEM_STRATEGY = "X25519 + ML-KEM-768"


@pytest.fixture
def verifier():
    return MigrationVerifier()


def plan(recommended: str, current: str = "RSA-2048", **overrides) -> PlanView:
    values = {
        "asset_id": "asset-1",
        "asset_name": "payments-gateway",
        "asset_type": "algorithm",
        "wave": 2,
        "current_algorithm": current,
        "recommended_algorithm": recommended,
        "constraints": [],
        "recommendation": {
            "hybrid_strategy": f"Classical + {recommended} hybrid during transition",
            "detected_functions": [],
        },
    }
    values.update(overrides)
    return PlanView(**values)


def checks_by_id(item):
    return {check.id: check for check in item.checks}


# --- checklist --------------------------------------------------------------------------
def test_ml_kem_768_is_fully_verified_with_evidence(verifier):
    item = verifier.verify(plan("ML-KEM-768", "ECDH-P256"))
    checks = checks_by_id(item)

    assert [check.id for check in item.checks] == list(CHECK_IDS)
    assert {check.status for check in item.checks} == {"pass"}
    assert item.overall == "verified"
    assert item.target_kind == "algorithm"
    assert "FIPS 203" in checks["algorithm_compatibility"].evidence[0]
    # sizes come from the knowledge base: 1184 + 1088 = 2272 bytes
    assert "2,272 B" in checks["key_size"].evidence[0]
    assert "keygen 29 µs" in checks["performance_threshold"].evidence[0]
    assert checks["rollback_plan"].basis == "generated"
    assert len(item.rollback_plan) >= 3


def test_slh_dsa_fails_performance_and_suggests_an_alternative(verifier):
    """SLH-DSA-SHA2-128f signing is orders of magnitude over the per-operation budget."""
    item = verifier.verify(plan("ML-KEM-512 + SLH-DSA-SHA2-128f", "ECC P-256"))
    checks = checks_by_id(item)

    assert checks["performance_threshold"].status == "fail"
    assert any("ML-DSA-65" in line for line in checks["performance_threshold"].evidence)
    # the 17 KB signature also busts the size budget (but that is a warning, not a blocker)
    assert checks["key_size"].status == "warn"
    assert "17,120 B" in " ".join(checks["key_size"].evidence)
    assert item.overall == "blocked"


def test_algorithm_without_benchmark_data_is_pending_not_passed(verifier):
    item = verifier.verify(plan("ML-DSA-44"))  # in the knowledge base, not in the benchmark set
    checks = checks_by_id(item)

    assert checks["algorithm_compatibility"].status == "pass"
    assert checks["performance_threshold"].status == "pending"
    assert "no benchmark data" in checks["performance_threshold"].evidence[0]
    assert item.overall == "pending"
    not_measured = [r for r in item.test_results if r.basis == "benchmark"]
    assert [r.status for r in not_measured] == ["pending"]


def test_application_upgrades_are_pending_and_use_dual_stack_steps(verifier):
    item = verifier.verify(
        plan(
            "PQC-capable hybrid integration",
            "Dependent application integration",
            asset_name="Customer Database",
            asset_type="application",
            recommendation={
                "hybrid_strategy": "Dual-stack classical and PQC client support",
                "metrics": {"compatibility": "requires integration testing"},
            },
        )
    )
    checks = checks_by_id(item)

    assert item.target_kind == "integration"
    assert [checks[c].status for c in CHECK_IDS] == [
        "pending",
        "pending",
        "pending",
        "pass",
        "pass",
    ]
    assert "requires integration testing" in " ".join(checks["algorithm_compatibility"].evidence)
    assert item.overall == "pending"
    assert (
        item.hybrid_steps[0].title
        == "Upgrade Customer Database to a PQC-capable release (dual-stack)"
    )
    assert item.hybrid_steps[2].title == "Retire classical-only mode in Customer Database"


def test_constraints_and_missing_hybrid_strategy_downgrade_backward_compatibility(verifier):
    constrained = verifier.verify(plan("ML-KEM-768", constraints=["legacy compatibility"]))
    assert checks_by_id(constrained)["backward_compatibility"].status == "warn"
    assert (
        "legacy compatibility" in checks_by_id(constrained)["backward_compatibility"].evidence[-1]
    )
    assert constrained.overall == "conditional"

    bare = verifier.verify(plan("ML-KEM-768", recommendation={}))
    assert checks_by_id(bare)["backward_compatibility"].status == "warn"


def test_undetected_function_left_uncovered_is_flagged(verifier):
    item = verifier.verify(
        plan(
            "ML-KEM-768",
            recommendation={
                "hybrid_strategy": KEM_STRATEGY,
                "detected_functions": ["key_establishment", "digital_signature"],
            },
        )
    )
    compatibility = checks_by_id(item)["algorithm_compatibility"]
    assert compatibility.status == "warn"
    assert "digital_signature" in compatibility.evidence[-1]


def test_thresholds_come_from_policy_not_code(verifier):
    strict = copy.deepcopy(load_policy())
    strict["thresholds"]["max_operation_us"] = 10  # ML-KEM-768 needs 36-40 µs
    item = MigrationVerifier(policy=strict).verify(plan("ML-KEM-768", "ECDH-P256"))

    assert checks_by_id(item)["performance_threshold"].status == "fail"
    assert item.overall == "blocked"
    operations = next(r for r in item.test_results if r.id == "ML-KEM-768:operations")
    assert (operations.status, operations.threshold) == ("fail", "≤ 10 µs each")


# --- hybrid path -------------------------------------------------------------------------
def test_hybrid_steps_follow_the_issue_wording(verifier):
    item = verifier.verify(plan("ML-KEM-768", "RSA-2048"))
    days = load_policy()["hybrid_schedule_days"]

    assert [step.step for step in item.hybrid_steps] == [1, 2, 3]
    assert item.hybrid_steps[0].title == "Add ML-KEM-768 alongside RSA-2048 (hybrid mode)"
    assert item.hybrid_steps[1].title == "Test hybrid for 30 days"
    assert item.hybrid_steps[2].title == "Remove RSA-2048 (PQC-only mode)"
    assert [step.duration_days for step in item.hybrid_steps] == [
        days["deploy"],
        days["soak"],
        days["cutover"],
    ]
    assert all(step.exit_criteria for step in item.hybrid_steps)


def test_trust_anchor_rollback_keeps_previous_keys(verifier):
    first_wave = verifier.verify(plan("ML-KEM-768", wave=1))
    later = verifier.verify(plan("ML-KEM-768", wave=2))
    assert any("archived" in step for step in first_wave.rollback_plan)
    assert not any("archived" in step for step in later.rollback_plan)


# --- test results ------------------------------------------------------------------------
def test_benchmark_results_match_the_issue_example(verifier):
    item = verifier.verify(plan("ML-KEM-768", "ECDH-P256"))
    by_id = {r.id: r for r in item.test_results}

    keygen = by_id["ML-KEM-768:keygen"]
    assert (keygen.measured, keygen.status, keygen.basis) == ("29 µs", "pass", "benchmark")
    operations = by_id["ML-KEM-768:operations"]
    assert operations.measured == "36 µs / 40 µs"
    assert by_id["ML-KEM-768:handshake"].basis == "model"
    assert by_id["ML-KEM-768:handshake"].status == "pass"


def test_hybrid_handshake_overhead_counts_an_extra_round_trip_when_the_window_is_exceeded(verifier):
    ref = pqc_benchmarks.load_reference()
    sig = ref["algorithms"]["ML-DSA-65"]
    limits = load_policy()["thresholds"]
    item = verifier.verify(plan("ML-DSA-65", "ECDSA-P256"))
    handshake = next(r for r in item.test_results if r.id == "ML-DSA-65:handshake")

    cpu_ms = (sig["sign_us"] + sig["verify_us"] * (limits["chain_certs"] + 1)) / 1000
    # the ML-DSA chain adds ~14.6 KB to the server flight, pushing it past the 14.6 KB window
    assert handshake.measured == f"+{cpu_ms + limits['assumed_rtt_ms']:.1f} ms"
    assert "1 extra round trip" in handshake.detail
    assert handshake.status == "pass"  # 40.6 ms is inside the 50 ms budget


def test_simulated_results_are_labelled_and_never_change_the_outcome(verifier, monkeypatch):
    item = verifier.verify(plan("ML-DSA-65", "ECDSA-P256"))
    simulated = [r for r in item.test_results if r.basis == "simulated"]
    assert {r.id for r in simulated} == {"certificate_chain_validation", "hybrid_interoperability"}
    assert all("Simulated" in r.detail for r in simulated)

    baseline = item.overall
    real = verifier._test_results

    def with_failing_simulation(*args, **kwargs):
        return [
            *real(*args, **kwargs),
            TestResult(
                id="x",
                name="x",
                measured="FAIL",
                threshold="-",
                status="fail",
                basis="simulated",
            ),
        ]

    monkeypatch.setattr(verifier, "_test_results", with_failing_simulation)
    assert verifier.verify(plan("ML-DSA-65", "ECDSA-P256")).overall == baseline


def test_certificate_chain_simulation_only_for_signature_or_certificate_targets(verifier):
    kem_only = verifier.verify(plan("ML-KEM-768", "ECDH-P256"))
    assert "certificate_chain_validation" not in {r.id for r in kem_only.test_results}
    certificate = verifier.verify(plan("ML-KEM-768", asset_type="certificate"))
    assert "certificate_chain_validation" in {r.id for r in certificate.test_results}


# --- summary -----------------------------------------------------------------------------
def test_summary_counts_are_consistent(verifier):
    items = verifier.verify_many(
        [
            plan("ML-KEM-768", "ECDH-P256"),
            plan("ML-KEM-512 + SLH-DSA-SHA2-128f"),
            plan("ML-DSA-44"),
            plan("PQC-capable hybrid integration", asset_type="application"),
        ]
    )
    summary = summarize(items)
    assert summary.total == 4
    assert (summary.verified, summary.blocked, summary.pending, summary.conditional) == (1, 1, 2, 0)
    assert summary.verified + summary.conditional + summary.pending + summary.blocked == 4
    for counts in summary.checks.values():
        assert sum(counts.values()) == 4
    assert summary.checks["performance_threshold"]["fail"] == 1


# --- HTTP API ----------------------------------------------------------------------------
def _login(username: str = "security-analyst") -> dict[str, str]:
    with SessionLocal() as db:
        tokens = AuthenticationService().login(
            db,
            LoginRequest(
                organization="SecureBank",
                username=username,
                password=get_settings().demo_password,
            ),
        )
    return {"Authorization": f"Bearer {tokens.access_token}"}


def _seed() -> None:
    with SessionLocal() as db:
        seed_securebank_demo(db)


def test_api_requires_authentication():
    assert TestClient(app).get("/api/v1/analytics/validation/migrations").status_code == 401


def test_api_verifies_every_migration_plan_of_the_organisation():
    _seed()
    client = TestClient(app)
    plans = client.get("/api/v1/migration/recommendations", headers=_login()).json()
    response = client.get(
        "/api/v1/analytics/validation/migrations", headers=_login("security-auditor")
    )

    assert response.status_code == 200  # read-only roles may view it
    body = response.json()
    assert body["summary"]["total"] == len(plans) > 0
    assert len(body["items"]) == len(plans)
    assert {item["asset_id"] for item in body["items"]} == {p["asset_id"] for p in plans}
    for item in body["items"]:
        assert [c["id"] for c in item["checks"]] == list(CHECK_IDS)
        assert len(item["hybrid_steps"]) == 3
    assert body["thresholds"]["max_operation_us"] > 0
    counts = body["summary"]
    assert (
        counts["verified"] + counts["conditional"] + counts["pending"] + counts["blocked"]
        == counts["total"]
    )


def test_api_project_filter_and_tenant_isolation():
    _seed()
    client = TestClient(app)
    headers = _login()
    everything = client.get("/api/v1/analytics/validation/migrations", headers=headers).json()
    nothing = client.get(
        "/api/v1/analytics/validation/migrations",
        headers=headers,
        params={"project_id": "no-such-project"},
    ).json()
    assert everything["summary"]["total"] > 0
    assert nothing["summary"]["total"] == 0

    with SessionLocal() as db:
        outsider = AuthenticationService().register(
            db,
            RegisterRequest(
                organization_name="Outside Org",
                industry="Technology",
                username="outsider",
                email="outsider@example.test",
                password=secrets.token_urlsafe(24),
            ),
        )
    seen = client.get(
        "/api/v1/analytics/validation/migrations",
        headers={"Authorization": f"Bearer {outsider.access_token}"},
    ).json()
    assert seen["summary"]["total"] == 0  # another tenant's plans are invisible
