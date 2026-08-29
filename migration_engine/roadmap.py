from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field


class RoadmapItem(BaseModel):
    asset_id: str
    asset: str
    wave: int = Field(ge=1)
    reason: str


class MigrationRoadmapEngine:
    """Order migrations so dependencies and trust anchors move before their consumers."""

    def generate(
        self,
        *,
        assets: dict[str, dict],
        dependencies: list[tuple[str, str]],
        included_ids: set[str] | None = None,
    ) -> list[RoadmapItem]:
        outgoing: dict[str, set[str]] = defaultdict(set)
        for consumer, dependency in dependencies:
            outgoing[consumer].add(dependency)
        included = included_ids or set(assets)
        memo: dict[str, int] = {}

        def wave(node_id: str, visiting: set[str]) -> int:
            if node_id in memo:
                return memo[node_id]
            if node_id in visiting:
                return 1
            direct = [item for item in outgoing[node_id] if item in included]
            value = (
                1
                if not direct
                else 1 + max(wave(item, visiting | {node_id}) for item in direct)
            )
            memo[node_id] = min(value, 9)
            return memo[node_id]

        items = [
            RoadmapItem(
                asset_id=asset_id,
                asset=assets[asset_id].get("name", asset_id),
                wave=wave(asset_id, set()),
                reason=self._reason(assets[asset_id], wave(asset_id, set())),
            )
            for asset_id in included
            if asset_id in assets
        ]
        return sorted(items, key=lambda item: (item.wave, item.asset))

    @staticmethod
    def _reason(asset: dict, wave: int) -> str:
        asset_type = asset.get("asset_type")
        if asset_type == "certificate":
            return (
                "Trust anchor and certificate lifecycle must be upgraded before "
                "dependent services."
            )
        if asset_type in {"algorithm", "protocol"}:
            return "Cryptographic primitive should be made available before consumer migration."
        if wave > 1:
            return "Scheduled after its cryptographic dependencies are migration-ready."
        return "Independent high-risk asset can begin in the first migration wave."
