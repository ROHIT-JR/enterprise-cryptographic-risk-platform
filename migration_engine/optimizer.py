from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from migration_engine.optimizer_models import OptimizationResult, OptimizedAsset, OptimizerInput

logger = logging.getLogger(__name__)


class DependencyAwareOptimizer:
    """Dependency-aware cryptographic migration optimizer."""

    VERSION = "1.0.0"

    # Default weights for individual factors.
    # We do NOT use composite final_risk_score to avoid double counting.
    DEFAULT_WEIGHTS = {
        "quantum_score": 0.30,
        "hndl_score": 0.20,
        "blast_radius": 0.20,
        "business_criticality": 0.20,
        "migration_complexity": 0.10,  # Treated as a penalty (subtracted)
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights if weights is not None else dict(self.DEFAULT_WEIGHTS)

    def optimize(self, inputs: list[OptimizerInput]) -> OptimizationResult:
        if not inputs:
            return OptimizationResult(waves={}, assets={}, optimizer_version=self.VERSION, configuration=self.weights)

        inputs_by_id = {item.asset_id: item for item in inputs}
        
        G = nx.DiGraph()
        for item in inputs:
            G.add_node(item.asset_id)
            for dep_id in item.dependencies:
                if dep_id in inputs_by_id:
                    G.add_edge(dep_id, item.asset_id)

        # 1. Identify intrinsically blocked assets
        blocked_assets = set()
        for item in inputs:
            if not item.vendor_ready or item.compatibility_blocked:
                blocked_assets.add(item.asset_id)

        # 2. SCC Condensation and Blocked propagation within SCC
        condensed = nx.condensation(G)
        
        # If any member of an SCC is blocked, the whole SCC is blocked
        for scc_node in condensed.nodes():
            members = set(condensed.nodes[scc_node]["members"])
            if blocked_assets.intersection(members):
                blocked_assets.update(members)

        # 3. Propagate blockers to dependents (BFS over the condensed DAG)
        # In our DAG, dep_id -> consumer_id. Thus successors are consumers (dependents).
        blocked_scc_nodes = [n for n in condensed.nodes() if blocked_assets.intersection(condensed.nodes[n]["members"])]
        for b_scc in blocked_scc_nodes:
            for reachable_scc in nx.descendants(condensed, b_scc):
                blocked_assets.update(condensed.nodes[reachable_scc]["members"])

        # 4. Compute Priority
        priorities: dict[str, tuple[float | None, float, list[str]]] = {}
        for item in inputs:
            priorities[item.asset_id] = self._calculate_priority(item)

        waves: dict[int, list[OptimizedAsset]] = {}
        assets: dict[str, OptimizedAsset] = {}
        
        try:
            topo_order = list(nx.topological_sort(condensed))
        except nx.NetworkXUnfeasible:
            topo_order = list(condensed.nodes)

        scc_wave_map = {}
        
        for scc_node in topo_order:
            members = condensed.nodes[scc_node]["members"]
            is_blocked = bool(blocked_assets.intersection(members))
            
            if is_blocked:
                current_wave = None
            else:
                preds = [p for p in condensed.predecessors(scc_node) if scc_wave_map[p] is not None]
                if not preds:
                    current_wave = 1
                else:
                    current_wave = 1 + max(scc_wave_map[p] for p in preds)
                
            scc_wave_map[scc_node] = current_wave
            
            if current_wave is not None and current_wave not in waves:
                waves[current_wave] = []
                
            is_cycle = len(members) > 1
            sorted_members = sorted(
                members, 
                key=lambda m: (priorities[m][0] or 0.0), 
                reverse=True
            )
            
            for m in sorted_members:
                item = inputs_by_id[m]
                score, confidence, missing = priorities[m]
                
                constraints = []
                if not item.vendor_ready:
                    constraints.append("Vendor not ready")
                if item.compatibility_blocked:
                    constraints.append("Compatibility blocked")
                    
                # Identify if blocked by a dependency
                # (if I am blocked but I don't have intrinsic blockers, I am blocked by dependency or SCC cycle)
                if current_wave is None and not constraints:
                    # Check explicit dependencies
                    blocked_deps = [d for d in item.dependencies if d in blocked_assets]
                    if blocked_deps:
                        constraints.append(f"Blocked by prerequisites: {','.join(blocked_deps)}")
                    elif is_cycle:
                        constraints.append("Blocked by cyclic SCC cluster member")
                
                rationale = list(item.legacy_reasons)
                if is_cycle:
                    rationale.append("These assets form a dependency cycle and should be migrated together or within the same coordinated maintenance window.")
                if missing:
                    rationale.append(f"Missing factors for prioritization: {', '.join(missing)}.")
                if current_wave is None:
                    rationale.append("Hard constraints block immediate migration execution.")
                elif current_wave > 1:
                    rationale.append("Scheduled after dependency prerequisites.")
                
                opt_asset = OptimizedAsset(
                    asset_id=item.asset_id,
                    asset_name=item.asset_name,
                    wave=current_wave,
                    priority_score=score if current_wave is not None else None,
                    confidence=confidence,
                    recommended_algorithm=item.recommended_algorithm,
                    constraints=constraints,
                    rationale=rationale
                )
                
                if current_wave is not None:
                    waves[current_wave].append(opt_asset)
                assets[item.asset_id] = opt_asset

        for w in waves:
            waves[w].sort(key=lambda a: (a.priority_score or 0.0), reverse=True)

        return OptimizationResult(
            waves=waves,
            assets=assets,
            optimizer_version=self.VERSION,
            configuration=self.weights
        )

    def _calculate_priority(self, item: OptimizerInput) -> tuple[float | None, float, list[str]]:
        """Calculates Priority correctly handling missing data."""
        # Using raw individual factors (not final_risk_score) to avoid double-counting.
        factors = {
            "quantum_score": (item.quantum_score, True),
            "hndl_score": (item.hndl_score, True),
            "blast_radius": (item.blast_radius, True),
            "business_criticality": (item.business_criticality, True),
            "migration_complexity": (item.migration_complexity, False)
        }
        
        active_weights = 0.0
        weighted_sum = 0.0
        missing = []
        total_possible_weights = sum(self.weights.values())
        
        for name, (val, is_benefit) in factors.items():
            w = self.weights.get(name, 0.0)
            if val is None:
                missing.append(name)
                continue
                
            active_weights += w
            norm_val = val / 100.0
            
            if is_benefit:
                weighted_sum += w * norm_val
            else:
                weighted_sum += w * (1.0 - norm_val)
                
        if active_weights == 0.0:
            # Prevent arbitrary constant drops. Confidence drops if input is entirely missing.
            return None, 0.0, missing
            
        priority = weighted_sum / active_weights
        priority = max(0.0, min(1.0, priority))
        
        # Rigorous confidence calculation: sum(weights available) / sum(all applicable weights)
        confidence = active_weights / total_possible_weights if total_possible_weights > 0 else 0.0
        confidence = max(0.0, min(1.0, confidence))
        
        return round(priority, 4), round(confidence, 4), missing
