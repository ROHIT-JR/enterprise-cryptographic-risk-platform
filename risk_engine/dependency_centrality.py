from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel, Field


class CentralityAssessment(BaseModel):
    asset: str
    dependent_systems: int = Field(ge=0)
    degree_centrality: float = Field(ge=0, le=1)
    critical_path_impact: float = Field(ge=0, le=1)
    centrality_score: float = Field(ge=0, le=1)
    dependent_ids: list[str]


class DependencyCentralityEngine:
    """Calculate blast radius from the same relationships projected to Neo4j."""

    def analyze_all(
        self,
        *,
        nodes: dict[str, dict],
        edges: list[tuple[str, str]],
    ) -> dict[str, CentralityAssessment]:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for source, target in edges:
            adjacency[source].add(target)
            adjacency[target].add(source)
        total = max(len(nodes) - 1, 1)
        raw: dict[str, tuple[list[str], float, float]] = {}
        maximum_dependents = 1
        for node_id, node in nodes.items():
            reachable = self._reachable(node_id, adjacency)
            applications = sorted(
                item
                for item in reachable
                if nodes.get(item, {}).get("asset_type") == "application"
            )
            critical = [
                item
                for item in applications
                if nodes[item].get("criticality", "medium") in {"critical", "high"}
            ]
            degree = min(len(adjacency[node_id]) / total, 1.0)
            critical_impact = len(critical) / max(len(applications), 1)
            raw[node_id] = (applications, degree, critical_impact)
            maximum_dependents = max(maximum_dependents, len(applications))

        results: dict[str, CentralityAssessment] = {}
        for node_id, (applications, degree, critical_impact) in raw.items():
            dependency_ratio = len(applications) / maximum_dependents
            score = min(
                degree * 0.3 + dependency_ratio * 0.5 + critical_impact * 0.2,
                1.0,
            )
            results[node_id] = CentralityAssessment(
                asset=nodes[node_id].get("name", node_id),
                dependent_systems=len(applications),
                degree_centrality=round(degree, 4),
                critical_path_impact=round(critical_impact, 4),
                centrality_score=round(score, 4),
                dependent_ids=applications,
            )
        return results

    @staticmethod
    def _reachable(start: str, adjacency: dict[str, set[str]]) -> set[str]:
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        visited.remove(start)
        return visited
