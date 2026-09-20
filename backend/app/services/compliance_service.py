"""India NQM compliance mapping.

Every requirement is scored from data ECDAT-X already computed elsewhere in the
platform (scans, risk analyses, migration plans, lifecycle state, verification
reports) — nothing here is asserted or hardcoded per organization.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    Asset,
    BusinessContext,
    MigrationPlan,
    Organization,
    RiskAnalysis,
    Scan,
)
from backend.app.services.migration_verification_service import build_verification_report
from lifecycle_engine.models import LifecycleState

_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "config"
NQM_CONFIG_PATH = _CONFIG_ROOT / "nqm_compliance.json"
SECTOR_CONFIG_PATH = _CONFIG_ROOT / "sector_profiles.json"

CRYPTO_TYPES = ("algorithm", "library", "certificate", "protocol", "configuration")
NIST_PQC_PREFIXES = ("ML-KEM", "ML-DSA", "SLH-DSA", "FN-DSA")
ADVANCED_STATES = {
    LifecycleState.ASSESSED.value,
    LifecycleState.RECOMMENDED.value,
    LifecycleState.MIGRATION_PLANNED.value,
    LifecycleState.MIGRATING.value,
    LifecycleState.REPLACED.value,
    LifecycleState.RETIRED.value,
}


@cache
def load_nqm_config(path: Path = NQM_CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@cache
def load_sector_profiles(path: Path = SECTOR_CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def match_sector_profile(industry: str | None) -> dict[str, Any]:
    profiles = load_sector_profiles()
    normalized = (industry or "").strip().lower()
    if normalized:
        for profile in profiles["profiles"]:
            if any(token in normalized for token in profile["match_industries"]):
                return profile
    return profiles["default"]


class _Context:
    """Query results shared by every requirement check for one organization."""

    def __init__(self, db: Session, organization_id: str) -> None:
        self.db = db
        self.organization_id = organization_id
        self.crypto_assets = list(
            db.scalars(
                select(Asset).where(
                    Asset.organization_id == organization_id,
                    Asset.asset_type.in_(CRYPTO_TYPES),
                )
            )
        )
        self.risk_rows = list(
            db.execute(
                select(RiskAnalysis, Asset)
                .join(Asset, RiskAnalysis.asset_id == Asset.id)
                .where(RiskAnalysis.organization_id == organization_id)
            ).all()
        )
        self.business_contexts = list(
            db.scalars(
                select(BusinessContext).where(
                    BusinessContext.asset_id.in_([asset.id for asset in self.crypto_assets])
                )
            )
        ) if self.crypto_assets else []
        self.migration_plans = list(
            db.scalars(
                select(MigrationPlan).where(MigrationPlan.organization_id == organization_id)
            )
        )
        self.completed_scans = db.scalar(
            select(Scan).where(
                Scan.organization_id == organization_id, Scan.status == "completed"
            )
        )
        self._verification = None

    @property
    def verification(self):
        if self._verification is None:
            self._verification = build_verification_report(self.db, self.organization_id)
        return self._verification


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return min(numerator / denominator, 1.0)


# --------------------------------------------------------------- Phase 1 checks


def has_completed_scan(ctx: _Context) -> tuple[float, str]:
    ok = ctx.completed_scans is not None
    return (1.0 if ok else 0.0, "At least one completed scan" if ok else "No completed scans yet")


def has_assets(ctx: _Context) -> tuple[float, str]:
    total = len(ctx.crypto_assets)
    return (1.0 if total > 0 else 0.0, f"{total} cryptographic assets in inventory")


def assets_assessed_ratio(ctx: _Context) -> tuple[float, str]:
    total = len(ctx.crypto_assets)
    scored = len(ctx.risk_rows)
    return (_ratio(scored, total), f"{scored}/{total} crypto assets quantum-risk assessed")


def has_hndl_findings(ctx: _Context) -> tuple[float, str]:
    count = sum(1 for risk, _ in ctx.risk_rows if risk.hndl_risk in {"critical", "high"})
    return (
        1.0 if count > 0 else 0.0,
        f"{count} assets flagged for harvest-now-decrypt-later exposure",
    )


def business_context_ratio(ctx: _Context) -> tuple[float, str]:
    total = len(ctx.crypto_assets)
    covered = len(ctx.business_contexts)
    return (_ratio(covered, total), f"{covered}/{total} assets have business-criticality context")


# --------------------------------------------------------------- Phase 2 checks


def has_roadmap(ctx: _Context) -> tuple[float, str]:
    sequenced = sum(1 for plan in ctx.migration_plans if plan.wave is not None)
    return (1.0 if sequenced > 0 else 0.0, f"{sequenced} assets sequenced into migration waves")


def nist_algorithm_ratio(ctx: _Context) -> tuple[float, str]:
    total = len(ctx.migration_plans)
    matching = sum(
        1
        for plan in ctx.migration_plans
        if plan.recommended_algorithm.upper().startswith(NIST_PQC_PREFIXES)
    )
    return (
        _ratio(matching, total),
        f"{matching}/{total} recommendations target NIST-standardized PQC algorithms",
    )


def wave1_in_progress(ctx: _Context) -> tuple[float, str]:
    asset_by_id = {asset.id: asset for asset in ctx.crypto_assets}
    wave1 = [
        plan for plan in ctx.migration_plans if plan.wave == 1 and plan.asset_id in asset_by_id
    ]
    if not wave1:
        return (0.0, "No Wave 1 trust-anchor assets identified yet")
    advanced = sum(
        1 for plan in wave1 if asset_by_id[plan.asset_id].lifecycle_state in ADVANCED_STATES
    )
    return (_ratio(advanced, len(wave1)), f"{advanced}/{len(wave1)} Wave 1 assets past discovery")


def has_verified_migrations(ctx: _Context) -> tuple[float, str]:
    summary = ctx.verification.summary
    if summary.total == 0:
        return (0.0, "No migration plans to verify yet")
    resolved = summary.verified + summary.conditional
    evidence = (
        f"{summary.verified} verified, {summary.conditional} conditional "
        f"of {summary.total} plans checked"
    )
    return (_ratio(resolved, summary.total), evidence)


def hndl_prioritized(ctx: _Context) -> tuple[float, str]:
    plan_by_asset = {plan.asset_id: plan for plan in ctx.migration_plans}
    hndl_assets = [
        asset
        for risk, asset in ctx.risk_rows
        if risk.hndl_risk in {"critical", "high"} and asset.id in plan_by_asset
    ]
    if not hndl_assets:
        return (1.0, "No harvest-now-decrypt-later assets require prioritization")
    in_wave1 = sum(1 for asset in hndl_assets if plan_by_asset[asset.id].wave == 1)
    return (
        _ratio(in_wave1, len(hndl_assets)),
        f"{in_wave1}/{len(hndl_assets)} HNDL-critical assets scheduled in Wave 1",
    )


# --------------------------------------------------------------- Phase 3 checks


def replaced_ratio(ctx: _Context) -> tuple[float, str]:
    asset_by_id = {asset.id: asset for asset in ctx.crypto_assets}
    vulnerable = [asset for risk, asset in ctx.risk_rows if risk.quantum_score >= 50]
    if not vulnerable:
        return (1.0, "No quantum-vulnerable assets remain")
    replaced = sum(
        1
        for asset in vulnerable
        if asset_by_id[asset.id].lifecycle_state == LifecycleState.REPLACED.value
    )
    evidence = f"{replaced}/{len(vulnerable)} quantum-vulnerable assets replaced"
    return (_ratio(replaced, len(vulnerable)), evidence)


def verified_ratio(ctx: _Context) -> tuple[float, str]:
    summary = ctx.verification.summary
    if summary.total == 0:
        return (0.0, "No migration plans to verify yet")
    return (
        _ratio(summary.verified, summary.total),
        f"{summary.verified}/{summary.total} migration plans fully verified",
    )


def compatibility_reviewed_ratio(ctx: _Context) -> tuple[float, str]:
    total = len(ctx.business_contexts)
    reviewed = sum(1 for context in ctx.business_contexts if context.compatibility != "unknown")
    evidence = f"{reviewed}/{total} assets have a reviewed compatibility posture"
    return (_ratio(reviewed, total), evidence)


CHECKS: dict[str, Callable[[_Context], tuple[float, str]]] = {
    "has_completed_scan": has_completed_scan,
    "has_assets": has_assets,
    "assets_assessed_ratio": assets_assessed_ratio,
    "has_hndl_findings": has_hndl_findings,
    "business_context_ratio": business_context_ratio,
    "has_roadmap": has_roadmap,
    "nist_algorithm_ratio": nist_algorithm_ratio,
    "wave1_in_progress": wave1_in_progress,
    "has_verified_migrations": has_verified_migrations,
    "hndl_prioritized": hndl_prioritized,
    "replaced_ratio": replaced_ratio,
    "verified_ratio": verified_ratio,
    "compatibility_reviewed_ratio": compatibility_reviewed_ratio,
}


def build_compliance_report(db: Session, organization_id: str) -> dict[str, Any]:
    config = load_nqm_config()
    ctx = _Context(db, organization_id)
    organization = db.get(Organization, organization_id)
    sector = match_sector_profile(organization.industry if organization else None)

    phases = []
    for phase in config["phases"]:
        requirements = []
        for requirement in phase["requirements"]:
            ratio, evidence = CHECKS[requirement["check"]](ctx)
            requirements.append(
                {
                    "id": requirement["id"],
                    "label": requirement["label"],
                    "complete": ratio >= 1.0,
                    "progress": round(ratio * 100),
                    "evidence": evidence,
                }
            )
        phase_progress = round(
            sum(item["progress"] for item in requirements) / len(requirements)
        ) if requirements else 0
        phases.append(
            {
                "id": phase["id"],
                "name": phase["name"],
                "years": phase["years"],
                "description": phase["description"],
                "progress": phase_progress,
                "status": (
                    "complete"
                    if phase_progress >= 95
                    else "in-progress"
                    if phase_progress > 0
                    else "not-started"
                ),
                "requirements": requirements,
            }
        )

    current_phase = next(
        (phase["id"] for phase in phases if phase["status"] != "complete"), phases[-1]["id"]
    )
    overall_progress = (
        round(sum(phase["progress"] for phase in phases) / len(phases)) if phases else 0
    )

    return {
        "source": config["source"],
        "organization_id": organization_id,
        "organization_name": organization.name if organization else organization_id,
        "current_phase": current_phase,
        "overall_progress": overall_progress,
        "phases": phases,
        "sector": sector,
    }
