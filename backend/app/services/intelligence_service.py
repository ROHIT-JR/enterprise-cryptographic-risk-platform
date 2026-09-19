from __future__ import annotations

import logging
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
from backend.app.services.lifecycle_service import LifecycleService
from graph_analysis.networkx_layer import NetworkXGraphLayer
from lifecycle_engine import GovernanceStatus, LifecycleState, TransitionRequest
from migration_engine import (
    MigrationRoadmapEngine,
    PQCRecommendationEngine,
    PQCRecommendationInput,
)
from risk_engine.business_criticality import BusinessCriticalityEngine
from risk_engine.dependency_centrality import (
    CentralityAssessment,
    DependencyCentralityEngine,
)
from risk_engine.evidence_engine import EvidenceIntelligenceEngine
from risk_engine.final_risk_engine import FinalRiskEngine, FinalRiskInput
from risk_engine.hndl_analysis import HNDLAnalysisEngine, HNDLInput
from risk_engine.migration_complexity import (
    MigrationComplexityEngine,
    MigrationComplexityInput,
)
from risk_engine.quantum_risk import QuantumRiskEngine

logger = logging.getLogger(__name__)

INTELLIGENCE_TYPES = {"algorithm", "certificate", "protocol", "library"}


class IntelligenceService:
    """Build and persist Phase 2 intelligence from normalized Phase 1.5 inventory."""

    def __init__(self) -> None:
        self.evidence = EvidenceIntelligenceEngine()
        self.quantum = QuantumRiskEngine()
        self.hndl = HNDLAnalysisEngine()
        self.centrality = DependencyCentralityEngine()
        self.networkx_layer = NetworkXGraphLayer()
        self.business = BusinessCriticalityEngine()
        self.complexity = MigrationComplexityEngine()
        self.final = FinalRiskEngine()
        self.lifecycle = LifecycleService()
        self.mosca = __import__(
            "risk_engine.mosca_model", fromlist=["MoscaModel"]
        ).MoscaModel()
        self.evidence_fusion = __import__(
            "risk_engine.evidence_fusion", fromlist=["EvidenceFusionEngine"]
        ).EvidenceFusionEngine()
        self.advanced_ext = __import__(
            "risk_engine.advanced_risk_extension", fromlist=["AdvancedRiskExtension"]
        ).AdvancedRiskExtension()
        self.recommendations = PQCRecommendationEngine()
        from migration_engine.topsis_recommendation import TOPSISRecommendationEngine
        self.topsis_recommendations = TOPSISRecommendationEngine()
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
        # The PostgreSQL inventory is authoritative; calculate legacy baseline for all assets
        centrality: dict[str, CentralityAssessment] = self.centrality.analyze_all(
            nodes=nodes, edges=edge_pairs
        )

        # Attempt NetworkX-based metrics enhancement if available
        try:
            payload = self.networkx_layer.fetch_payload(
                project_id=project.id,
                organization_id=project.organization_id,
            )
            if payload and payload.nodes:
                G = self.networkx_layer.build_graph(payload)
                if G.number_of_nodes() > 0:
                    nx_metrics = self.networkx_layer.compute_metrics(
                        G,
                        project_id=project.id,
                        organization_id=project.organization_id,
                    )
                    if nx_metrics:
                        # Overlay NetworkX metrics onto PostgreSQL assets
                        for asset in assets:
                            if asset.id in nx_metrics:
                                mdata = nx_metrics[asset.id]
                                legacy = centrality[asset.id]
                                deg_val = float(
                                    mdata.get(
                                        "degree_centrality",
                                        legacy.degree_centrality,
                                    )
                                )
                                score_val = float(
                                    mdata.get(
                                        "centrality_score",
                                        mdata.get(
                                            "blast_radius",
                                            legacy.centrality_score,
                                        ),
                                    )
                                )
                                centrality[asset.id] = CentralityAssessment(
                                    asset=legacy.asset,
                                    dependent_systems=int(
                                        mdata.get("dependent_systems", legacy.dependent_systems)
                                    ),
                                    degree_centrality=round(
                                        min(max(deg_val, 0.0), 1.0), 4
                                    ),
                                    critical_path_impact=legacy.critical_path_impact,
                                    centrality_score=round(
                                        min(max(score_val, 0.0), 1.0), 4
                                    ),
                                    dependent_ids=list(
                                        mdata.get("dependent_ids", legacy.dependent_ids)
                                    ),
                                )
                        # Write-back once after successful computation (non-fatal)
                        try:
                            self.networkx_layer.write_back(
                                project_id=project.id,
                                metrics=nx_metrics,
                                organization_id=project.organization_id,
                            )
                        except Exception as wb_exc:
                            logger.warning(
                                "NetworkX metric write-back failed for project %s: %s",
                                project.id,
                                wb_exc,
                            )
        except Exception as exc:
            logger.warning(
                "NetworkX graph intelligence failed for project %s; using legacy centrality: %s",
                project.id,
                exc,
            )
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
            # Original evidence assessment (kept for explanation)
            evidence_original = self.evidence.assess(
                asset.name,
                sources_by_family[self._algorithm_family(algorithm)],
            )
            # New evidence fusion using Dempster‑Shafer
            # Convert each source confidence into a simple mass dict (True mass = confidence)
            source_masses = []
            for _src in sources_by_family[self._algorithm_family(algorithm)]:
                # Treat each source as having the same confidence as original evidence
                # In a real implementation, each source would have its own confidence metric
                mass = {
                    "True": evidence_original.confidence / 100.0,
                    "False": 0.0,
                    "Both": 1.0 - (evidence_original.confidence / 100.0),
                }
                source_masses.append(mass)
            evidence_fused = self.evidence_fusion.fuse(source_masses)
            # Use fused confidence for downstream scoring
            evidence_confidence = evidence_fused["confidence"]
            evidence_explanation = evidence_original.explanation

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
            explanations.append(evidence_explanation)
            final = self.final.assess(
                FinalRiskInput(
                    asset=asset.name,
                    quantum_vulnerability=quantum.score,
                    hndl_exposure=hndl.score,
                    dependency_centrality=graph.centrality_score * 100,
                    business_criticality=business.score,
                    migration_complexity=complexity.score,
                    evidence_confidence=evidence_confidence,
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
                "evidence_confidence": evidence_confidence,
                "final_score": final.score,
                "severity": final.severity,
                "hndl_risk": hndl.hndl_risk,
                "quantum_classification": quantum.classification,
                "dependent_systems": graph.dependent_systems,
                "evidence_sources": evidence_original.evidence_sources,
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
        dep_map: dict[str, list[str]] = defaultdict(list)
        
        for relationship in relationships:
            source, target = relationship.source_asset_id, relationship.target_asset_id
            adjacency[source].add(target)
            adjacency[target].add(source)
            if relationship.relationship_type == "PROTECTS":
                dependencies.append((target, source))
                dep_map[target].append(source)
            else:
                dependencies.append((source, target))
                dep_map[source].append(target)
                
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
        
        # Gather all risk analyses to extract raw risk factors for the M4 optimizer
        risk_analyses = db.scalars(
            select(RiskAnalysis).where(RiskAnalysis.asset_id.in_(candidates))
        ).all()
        risk_by_id = {r.asset_id: r for r in risk_analyses}
        
        # 1. First Pass: Compute properties required by both Optimizer and Fallback
        computed_plans = {}
        optimizer_inputs = []
        
        # Late import to prevent circular dependency
        from migration_engine.optimizer_models import OptimizerInput
        
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
                req_input = PQCRecommendationInput(
                    asset=asset.name,
                    current_algorithm=current_algorithm,
                    use_case=str(asset.details.get("use_case", asset.asset_type)),
                    compatibility=context.compatibility,
                    memory_constraint=str(asset.details.get("memory_constraint", "standard")),
                )
                try:
                    recommendation = self.topsis_recommendations.recommend(req_input).model_dump()
                except Exception as e:
                    logger.warning("TOPSIS recommendation failed for %s: %s", asset.name, e)
                    recommendation = self.recommendations.recommend(req_input).model_dump()
                    
            complexity = self.complexity.assess(
                MigrationComplexityInput(
                    dependency_count=graph.dependent_systems,
                    legacy_technology=context.legacy_technology,
                    application_criticality=context.criticality,
                    downtime_requirement=context.downtime_requirement,
                    compatibility=context.compatibility,
                )
            )
            
            # Retrieve available risk scores
            risk_model = risk_by_id.get(asset_id)
            quantum_score = risk_model.quantum_score if risk_model else None
            hndl_score = risk_model.hndl_score if risk_model else None
            business_score = risk_model.business_score if risk_model else None
            
            # Map blast radius using the NetworkX Graph's output
            blast_radius = min(
                100.0, float(graph.dependent_systems * 10)
            )  # Approximation based on deps, usually properly set in NetworkX

            optimizer_inputs.append(
                OptimizerInput(
                    asset_id=asset_id,
                    asset_name=asset.name,
                    asset_type=asset.asset_type,
                    quantum_score=quantum_score,
                    hndl_score=hndl_score,
                    blast_radius=blast_radius,
                    business_criticality=business_score,
                    migration_complexity=complexity.migration_complexity_score
                    if hasattr(complexity, "migration_complexity_score")
                    else 50.0,
                    recommended_algorithm=recommendation["recommended_algorithm"],
                    dependencies=dep_map[asset_id],
                    vendor_ready=True,
                    compatibility_blocked=False,
                    legacy_reasons=complexity.reasons,
                    recommendation_metadata=recommendation,
                )
            )
            
            computed_plans[asset_id] = {
                "recommendation": recommendation,
                "complexity": complexity,
            }

        # 2. Attempt M4 Optimization
        optimized_result = None
        if getattr(self, "optimizer", None) is None:
            try:
                from migration_engine.optimizer import DependencyAwareOptimizer
                self.optimizer = DependencyAwareOptimizer()
            except ImportError:
                pass

        if getattr(self, "optimizer", None) is not None:
            try:
                optimized_result = self.optimizer.optimize(optimizer_inputs)
            except Exception as e:
                logger.warning(
                    "DependencyAwareOptimizer failed: %s. Falling back to baseline roadmap.", e
                )

        # 3. Apply results
        if optimized_result and optimized_result.assets:
            for asset_id, opt_asset in optimized_result.assets.items():
                plan = db.scalar(select(MigrationPlan).where(MigrationPlan.asset_id == asset_id))
                computed = computed_plans[asset_id]
                
                values = {
                    "organization_id": project.organization_id,
                    "project_id": project.id,
                    "recommended_algorithm": opt_asset.recommended_algorithm,
                    "wave": opt_asset.wave,
                    "complexity": computed["complexity"].migration_complexity,
                    "reasons": opt_asset.rationale,
                    "recommendation": computed["recommendation"],
                    "priority_score": opt_asset.priority_score,
                    "confidence": opt_asset.confidence,
                    "optimizer_version": optimized_result.optimizer_version,
                    "constraints": opt_asset.constraints,
                }
                if plan:
                    for key, value in values.items():
                        setattr(plan, key, value)
                else:
                    db.add(MigrationPlan(asset_id=asset_id, **values))
        else:
            # Fallback to Phase 2 roadmap
            roadmap = self.roadmap.generate(
                assets=roadmap_assets,
                dependencies=dependencies,
                included_ids=candidates,
            )
            wave_by_id = {item.asset_id: item for item in roadmap}
            
            for asset_id in candidates:
                computed = computed_plans[asset_id]
                item = wave_by_id[asset_id]
                plan = db.scalar(select(MigrationPlan).where(MigrationPlan.asset_id == asset_id))
                values = {
                    "organization_id": project.organization_id,
                    "project_id": project.id,
                    "recommended_algorithm": computed["recommendation"]["recommended_algorithm"],
                    "wave": item.wave,
                    "complexity": computed["complexity"].migration_complexity,
                    "reasons": [item.reason, *computed["complexity"].reasons],
                    "recommendation": computed["recommendation"],
                    "priority_score": None,
                    "confidence": None,
                    "optimizer_version": None,
                    "constraints": [],
                }
                if plan:
                    for key, value in values.items():
                        setattr(plan, key, value)
                else:
                    db.add(MigrationPlan(asset_id=asset_id, **values))

        # 4. Lifecycle Transitions (Audit Trail)
        db.flush() # Ensure plans are persisted before we link metadata
        for asset_id in candidates:
            plan = db.scalar(select(MigrationPlan).where(MigrationPlan.asset_id == asset_id))
            asset = assets_by_id[asset_id]
            
            # Step 1: DISCOVERED -> ASSESSED
            # Evidence: Must have a completed risk assessment.
            has_assessment = asset_id in risk_by_id
            if asset.lifecycle_state == "DISCOVERED" and has_assessment:
                self.lifecycle.process_transition(
                    db,
                    asset_id,
                    project.organization_id,
                    project.id,
                    TransitionRequest(
                        target_state=LifecycleState.ASSESSED,
                        source="Intelligence Pipeline",
                        is_automated=True,
                    ),
                )
                
            # Step 2: ASSESSED -> RECOMMENDED
            # Evidence: must have a specific PQC recommendation that is not empty/none
            # or 'Keep existing cryptography'.
            recommendation_dict = computed_plans.get(asset_id, {}).get("recommendation", {})
            recommendation_val = (
                recommendation_dict.get("recommended_algorithm", "")
                if isinstance(recommendation_dict, dict)
                else ""
            )
            has_recommendation = bool(
                recommendation_val
                and recommendation_val.strip()
                and "keep existing" not in recommendation_val.lower()
            )

            if asset.lifecycle_state == "ASSESSED" and has_recommendation:
                self.lifecycle.process_transition(
                    db,
                    asset_id,
                    project.organization_id,
                    project.id,
                    TransitionRequest(
                        target_state=LifecycleState.RECOMMENDED,
                        source="Intelligence Pipeline",
                        is_automated=True,
                    ),
                )
                
            # Step 3: RECOMMENDED -> MIGRATION_PLANNED / BLOCKED
            if asset.lifecycle_state == "RECOMMENDED":
                metadata = {
                    "migration_plan_id": plan.id if plan else None,
                    "optimizer_version": plan.optimizer_version if plan else None,
                    "migration_wave": plan.wave if plan else None
                }
                if plan and plan.wave is not None:
                    self.lifecycle.process_transition(
                        db, asset_id, project.organization_id, project.id, 
                        TransitionRequest(
                            target_state=LifecycleState.MIGRATION_PLANNED, 
                            target_governance_status=GovernanceStatus.ACTIVE, 
                            source="M4 Optimizer", 
                            is_automated=True, 
                            metadata=metadata
                        )
                    )
                else:
                    self.lifecycle.process_transition(
                        db, asset_id, project.organization_id, project.id, 
                        TransitionRequest(
                            target_state=LifecycleState.RECOMMENDED, 
                            target_governance_status=GovernanceStatus.BLOCKED, 
                            reason="Blocked by hard constraints or prerequisite constraints",
                            source="M4 Optimizer", 
                            is_automated=True, 
                            metadata=metadata
                        )
                    )

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
