"""Verification of PQC migration recommendations.

For each migration plan this derives, from the plan's own recommendation metadata, the NIST
knowledge base and the benchmark reference data:

* a five-item verification checklist (compatibility, performance, key size, backward
  compatibility, rollback),
* a hybrid migration path (add PQC alongside classical, soak, then cut over), and
* test results.

Checklist status rests only on evidence the platform computed. Test results whose ``basis`` is
``simulated`` are illustrative placeholders (no PQC-capable X.509 stack is integrated) and never
influence the overall status.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from benchmarks import pqc_benchmarks
from migration_engine.pqc_knowledge_base import PQCCandidate, PQCKnowledgeBase

POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "migration_verification.json"

CheckStatus = Literal["pass", "warn", "fail", "pending"]
OverallStatus = Literal["verified", "conditional", "pending", "blocked"]
CheckBasis = Literal["computed", "policy", "generated"]
ResultStatus = Literal["pass", "fail", "pending"]
ResultBasis = Literal["benchmark", "model", "simulated"]

CHECK_IDS = (
    "algorithm_compatibility",
    "performance_threshold",
    "key_size",
    "backward_compatibility",
    "rollback_plan",
)
# When several targets or rules disagree, the least reassuring status wins.
_STATUS_ORDER: dict[str, int] = {"fail": 3, "pending": 2, "warn": 1, "pass": 0}


class VerificationCheck(BaseModel):
    id: str
    title: str
    status: CheckStatus
    basis: CheckBasis
    evidence: list[str] = Field(default_factory=list)


class HybridStep(BaseModel):
    step: int
    title: str
    description: str
    duration_days: int
    exit_criteria: str


class TestResult(BaseModel):
    __test__ = False  # not a pytest class

    id: str
    name: str
    measured: str
    threshold: str
    status: ResultStatus
    basis: ResultBasis
    detail: str = ""


class MigrationVerification(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    wave: int
    current_algorithm: str
    recommended_algorithm: str
    target_kind: Literal["algorithm", "integration"]
    targets: list[str]
    overall: OverallStatus
    checks: list[VerificationCheck]
    hybrid_steps: list[HybridStep]
    rollback_plan: list[str]
    test_results: list[TestResult]


class VerificationSummary(BaseModel):
    total: int
    verified: int
    conditional: int
    pending: int
    blocked: int
    checks: dict[str, dict[str, int]]


class MigrationVerificationReport(BaseModel):
    thresholds: dict[str, float]
    hybrid_schedule_days: dict[str, int]
    summary: VerificationSummary
    items: list[MigrationVerification]


@dataclass
class PlanView:
    """The parts of a stored migration plan that verification needs."""

    asset_id: str
    asset_name: str
    asset_type: str
    wave: int
    current_algorithm: str
    recommended_algorithm: str
    constraints: list[str] = field(default_factory=list)
    recommendation: dict[str, Any] = field(default_factory=dict)


@cache
def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@cache
def _knowledge_base() -> PQCKnowledgeBase:
    return PQCKnowledgeBase()


def _fmt_us(us: float) -> str:
    if us >= 1000:
        return f"{us / 1000:.2f} ms".replace(".00 ms", " ms")
    return f"{us:g} µs"


def _worst(statuses: Iterable[str], default: CheckStatus = "pass") -> CheckStatus:
    return max(statuses, key=_STATUS_ORDER.__getitem__, default=default)  # type: ignore[return-value]


class MigrationVerifier:
    def __init__(
        self,
        reference: dict[str, Any] | None = None,
        policy: dict[str, Any] | None = None,
        knowledge_base: PQCKnowledgeBase | None = None,
    ) -> None:
        self.reference = reference or pqc_benchmarks.load_reference()
        self.policy = policy or load_policy()
        self.kb = knowledge_base or _knowledge_base()
        self.limits: dict[str, float] = self.policy["thresholds"]

    # -- public -------------------------------------------------------------------------
    def verify(self, plan: PlanView) -> MigrationVerification:
        targets = [part.strip() for part in plan.recommended_algorithm.split("+") if part.strip()]
        known = [t for t in targets if self.kb.get(t) or t in self.reference["algorithms"]]
        kind: Literal["algorithm", "integration"] = "algorithm" if known else "integration"

        checks = [
            self._compatibility(plan, targets, kind),
            self._performance(targets, kind),
            self._key_size(targets, kind),
            self._backward_compatibility(plan),
            self._rollback(plan, targets, kind),
        ]
        return MigrationVerification(
            asset_id=plan.asset_id,
            asset_name=plan.asset_name,
            asset_type=plan.asset_type,
            wave=plan.wave,
            current_algorithm=plan.current_algorithm,
            recommended_algorithm=plan.recommended_algorithm,
            target_kind=kind,
            targets=targets,
            overall=self._overall(checks),
            checks=checks,
            hybrid_steps=self._hybrid_steps(plan, targets, kind),
            rollback_plan=self._rollback_steps(plan, targets, kind),
            test_results=self._test_results(plan, targets, kind),
        )

    def verify_many(self, plans: Iterable[PlanView]) -> list[MigrationVerification]:
        return [self.verify(plan) for plan in plans]

    def report(self, items: list[MigrationVerification]) -> MigrationVerificationReport:
        return MigrationVerificationReport(
            thresholds=self.limits,
            hybrid_schedule_days=self.policy["hybrid_schedule_days"],
            summary=summarize(items),
            items=items,
        )

    # -- checklist ----------------------------------------------------------------------
    @staticmethod
    def _overall(checks: list[VerificationCheck]) -> OverallStatus:
        statuses = {check.status for check in checks}
        if "fail" in statuses:
            return "blocked"
        if "pending" in statuses:
            return "pending"
        if "warn" in statuses:
            return "conditional"
        return "verified"

    def _compatibility(self, plan: PlanView, targets: list[str], kind: str) -> VerificationCheck:
        title = "Algorithm compatibility verified"
        if kind == "integration":
            hint = (plan.recommendation.get("metrics") or {}).get("compatibility")
            return VerificationCheck(
                id="algorithm_compatibility",
                title=title,
                status="pending",
                basis="policy",
                evidence=[
                    f"'{plan.recommended_algorithm}' is an application or library upgrade, not "
                    "a standardised algorithm.",
                    "Algorithm support is inherited from the dependencies it migrates behind; "
                    + (f"{hint}." if hint else "integration testing is required."),
                ],
            )
        statuses: list[str] = []
        evidence: list[str] = []
        functions: set[str] = set()
        for target in targets:
            candidate: PQCCandidate | None = self.kb.get(target)
            if candidate is None:
                statuses.append("warn")
                evidence.append(f"{target}: not in the NIST-standardised knowledge base.")
                continue
            functions.add(candidate.function)
            statuses.append("pass")
            evidence.append(
                f"{target}: {candidate.source}, NIST level {candidate.nist_level}, "
                f"knowledge-base compatibility score {candidate.compatibility:.2f}."
            )
        detected = set(plan.recommendation.get("detected_functions") or [])
        missing = sorted(detected - functions)
        if missing:
            statuses.append("warn")
            evidence.append(
                "No replacement selected for detected function(s): " + ", ".join(missing) + "."
            )
        return VerificationCheck(
            id="algorithm_compatibility",
            title=title,
            status=_worst(statuses),
            basis="computed",
            evidence=evidence,
        )

    def _timings(self, target: str) -> dict[str, float] | None:
        entry = self.reference["algorithms"].get(target)
        if entry is None:
            return None
        keys = pqc_benchmarks.TIMING_KEYS[entry["kind"]]
        return {key: float(entry[key]) for key in keys}

    def _within_limits(self, timings: dict[str, float]) -> bool:
        keygen_ok = timings["keygen_us"] <= self.limits["max_keygen_us"]
        ops_ok = all(
            value <= self.limits["max_operation_us"]
            for key, value in timings.items()
            if key != "keygen_us"
        )
        return keygen_ok and ops_ok

    def _performance(self, targets: list[str], kind: str) -> VerificationCheck:
        title = "Performance benchmarks within threshold"
        if kind == "integration":
            return VerificationCheck(
                id="performance_threshold",
                title=title,
                status="pending",
                basis="policy",
                evidence=["Performance is inherited from the migrated dependencies; not measured."],
            )
        statuses: list[str] = []
        evidence: list[str] = []
        extra: list[str] = []
        for target in targets:
            timings = self._timings(target)
            if timings is None:
                statuses.append("pending")
                evidence.append(
                    f"{target}: no benchmark data yet; run a live benchmark or add reference data."
                )
                continue
            ok = self._within_limits(timings)
            statuses.append("pass" if ok else "fail")
            if not ok and (alternative := self._alternative(target)):
                extra.append(alternative)
            parts = ", ".join(f"{k.removesuffix('_us')} {_fmt_us(v)}" for k, v in timings.items())
            evidence.append(
                f"{target}: {parts} "
                f"(limits: keygen {_fmt_us(self.limits['max_keygen_us'])}, "
                f"operations {_fmt_us(self.limits['max_operation_us'])})."
            )
        return VerificationCheck(
            id="performance_threshold",
            title=title,
            status=_worst(statuses),
            basis="computed",
            evidence=[*evidence, *extra],
        )

    def _alternative(self, target: str) -> str | None:
        """A same-function candidate at an equal or higher NIST level that meets the limits."""
        candidate = self.kb.get(target)
        if candidate is None:
            return None
        others = sorted(
            self.kb.candidates_for_function(candidate.function),
            key=lambda c: (c.nist_level, c.public_key_bytes + c.sig_or_ct_bytes),
        )
        for other in others:
            if other.name == target or other.nist_level < candidate.nist_level:
                continue
            timings = self._timings(other.name)
            if timings and self._within_limits(timings):
                return (
                    f"Alternative within the limits: {other.name} (NIST level "
                    f"{other.nist_level}, {other.source})."
                )
        return None

    def _key_size(self, targets: list[str], kind: str) -> VerificationCheck:
        title = "Key size acceptable for infrastructure"
        budget = int(self.limits["max_wire_bytes"])
        window = self.reference["tls_model"]["initial_congestion_window_bytes"]
        if kind == "integration":
            return VerificationCheck(
                id="key_size",
                title=title,
                status="pending",
                basis="policy",
                evidence=["Key and signature sizes are inherited from the migrated dependencies."],
            )
        statuses: list[str] = []
        evidence: list[str] = []
        for target in targets:
            candidate = self.kb.get(target)
            if candidate is None:
                statuses.append("pending")
                evidence.append(f"{target}: sizes unknown (not in the knowledge base).")
                continue
            label = "ciphertext" if candidate.function == "key_establishment" else "signature"
            wire = candidate.public_key_bytes + candidate.sig_or_ct_bytes
            within = wire <= budget
            statuses.append("pass" if within else "warn")
            note = (
                f"within the {budget:,} B budget"
                if within
                else f"exceeds the {budget:,} B budget (initial congestion window {window:,} B)"
            )
            evidence.append(
                f"{target}: public key {candidate.public_key_bytes:,} B + {label} "
                f"{candidate.sig_or_ct_bytes:,} B = {wire:,} B, {note}."
            )
        return VerificationCheck(
            id="key_size",
            title=title,
            status=_worst(statuses),
            basis="computed",
            evidence=evidence,
        )

    @staticmethod
    def _backward_compatibility(plan: PlanView) -> VerificationCheck:
        strategy = plan.recommendation.get("hybrid_strategy")
        constraints = [
            *plan.constraints,
            *(plan.recommendation.get("constraints") or []),
        ]
        evidence: list[str] = []
        if strategy:
            evidence.append(f"Hybrid strategy keeps the classical path active: {strategy}.")
            status: CheckStatus = "pass"
        else:
            evidence.append("No hybrid strategy recorded; classical-only peers would break.")
            status = "warn"
        if constraints:
            evidence.append("Constraints to resolve: " + "; ".join(map(str, constraints)) + ".")
            status = "warn"
        return VerificationCheck(
            id="backward_compatibility",
            title="Backward compatibility confirmed",
            status=status,
            basis="policy",
            evidence=evidence,
        )

    def _rollback(self, plan: PlanView, targets: list[str], kind: str) -> VerificationCheck:
        steps = self._rollback_steps(plan, targets, kind)
        return VerificationCheck(
            id="rollback_plan",
            title="Rollback plan documented",
            status="pass",
            basis="generated",
            evidence=[f"{len(steps)}-step rollback plan generated for this migration (see below)."],
        )

    # -- hybrid path & rollback -----------------------------------------------------------
    def _hybrid_steps(self, plan: PlanView, targets: list[str], kind: str) -> list[HybridStep]:
        days = self.policy["hybrid_schedule_days"]
        classical = plan.current_algorithm
        strategy = plan.recommendation.get("hybrid_strategy")
        if kind == "integration":
            first = f"Upgrade {plan.asset_name} to a PQC-capable release (dual-stack)"
            last = f"Retire classical-only mode in {plan.asset_name}"
            add_detail = strategy or "Run classical and PQC client support side by side."
        else:
            pqc = " + ".join(targets)
            first = f"Add {pqc} alongside {classical} (hybrid mode)"
            last = f"Remove {classical} (PQC-only mode)"
            add_detail = strategy or f"Run {pqc} and {classical} side by side."
        return [
            HybridStep(
                step=1,
                title=first,
                description=add_detail,
                duration_days=days["deploy"],
                exit_criteria=(
                    "Hybrid handshakes succeed for both classical-only and PQC-capable peers."
                ),
            ),
            HybridStep(
                step=2,
                title=f"Test hybrid for {days['soak']} days",
                description=(
                    "Monitor handshake success rate, latency and errors with both algorithms "
                    "active, against the pre-migration baseline."
                ),
                duration_days=days["soak"],
                exit_criteria="No regression versus baseline and no rollback trigger fired.",
            ),
            HybridStep(
                step=3,
                title=last,
                description=(
                    "Disable the classical algorithm once no classical-only peers remain and the "
                    "inventory confirms PQC-only operation."
                ),
                duration_days=days["cutover"],
                exit_criteria="Classical algorithm no longer negotiated; re-scan is clean.",
            ),
        ]

    @staticmethod
    def _rollback_steps(plan: PlanView, targets: list[str], kind: str) -> list[str]:
        classical = plan.current_algorithm
        steps = [
            "Rollback trigger: handshake failure or latency regression above the pre-migration "
            "baseline during the hybrid test window.",
        ]
        if kind == "integration":
            steps.append(
                f"Disable the PQC client path in {plan.asset_name} (feature flag or previous "
                "release); classical clients keep working because dual-stack was retained."
            )
        else:
            steps.append(
                f"Remove {' + '.join(targets)} from the negotiated algorithms; {classical} "
                "remains active throughout the hybrid period, so no keys need to be re-issued."
            )
        if plan.wave == 1:
            steps.append(
                "Keep the previous certificates and keys archived until the cutover step "
                "completes (trust-anchor asset)."
            )
        steps.append("Re-run the inventory scan and confirm the asset reports its prior state.")
        return steps

    # -- test results ---------------------------------------------------------------------
    def _handshake_overhead(self, target: str) -> dict[str, float] | None:
        entry = self.reference["algorithms"].get(target)
        if entry is None:
            return None
        model = self.reference["tls_model"]
        window = model["initial_congestion_window_bytes"]
        chain = int(self.limits["chain_certs"])
        baseline = pqc_benchmarks.migration_impact(
            self.reference, "ECDH-P256", "ECDH-P256", "ECDSA-P256", "ECDSA-P256", chain
        )["before"]["server_flight_bytes"]
        if entry["kind"] == "kem":
            cpu_us = entry["keygen_us"] + entry["encaps_us"] + entry["decaps_us"]
            server_bytes = entry["ct_bytes"]
        else:
            cpu_us = entry["sign_us"] + entry["verify_us"] * (chain + 1)
            server_bytes = (
                chain * (entry["pk_bytes"] + entry["sig_bytes"] + model["cert_overhead_bytes"])
                + entry["sig_bytes"]
            )
        extra_rtts = max(
            0, math.ceil((baseline + server_bytes) / window) - math.ceil(baseline / window)
        )
        rtt_ms = self.limits["assumed_rtt_ms"]
        return {
            "cpu_us": float(cpu_us),
            "baseline": float(baseline),
            "total": float(baseline + server_bytes),
            "extra_rtts": float(extra_rtts),
            "added_ms": cpu_us / 1000 + extra_rtts * rtt_ms,
        }

    def _test_results(self, plan: PlanView, targets: list[str], kind: str) -> list[TestResult]:
        results: list[TestResult] = []
        if kind == "algorithm":
            for target in targets:
                results.extend(self._benchmark_results(target))
        function_kinds = {self.kb.get(t).function for t in targets if self.kb.get(t)}
        if kind == "algorithm" and (
            "digital_signature" in function_kinds or plan.asset_type == "certificate"
        ):
            results.append(
                TestResult(
                    id="certificate_chain_validation",
                    name="Certificate chain validation",
                    measured="PASS",
                    threshold="chain validates",
                    status="pass",
                    basis="simulated",
                    detail=("Simulated placeholder: no PQC-capable X.509 stack is integrated yet."),
                )
            )
        results.append(
            TestResult(
                id="hybrid_interoperability",
                name="Hybrid interoperability with a classical-only peer",
                measured="PASS",
                threshold="handshake completes",
                status="pass",
                basis="simulated",
                detail="Simulated placeholder: no interoperability harness is integrated yet.",
            )
        )
        return results

    def _benchmark_results(self, target: str) -> list[TestResult]:
        timings = self._timings(target)
        if timings is None:
            return [
                TestResult(
                    id=f"{target}:benchmark",
                    name=f"{target} benchmark",
                    measured="not measured",
                    threshold="—",
                    status="pending",
                    basis="benchmark",
                    detail="No benchmark data for this algorithm yet.",
                )
            ]
        keygen, *operations = timings.items()
        limit_op, limit_kg = self.limits["max_operation_us"], self.limits["max_keygen_us"]
        results = [
            TestResult(
                id=f"{target}:keygen",
                name=f"{target} keygen",
                measured=_fmt_us(keygen[1]),
                threshold=f"≤ {_fmt_us(limit_kg)}",
                status="pass" if keygen[1] <= limit_kg else "fail",
                basis="benchmark",
            ),
            TestResult(
                id=f"{target}:operations",
                name=f"{target} " + " / ".join(k.removesuffix("_us") for k, _ in operations),
                measured=" / ".join(_fmt_us(v) for _, v in operations),
                threshold=f"≤ {_fmt_us(limit_op)} each",
                status="pass" if all(v <= limit_op for _, v in operations) else "fail",
                basis="benchmark",
            ),
        ]
        overhead = self._handshake_overhead(target)
        if overhead is not None:
            limit = self.limits["max_added_handshake_ms"]
            rtt = self.limits["assumed_rtt_ms"]
            results.append(
                TestResult(
                    id=f"{target}:handshake",
                    name=f"TLS handshake with hybrid {target}",
                    measured=f"+{overhead['added_ms']:.1f} ms",
                    threshold=f"≤ {limit:g} ms",
                    status="pass" if overhead["added_ms"] <= limit else "fail",
                    basis="model",
                    detail=(
                        f"{overhead['cpu_us'] / 1000:.2f} ms CPU + {int(overhead['extra_rtts'])} "
                        f"extra round trip(s) at {rtt:g} ms; server flight "
                        f"{overhead['baseline']:,.0f} → {overhead['total']:,.0f} B."
                    ),
                )
            )
        return results


def summarize(items: list[MigrationVerification]) -> VerificationSummary:
    counts = {"verified": 0, "conditional": 0, "pending": 0, "blocked": 0}
    by_check: dict[str, dict[str, int]] = {
        check_id: {"pass": 0, "warn": 0, "fail": 0, "pending": 0} for check_id in CHECK_IDS
    }
    for item in items:
        counts[item.overall] += 1
        for check in item.checks:
            by_check[check.id][check.status] += 1
    return VerificationSummary(total=len(items), checks=by_check, **counts)
