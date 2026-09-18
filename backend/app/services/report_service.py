from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    Asset,
    AssetRelationship,
    BusinessContext,
    MigrationPlan,
    Organization,
    Project,
    RiskAnalysis,
    Scan,
)
from cbom_engine import CBOMGenerator
from risk_engine.mosca_model import MoscaModel

ReportType = Literal["inventory", "quantum-risk", "migration", "executive-summary", "technical"]

CRYPTO_ASSET_TYPES = {"algorithm", "certificate", "protocol"}
CRYPTO_TYPES = ("algorithm", "library", "certificate", "protocol", "configuration")
SEVERITY_ORDER = ("critical", "high", "medium", "low")
WAVE_TITLES = {
    1: "Trust and cryptographic foundations",
    2: "Direct dependents and shared services",
    3: "Dependent applications",
}
# Month windows (start, end) mirror the Migration Planner timeline in the UI.
WAVE_WINDOWS_MONTHS = {1: (0, 6), 2: (3, 12), 3: (9, 18)}
MAX_GRAPH_NODES = 250
EFFORT_HOURS = {"critical": 80, "high": 40, "medium": 20, "low": 8}


def severity_band(score: float) -> str:
    """Map a 0-100 ECDAT score to its documented severity band."""
    if score >= 81:
        return "critical"
    if score >= 61:
        return "high"
    if score >= 31:
        return "medium"
    return "low"


class ReportService:
    def build(
        self,
        db: Session,
        *,
        organization_id: str,
        report_type: ReportType,
        analyst: str | None = None,
    ) -> dict[str, Any]:
        if report_type == "executive-summary":
            return self.executive_summary(db, organization_id=organization_id, analyst=analyst)
        if report_type == "technical":
            return self.technical_report(db, organization_id=organization_id, analyst=analyst)
        projects = list(
            db.scalars(select(Project).where(Project.organization_id == organization_id))
        )
        organization = db.get(Organization, organization_id)
        header = {
            "report_type": report_type,
            "organization_id": organization_id,
            "organization_name": organization.name if organization else organization_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "project_count": len(projects),
        }
        if report_type == "inventory":
            assets = list(
                db.scalars(
                    select(Asset)
                    .where(Asset.organization_id == organization_id)
                    .order_by(Asset.asset_type, Asset.name)
                )
            )
            return {
                **header,
                "assets": [
                    {
                        "id": asset.id,
                        "type": asset.asset_type,
                        "name": asset.name,
                        "algorithm": asset.algorithm,
                        "version": asset.version,
                        "location": asset.location,
                        "confidence": asset.confidence,
                    }
                    for asset in assets
                ],
            }
        if report_type == "quantum-risk":
            rows = db.execute(
                select(RiskAnalysis, Asset)
                .join(Asset, RiskAnalysis.asset_id == Asset.id)
                .where(RiskAnalysis.organization_id == organization_id)
                .order_by(RiskAnalysis.final_score.desc())
            ).all()
            return {
                **header,
                "risks": [
                    {
                        "asset_id": asset.id,
                        "asset": asset.name,
                        "algorithm": asset.algorithm,
                        "score": risk.final_score,
                        "severity": risk.severity,
                        "hndl_risk": risk.hndl_risk,
                        "dependent_systems": risk.dependent_systems,
                        "explanations": risk.explanations,
                    }
                    for risk, asset in rows
                ],
            }
        rows = db.execute(
            select(MigrationPlan, Asset)
            .join(Asset, MigrationPlan.asset_id == Asset.id)
            .where(MigrationPlan.organization_id == organization_id)
            .order_by(MigrationPlan.wave, Asset.name)
        ).all()
        return {
            **header,
            "migration_plan": [
                {
                    "asset_id": asset.id,
                    "asset": asset.name,
                    "current_algorithm": asset.algorithm or asset.name,
                    "recommended_algorithm": plan.recommended_algorithm,
                    "wave": plan.wave,
                    "complexity": plan.complexity,
                    "reasons": plan.reasons,
                }
                for plan, asset in rows
            ],
        }

    # ------------------------------------------------------------------ CBOM

    def cbom(self, db: Session, *, organization_id: str) -> dict[str, Any]:
        """Organization-wide CycloneDX 1.6 CBOM generated from the live inventory.

        Built from the authoritative inventory (rather than merging stored per-scan
        documents) so it always carries the latest risk scores and is one valid BOM.
        """
        organization = db.get(Organization, organization_id)
        assets = list(
            db.scalars(
                select(Asset)
                .where(Asset.organization_id == organization_id)
                .order_by(Asset.asset_type, Asset.name)
            )
        )
        scores = self._risk_by_asset(db, organization_id)
        relationships = list(
            db.scalars(
                select(AssetRelationship).where(
                    AssetRelationship.organization_id == organization_id
                )
            )
        )
        return CBOMGenerator().generate(
            project={
                "id": organization_id,
                "name": organization.name if organization else organization_id,
                "criticality": "high",
            },
            scan={
                "id": f"enterprise-{organization_id}",
                "source_type": "enterprise",
                "target": "all projects",
            },
            assets=[
                {
                    "id": asset.id,
                    "asset_type": asset.asset_type,
                    "name": asset.name,
                    "algorithm": asset.algorithm,
                    "version": asset.version,
                    "location": asset.location,
                    "evidence": asset.evidence,
                    "confidence": asset.confidence,
                    "risk_score": scores[asset.id][0] if asset.id in scores else None,
                    "risk_severity": scores[asset.id][1] if asset.id in scores else None,
                }
                for asset in assets
            ],
            relationships=[
                {
                    "source_asset_id": item.source_asset_id,
                    "target_asset_id": item.target_asset_id,
                    "relationship_type": item.relationship_type,
                }
                for item in relationships
            ],
        )

    def cbom_report(self, db: Session, *, organization_id: str, analyst: str | None) -> dict:
        """Human-readable companion data for the CBOM JSON export."""
        organization = db.get(Organization, organization_id)
        document = self.cbom(db, organization_id=organization_id)
        return {
            "report_type": "cbom",
            "organization_id": organization_id,
            "organization_name": organization.name if organization else organization_id,
            "analyst": analyst,
            "generated_at": datetime.now(UTC).isoformat(),
            "scan_date": self._latest_scan_date(db, organization_id),
            "cbom": self._cbom_summary(document),
            "components": [
                {
                    "name": component["name"],
                    "type": component["type"],
                    "primitive": component.get("cryptoProperties", {})
                    .get("algorithmProperties", {})
                    .get("primitive"),
                    "quantum_level": component.get("cryptoProperties", {})
                    .get("algorithmProperties", {})
                    .get("nistQuantumSecurityLevel"),
                    "risk_score": _property(component, "ecdat:risk-score"),
                    "risk_severity": _property(component, "ecdat:risk-severity"),
                    "location": _property(component, "ecdat:location"),
                }
                for component in document["components"]
                if component["type"] == "cryptographic-asset" or "cryptoProperties" in component
            ],
        }

    @staticmethod
    def _cbom_summary(document: dict[str, Any]) -> dict[str, Any]:
        components = document["components"]
        metadata_properties = {
            item["name"]: item["value"] for item in document["metadata"].get("properties", [])
        }
        return {
            "format": document["bomFormat"],
            "spec_version": document["specVersion"],
            "serial_number": document["serialNumber"],
            "component_total": len(components),
            "crypto_components": sum(1 for item in components if "cryptoProperties" in item),
            "components_by_type": dict(Counter(item["type"] for item in components)),
            "dependency_edges": sum(len(item["dependsOn"]) for item in document["dependencies"]),
            "risk_average": metadata_properties.get("ecdat:risk-score-average"),
            "risk_max": metadata_properties.get("ecdat:risk-score-max"),
            "risk_scored": metadata_properties.get("ecdat:components-risk-scored"),
        }

    # ------------------------------------------------------ executive summary

    def executive_summary(
        self, db: Session, *, organization_id: str, analyst: str | None = None
    ) -> dict[str, Any]:
        organization = db.get(Organization, organization_id)
        rows = self._analysis_rows(db, organization_id)
        scores = [risk.final_score for risk, _ in rows]
        overall = round(sum(scores) / len(scores), 1) if scores else 0.0

        total_assets = (
            db.scalar(
                select(func.count(Asset.id)).where(
                    Asset.organization_id == organization_id,
                    Asset.asset_type.in_(CRYPTO_TYPES),
                )
            )
            or 0
        )
        plans = self._plans_by_asset(db, organization_id)
        top_assets = [
            {
                "asset": asset.name,
                "type": asset.asset_type,
                "algorithm": asset.algorithm,
                "score": round(risk.final_score, 1),
                "severity": risk.severity,
                "hndl_risk": risk.hndl_risk,
                "dependent_systems": risk.dependent_systems,
                "recommended_algorithm": (
                    plans[asset.id].recommended_algorithm if asset.id in plans else None
                ),
            }
            for risk, asset in rows[:5]
        ]
        mosca = self._mosca_status(db, organization_id, rows, plans)
        return {
            "report_type": "executive-summary",
            "organization_id": organization_id,
            "organization_name": organization.name if organization else organization_id,
            "analyst": analyst,
            "generated_at": datetime.now(UTC).isoformat(),
            "scan_date": self._latest_scan_date(db, organization_id),
            "risk_score": overall,
            "risk_band": severity_band(overall),
            "metrics": {
                "total_assets": total_assets,
                "critical_findings": sum(1 for risk, _ in rows if risk.severity == "critical"),
                "hndl_at_risk": sum(
                    1 for risk, _ in rows if risk.hndl_risk in {"critical", "high"}
                ),
                "quantum_vulnerable": sum(1 for risk, _ in rows if risk.quantum_score >= 50),
                "analyzed_assets": len(rows),
            },
            "severity_counts": {
                level: sum(1 for risk, _ in rows if risk.severity == level)
                for level in SEVERITY_ORDER
            },
            "top_assets": top_assets,
            "mosca": mosca,
            "recommendation": self._recommendation(top_assets, mosca, plans, rows),
        }

    @staticmethod
    def _latest_scan_date(db: Session, organization_id: str) -> str | None:
        latest = db.scalar(
            select(func.max(Scan.completed_at)).where(
                Scan.organization_id == organization_id, Scan.status == "completed"
            )
        ) or db.scalar(
            select(func.max(Scan.created_at)).where(Scan.organization_id == organization_id)
        )
        return latest.isoformat() if latest else None

    @staticmethod
    def _mosca_status(
        db: Session,
        organization_id: str,
        rows: list[tuple[RiskAnalysis, Asset]],
        plans: dict[str, MigrationPlan],
    ) -> dict[str, Any]:
        """Mosca inequality X + Y > Z, evaluated for the quantum-vulnerable estate."""
        vulnerable_ids = [asset.id for risk, asset in rows if risk.quantum_score >= 50]
        model = MoscaModel()
        quantum_year = model.quantum_year
        years_to_quantum = (
            quantum_year - datetime.now(UTC).year if quantum_year > 1000 else quantum_year
        )
        if not vulnerable_ids:
            return {
                "status": "not-applicable",
                "headline": "No quantum-vulnerable assets detected",
                "explanation": "The Mosca inequality applies once quantum-vulnerable "
                "cryptography is present in the estate.",
                "quantum_year": quantum_year,
            }
        lifetimes = db.scalars(
            select(BusinessContext.data_lifetime_years).where(
                BusinessContext.asset_id.in_(vulnerable_ids)
            )
        ).all()
        data_lifetime = max(lifetimes, default=0)
        used_waves = {plan.wave for plan in plans.values() if plan.wave in WAVE_WINDOWS_MONTHS}
        migration_months = max(
            (WAVE_WINDOWS_MONTHS[wave][1] for wave in used_waves),
            default=max(end for _, end in WAVE_WINDOWS_MONTHS.values()),
        )
        migration_years = math.ceil(migration_months / 12)
        # MoscaModel compares against a *relative* horizon in years.
        model.quantum_year = max(years_to_quantum, 0)
        result = model.evaluate(data_lifetime=data_lifetime, migration_time=migration_years)
        behind = result["deadline_risk"] == "Critical"
        return {
            "status": "behind" if behind else "ahead",
            "headline": (
                "BEHIND the quantum timeline" if behind else "AHEAD of the quantum timeline"
            ),
            "formula": result["formula"],
            "explanation": (
                f"Data must stay secret for {data_lifetime} years and migration takes about "
                f"{migration_years}; quantum computers are assumed by {quantum_year} "
                f"(~{years_to_quantum} years). "
                + (
                    "Exposed data outlives the safe window, so migration must begin now."
                    if behind
                    else "The current schedule completes inside the safe window."
                )
            ),
            "data_lifetime_years": data_lifetime,
            "migration_years": migration_years,
            "years_to_quantum": years_to_quantum,
            "quantum_year": quantum_year,
        }

    @staticmethod
    def _recommendation(
        top_assets: list[dict[str, Any]],
        mosca: dict[str, Any],
        plans: dict[str, MigrationPlan],
        rows: list[tuple[RiskAnalysis, Asset]],
    ) -> str:
        if not top_assets:
            return "Run a discovery scan to build the cryptographic inventory and risk model."
        top = top_assets[0]
        wave_one = sum(1 for plan in plans.values() if plan.wave == 1)
        target = f" to {top['recommended_algorithm']}" if top["recommended_algorithm"] else ""
        first = (
            f"Start Wave 1 now: migrate {top['asset']}{target}"
            + (f" together with {wave_one - 1} other trust-layer assets" if wave_one > 1 else "")
            + f" - {top['dependent_systems']} dependent systems inherit its risk."
        )
        if mosca["status"] == "behind":
            return (
                first
                + " The Mosca timeline is already breached; each quarter of delay adds exposure."
            )
        return first + " Keep the roadmap on schedule to stay inside the Mosca window."

    # ------------------------------------------------------ technical report

    def technical_report(
        self, db: Session, *, organization_id: str, analyst: str | None = None
    ) -> dict[str, Any]:
        summary = self.executive_summary(db, organization_id=organization_id, analyst=analyst)
        rows = self._analysis_rows(db, organization_id)
        risk_by_asset = {asset.id: risk for risk, asset in rows}

        inventory_assets = list(
            db.scalars(
                select(Asset)
                .where(
                    Asset.organization_id == organization_id,
                    Asset.asset_type.in_(CRYPTO_TYPES),
                )
                .order_by(Asset.asset_type, Asset.name)
            )
        )
        inventory = [
            {
                "type": asset.asset_type,
                "name": asset.name,
                "algorithm": asset.algorithm,
                "version": asset.version,
                "location": asset.location,
                "score": round(risk_by_asset[asset.id].final_score, 1)
                if asset.id in risk_by_asset
                else None,
                "severity": risk_by_asset[asset.id].severity if asset.id in risk_by_asset else None,
            }
            for asset in inventory_assets
        ]

        categories: dict[str, list[RiskAnalysis]] = defaultdict(list)
        for risk, asset in rows:
            categories[asset.asset_type].append(risk)
        risk_by_category = [
            {
                "category": category,
                "count": len(items),
                "average_score": round(sum(item.final_score for item in items) / len(items), 1),
                "band": severity_band(sum(item.final_score for item in items) / len(items)),
                "max_score": round(max(item.final_score for item in items), 1),
                "severity_counts": {
                    level: sum(1 for item in items if item.severity == level)
                    for level in SEVERITY_ORDER
                },
            }
            for category, items in sorted(categories.items())
        ]

        return {
            **summary,
            "report_type": "technical",
            "inventory": inventory,
            "risk_by_category": risk_by_category,
            "quantum_classification": dict(
                Counter(risk.quantum_classification for risk, _ in rows)
            ),
            "graph": self._graph(db, organization_id, risk_by_asset),
            "roadmap": self._roadmap(db, organization_id),
            "pqc_matrix": self._pqc_matrix(db, organization_id),
            "cbom": self._cbom_summary(self.cbom(db, organization_id=organization_id)),
        }

    @staticmethod
    def _graph(
        db: Session, organization_id: str, risk_by_asset: dict[str, RiskAnalysis]
    ) -> dict[str, Any]:
        all_assets = list(db.scalars(select(Asset).where(Asset.organization_id == organization_id)))
        edges = db.execute(
            select(
                AssetRelationship.source_asset_id,
                AssetRelationship.target_asset_id,
                AssetRelationship.relationship_type,
            ).where(AssetRelationship.organization_id == organization_id)
        ).all()
        degree: Counter[str] = Counter()
        for source, target, _ in edges:
            degree[source] += 1
            degree[target] += 1
        truncated = len(all_assets) > MAX_GRAPH_NODES
        # A printed drawing stops being readable (and gets slow to lay out) past a few
        # hundred nodes, so very large estates keep their most-connected assets.
        assets = (
            sorted(all_assets, key=lambda asset: -degree[asset.id])[:MAX_GRAPH_NODES]
            if truncated
            else all_assets
        )
        index = {asset.id: position for position, asset in enumerate(assets)}
        return {
            "truncated": truncated,
            "total_assets": len(all_assets),
            "nodes": [
                {
                    "label": asset.name,
                    "type": asset.asset_type,
                    "severity": risk_by_asset[asset.id].severity
                    if asset.id in risk_by_asset
                    else None,
                    "degree": degree[asset.id],
                }
                for asset in assets
            ],
            "edges": [
                {"source": index[source], "target": index[target], "type": kind}
                for source, target, kind in edges
                if source in index and target in index
            ],
        }

    @staticmethod
    def _roadmap(db: Session, organization_id: str) -> list[dict[str, Any]]:
        rows = db.execute(
            select(MigrationPlan, Asset)
            .join(Asset, MigrationPlan.asset_id == Asset.id)
            .where(
                MigrationPlan.organization_id == organization_id, MigrationPlan.wave.is_not(None)
            )
            .order_by(MigrationPlan.wave, Asset.name)
        ).all()
        grouped: dict[int, list[tuple[MigrationPlan, Asset]]] = defaultdict(list)
        for plan, asset in rows:
            grouped[plan.wave].append((plan, asset))
        waves = []
        for wave, items in sorted(grouped.items()):
            start, end = WAVE_WINDOWS_MONTHS.get(wave, WAVE_WINDOWS_MONTHS[3])
            waves.append(
                {
                    "wave": wave,
                    "title": WAVE_TITLES.get(wave, WAVE_TITLES[3]),
                    "assets": len(items),
                    "effort_hours": sum(EFFORT_HOURS.get(plan.complexity, 20) for plan, _ in items),
                    "start_month": start,
                    "end_month": end,
                    "examples": [asset.name for _, asset in items[:4]],
                }
            )
        return waves

    @staticmethod
    def _pqc_matrix(db: Session, organization_id: str) -> list[dict[str, Any]]:
        rows = db.execute(
            select(MigrationPlan, Asset)
            .join(Asset, MigrationPlan.asset_id == Asset.id)
            .where(MigrationPlan.organization_id == organization_id)
        ).all()
        grouped: dict[tuple[str, str], list[MigrationPlan]] = defaultdict(list)
        for plan, asset in rows:
            # Algorithms/certs/protocols map one-to-one to a PQC target; applications and
            # libraries only inherit it, so they collapse into one row per recommendation.
            current = (
                asset.algorithm or asset.name
                if asset.asset_type in CRYPTO_ASSET_TYPES
                else f"{asset.asset_type.title()} dependents"
            )
            grouped[(current, plan.recommended_algorithm)].append(plan)
        complexity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        matrix = []
        for (current, recommended), plans in grouped.items():
            waves = [plan.wave for plan in plans if plan.wave is not None]
            matrix.append(
                {
                    "current": current,
                    "recommended": recommended,
                    "assets": len(plans),
                    "wave": min(waves) if waves else None,
                    "complexity": max(
                        (plan.complexity for plan in plans),
                        key=lambda value: complexity_rank.get(value, 1),
                    ),
                    "strategy": next(
                        (
                            plan.recommendation.get("hybrid_strategy")
                            for plan in plans
                            if plan.recommendation.get("hybrid_strategy")
                        ),
                        None,
                    ),
                }
            )
        return sorted(
            matrix, key=lambda item: (item["wave"] is None, item["wave"], -item["assets"])
        )

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _analysis_rows(db: Session, organization_id: str) -> list[tuple[RiskAnalysis, Asset]]:
        return list(
            db.execute(
                select(RiskAnalysis, Asset)
                .join(Asset, RiskAnalysis.asset_id == Asset.id)
                .where(RiskAnalysis.organization_id == organization_id)
                .order_by(RiskAnalysis.final_score.desc(), Asset.name)
            ).all()
        )

    @staticmethod
    def _plans_by_asset(db: Session, organization_id: str) -> dict[str, MigrationPlan]:
        return {
            plan.asset_id: plan
            for plan in db.scalars(
                select(MigrationPlan).where(MigrationPlan.organization_id == organization_id)
            )
        }

    @staticmethod
    def _risk_by_asset(db: Session, organization_id: str) -> dict[str, tuple[float, str]]:
        return {
            asset_id: (round(score, 1), severity)
            for asset_id, score, severity in db.execute(
                select(
                    RiskAnalysis.asset_id, RiskAnalysis.final_score, RiskAnalysis.severity
                ).where(RiskAnalysis.organization_id == organization_id)
            )
        }

    @staticmethod
    def json_bytes(report: dict[str, Any]) -> bytes:
        return json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def pdf_bytes(report: dict[str, Any]) -> bytes:
        from backend.app.services.pdf_report import render_pdf

        return render_pdf(report)


def _property(component: dict[str, Any], name: str) -> str | None:
    return next(
        (item["value"] for item in component.get("properties", []) if item["name"] == name), None
    )
