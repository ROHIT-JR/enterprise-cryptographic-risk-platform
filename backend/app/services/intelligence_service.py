from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import (
    Asset,
    AssetRelationship,
    BusinessContext,
    MigrationPlan,
    Project,
    RiskAnalysis,
    RiskFinding,
)
from backend.app.services.audit_service import record_audit
from migration_engine import (
    MigrationRoadmapEngine,
    PQCRecommendationEngine,
    PQCRecommendationInput,
)
from risk_engine.business_criticality import BusinessCriticalityEngine
from risk_engine.dependency_centrality import DependencyCentralityEngine
from risk_engine.evidence_engine import EvidenceIntelligenceEngine
from risk_engine.final_risk_engine import FinalRiskEngine, FinalRiskInput
from risk_engine.hndl_analysis import HNDLAnalysisEngine, HNDLInput
from risk_engine.migration_complexity import (
    MigrationComplexityEngine,
    MigrationComplexityInput,
)
from risk_engine.quantum_risk import QuantumRiskEngine

INTELLIGENCE_TYPES = {"algorithm", "certificate", "protocol", "library"}


class IntelligenceService:
    """Build and persist Phase 2 intelligence from normalized Phase 1.5 inventory."""

    def __init__(self) -> None:
        self.evidence = EvidenceIntelligenceEngine()
        self.quantum = QuantumRiskEngine()
        self.hndl = HNDLAnalysisEngine()
        self.centrality = DependencyCentralityEngine()
        self.business = BusinessCriticalityEngine()
        self.complexity = MigrationComplexityEngine()
        self.final = FinalRiskEngine()
        self.recommendations = PQCRecommendationEngine()
        self.roadmap = MigrationRoadmapEngine()

    def analyze_project(self, db: Session, project: Project) -> list[RiskAnalysis]:
        assets = list(
            db.scalars(
                select(Asset)
                .where(Asset.project_id == project.id)
                .options(joinedload(Asset.scan))
                .order_by(Asset.created_at)
            ).unique()
        )
        if not assets:
            return []
        relationships = list(
            db.scalars(
                select(AssetRelationship).where(AssetRelationship.project_id == project.id)
            )
        )
        contexts = {asset.id: self._context(db, asset, project) for asset in assets}
        nodes = {
            asset.id: {
                "name": asset.name,
                "asset_type": asset.asset_type,
                "criticality": contexts[asset.id].criticality,
            }
            for asset in assets
        }
        edge_pairs = [
            (relationship.source_asset_id, relationship.target_asset_id)
            for relationship in relationships
        ]
        centrality = self.centrality.analyze_all(nodes=nodes, edges=edge_pairs)
        sources_by_family = self._evidence_sources(assets)
        analyses: list[RiskAnalysis] = []
        vulnerable_ids: set[str] = set()

        for asset in assets:
            if asset.asset_type not in INTELLIGENCE_TYPES:
                continue
            context = contexts[asset.id]
            algorithm = asset.algorithm or asset.name
            quantum = self.quantum.assess(algorithm)
            if quantum.quantum_vulnerable:
                vulnerable_ids.add(asset.id)
            evidence = self.evidence.assess(
                asset.name,
                sources_by_family[self._algorithm_family(algorithm)],
            )
            hndl = self.hndl.assess(
                HNDLInput(
                    asset=asset.name,
                    data_sensitivity=context.data_sensitivity,
                    data_lifetime_years=context.data_lifetime_years,
                    encryption_algorithm=algorithm,
                    exposure_period_years=int(asset.details.get("exposure_period_years", 0)),
                    quantum_vulnerable=quantum.quantum_vulnerable,
                )
            )
            graph = centrality[asset.id]
            business = self.business.assess(context.criticality)
            complexity = self.complexity.assess(
                MigrationComplexityInput(
                    dependency_count=graph.dependent_systems,
                    legacy_technology=context.legacy_technology
                    or quantum.quantum_vulnerable,
                    application_criticality=context.criticality,
                    downtime_requirement=context.downtime_requirement,
                    compatibility=context.compatibility,
                )
            )
            explanations = [quantum.reason, hndl.reason, business.reason]
            if graph.dependent_systems:
                explanations.append(f"Used by {graph.dependent_systems} dependent systems")
            explanations.extend(complexity.reasons)
            explanations.append(evidence.explanation)
            final = self.final.assess(
                FinalRiskInput(
                    asset=asset.name,
                    quantum_vulnerability=quantum.score,
                    hndl_exposure=hndl.score,
                    dependency_centrality=graph.centrality_score * 100,
                    business_criticality=business.score,
                    migration_complexity=complexity.score,
                    evidence_confidence=evidence.confidence,
                    explanations=explanations,
                )
            )
            analysis = db.scalar(select(RiskAnalysis).where(RiskAnalysis.asset_id == asset.id))
            values = {
                "organization_id": project.organization_id,
                "project_id": project.id,
                "quantum_score": quantum.score,
                "hndl_score": hndl.score,
                "centrality_score": graph.centrality_score,
                "business_score": business.score,
                "migration_complexity_score": complexity.score,
                "evidence_confidence": evidence.confidence,
                "final_score": final.score,
                "severity": final.severity,
                "hndl_risk": hndl.hndl_risk,
                "quantum_classification": quantum.classification,
                "dependent_systems": graph.dependent_systems,
                "evidence_sources": evidence.evidence_sources,
                "explanations": final.explanation,
                "factors": {
                    **final.components,
                    "degree_centrality": graph.degree_centrality,
                    "critical_path_impact": graph.critical_path_impact,
                    "dependent_ids": graph.dependent_ids,
                    "hndl_reason": hndl.reason,
                    "quantum_reason": quantum.reason,
                },
            }
            if analysis:
                for key, value in values.items():
                    setattr(analysis, key, value)
            else:
                analysis = RiskAnalysis(asset_id=asset.id, **values)
                db.add(analysis)
            analyses.append(analysis)
            self._promote_final_risk(db, asset, analysis, final.components)

        db.flush()
        self._build_migration_plans(
            db=db,
            project=project,
            assets=assets,
            relationships=relationships,
            contexts=contexts,
            centrality=centrality,
            vulnerable_ids=vulnerable_ids,
        )
        record_audit(
            db,
            action="risk.analysis_completed",
            organization_id=project.organization_id,
            metadata={"project_id": project.id, "assets_analyzed": len(analyses)},
        )
        record_audit(
            db,
            action="migration.generated",
            organization_id=project.organization_id,
            metadata={"project_id": project.id, "vulnerable_assets": len(vulnerable_ids)},
        )
        db.flush()
        return analyses

    @staticmethod
    def _promote_final_risk(
        db: Session,
        asset: Asset,
        analysis: RiskAnalysis,
        components: dict[str, float],
    ) -> None:
        finding = db.scalar(select(RiskFinding).where(RiskFinding.asset_id == asset.id))
        if not finding:
            return
        finding.score = analysis.final_score
        finding.severity = analysis.severity
        finding.reasons = analysis.explanations
        finding.factors = [
            {
                "category": name,
                "points": round(points),
                "explanation": f"Weighted Phase 2 contribution: {points:.2f}",
                "rule_id": f"PHASE2-{name.upper().replace('_', '-')}",
            }
            for name, points in components.items()
        ]

    def _context(self, db: Session, asset: Asset, project: Project) -> BusinessContext:
        context = db.scalar(select(BusinessContext).where(BusinessContext.asset_id == asset.id))
        details = asset.details
        values: dict[str, Any] = {
            "criticality": details.get("business_criticality", project.criticality),
            "owner": details.get("owner"),
            "data_lifetime_years": int(details.get("data_lifetime_years", 5)),
            "data_sensitivity": details.get("data_sensitivity", "internal"),
            "downtime_requirement": details.get("downtime_requirement", "standard"),
            "compatibility": details.get("compatibility", "unknown"),
            "legacy_technology": bool(details.get("legacy_technology", False)),
        }
        if context:
            return context
        context = BusinessContext(asset_id=asset.id, **values)
        db.add(context)
        db.flush()
        return context

    def _evidence_sources(self, assets: list[Asset]) -> dict[str, set[str]]:
        sources: dict[str, set[str]] = defaultdict(set)
        for asset in assets:
            family = self._algorithm_family(asset.algorithm or asset.name)
            explicit = asset.details.get("evidence_sources", [])
            if isinstance(explicit, list):
                sources[family].update(str(item) for item in explicit)
            source_type = asset.scan.source_type if asset.scan else None
            if source_type:
                sources[family].add(source_type)
            detector = asset.details.get("detector")
            if detector:
                sources[family].add(str(detector))
            if asset.asset_type == "certificate":
                sources[family].add("certificate")
        return sources

    def _build_migration_plans(
        self,
        *,
        db: Session,
        project: Project,
        assets: list[Asset],
        relationships: list[AssetRelationship],
        contexts: dict[str, BusinessContext],
        centrality: dict,
        vulnerable_ids: set[str],
    ) -> None:
        assets_by_id = {asset.id: asset for asset in assets}
        adjacency: dict[str, set[str]] = defaultdict(set)
        dependencies: list[tuple[str, str]] = []
        for relationship in relationships:
            source, target = relationship.source_asset_id, relationship.target_asset_id
            adjacency[source].add(target)
            adjacency[target].add(source)
            if relationship.relationship_type == "PROTECTS":
                dependencies.append((target, source))
            else:
                dependencies.append((source, target))
        candidates = set(vulnerable_ids)
        for asset_id in vulnerable_ids:
            candidates.update(self._connected_migration_nodes(asset_id, adjacency, assets_by_id))
        roadmap_assets = {
            asset_id: {
                "name": assets_by_id[asset_id].name,
                "asset_type": assets_by_id[asset_id].asset_type,
            }
            for asset_id in candidates
        }
        roadmap = self.roadmap.generate(
            assets=roadmap_assets,
            dependencies=dependencies,
            included_ids=candidates,
        )
        wave_by_id = {item.asset_id: item for item in roadmap}
        for asset_id in candidates:
            asset = assets_by_id[asset_id]
            context = contexts[asset_id]
            graph = centrality[asset_id]
            current_algorithm = asset.algorithm or asset.name
            if asset.asset_type == "application":
                recommendation = {
                    "asset": asset.name,
                    "current_algorithm": "Dependent application integration",
                    "recommended_algorithm": "PQC-capable hybrid integration",
                    "hybrid_strategy": "Dual-stack classical and PQC client support",
                    "reason": "Update the application after its trust and library dependencies.",
                    "metrics": {
                        "security": "inherits migrated dependencies",
                        "latency": "application-specific",
                        "compatibility": "requires integration testing",
                    },
                    "constraints": [],
                }
            elif asset.asset_type == "library":
                recommendation = {
                    "asset": asset.name,
                    "current_algorithm": asset.name,
                    "recommended_algorithm": "PQC-capable library release",
                    "hybrid_strategy": "Enable hybrid KEM and signature APIs",
                    "reason": "Upgrade the shared implementation before applications consume PQC.",
                    "metrics": {
                        "security": "implementation-dependent",
                        "latency": "benchmark required",
                        "compatibility": "API change likely",
                    },
                    "constraints": [],
                }
            else:
                recommendation = self.recommendations.recommend(
                    PQCRecommendationInput(
                        asset=asset.name,
                        current_algorithm=current_algorithm,
                        use_case=str(asset.details.get("use_case", asset.asset_type)),
                        compatibility=context.compatibility,
                        memory_constraint=str(asset.details.get("memory_constraint", "standard")),
                    )
                ).model_dump()
            complexity = self.complexity.assess(
                MigrationComplexityInput(
                    dependency_count=graph.dependent_systems,
                    legacy_technology=context.legacy_technology,
                    application_criticality=context.criticality,
                    downtime_requirement=context.downtime_requirement,
                    compatibility=context.compatibility,
                )
            )
            plan = db.scalar(select(MigrationPlan).where(MigrationPlan.asset_id == asset_id))
            item = wave_by_id[asset_id]
            values = {
                "organization_id": project.organization_id,
                "project_id": project.id,
                "recommended_algorithm": recommendation["recommended_algorithm"],
                "wave": item.wave,
                "complexity": complexity.migration_complexity,
                "reasons": [item.reason, *complexity.reasons],
                "recommendation": recommendation,
            }
            if plan:
                for key, value in values.items():
                    setattr(plan, key, value)
            else:
                db.add(MigrationPlan(asset_id=asset_id, **values))

    @staticmethod
    def _connected_migration_nodes(
        start: str,
        adjacency: dict[str, set[str]],
        assets: dict[str, Asset],
    ) -> set[str]:
        included: set[str] = set()
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
                if assets[neighbor].asset_type in {"application", "library"}:
                    included.add(neighbor)
        return included

    @staticmethod
    def _algorithm_family(value: str) -> str:
        upper = value.upper().replace("_", "-")
        for family, pattern in (
            ("RSA", r"\bRSA"),
            ("ECC", r"\b(?:ECC|ECDSA|ECDH|P-256|SECP)"),
            ("DH", r"DIFFIE[- ]HELLMAN|\bDH\b"),
            ("AES", r"\bAES"),
            ("TLS", r"\bTLS"),
            ("SHA", r"\bSHA"),
            ("HMAC", r"\bHMAC"),
        ):
            if re.search(pattern, upper):
                return family
        return upper
