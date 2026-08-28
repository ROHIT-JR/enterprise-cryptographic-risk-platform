from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5


class CBOMGenerator:
    """Generate an ECDAT-CBOM document aligned with CycloneDX CBOM concepts."""

    format_name = "ECDAT-CBOM"
    spec_version = "1.0"

    def generate(
        self,
        *,
        project: Mapping[str, Any],
        scan: Mapping[str, Any],
        assets: Iterable[Mapping[str, Any]],
        relationships: Iterable[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        asset_list = list(assets)
        ref_by_id: dict[str, str] = {}
        components: list[dict[str, Any]] = []

        for asset in asset_list:
            asset_id = str(asset["id"])
            bom_ref = f"urn:ecdat:asset:{asset_id}"
            ref_by_id[asset_id] = bom_ref
            components.append(self._component(asset, bom_ref))

        dependency_map: dict[str, set[str]] = {ref: set() for ref in ref_by_id.values()}
        relationship_records: list[dict[str, str]] = []
        for relationship in relationships:
            source = ref_by_id.get(str(relationship["source_asset_id"]))
            target = ref_by_id.get(str(relationship["target_asset_id"]))
            if not source or not target:
                continue
            dependency_map[source].add(target)
            relationship_records.append(
                {
                    "source": source,
                    "target": target,
                    "type": str(relationship.get("relationship_type", "DEPENDS_ON")),
                }
            )

        scan_id = str(scan["id"])
        return {
            "bomFormat": self.format_name,
            "specVersion": self.spec_version,
            "serialNumber": f"urn:uuid:{uuid5(NAMESPACE_URL, f'ecdat-scan:{scan_id}')}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(UTC).isoformat(),
                "tools": [
                    {
                        "vendor": "ECDAT-X",
                        "name": "Cryptographic Discovery Engine",
                        "version": "0.1.0",
                    }
                ],
                "component": {
                    "bom-ref": f"urn:ecdat:project:{project['id']}",
                    "type": "application",
                    "name": project["name"],
                    "properties": [
                        {
                            "name": "ecdat:criticality",
                            "value": project.get("criticality", "medium"),
                        },
                        {"name": "ecdat:scan-source", "value": scan.get("source_type", "unknown")},
                    ],
                },
            },
            "components": components,
            "dependencies": [
                {"ref": source, "dependsOn": sorted(targets)}
                for source, targets in dependency_map.items()
                if targets
            ],
            "relationships": relationship_records,
            "properties": [
                {"name": "ecdat:scan-id", "value": scan_id},
                {"name": "ecdat:target", "value": scan.get("target", "")},
            ],
        }

    @staticmethod
    def _component(asset: Mapping[str, Any], bom_ref: str) -> dict[str, Any]:
        asset_type = str(asset.get("asset_type", "cryptographic-asset"))
        algorithm = asset.get("algorithm")
        properties = [
            {"name": "ecdat:asset-type", "value": asset_type},
            {"name": "ecdat:location", "value": str(asset.get("location", ""))},
            {"name": "ecdat:evidence", "value": str(asset.get("evidence", ""))},
            {"name": "ecdat:confidence", "value": str(asset.get("confidence", 0))},
        ]
        if asset.get("risk_score") is not None:
            properties.extend(
                [
                    {"name": "ecdat:risk-score", "value": str(asset["risk_score"])},
                    {"name": "ecdat:risk-severity", "value": str(asset.get("risk_severity", ""))},
                ]
            )

        component: dict[str, Any] = {
            "bom-ref": bom_ref,
            "type": "library" if asset_type == "library" else "cryptographic-asset",
            "name": asset["name"],
            "version": asset.get("version"),
            "properties": properties,
        }
        if asset_type == "application":
            component["type"] = "application"
        if asset_type in {"algorithm", "certificate", "protocol"} or algorithm:
            component["cryptoProperties"] = {
                "assetType": asset_type,
                "algorithmProperties": {
                    "primitive": algorithm or asset.get("name"),
                    "executionEnvironment": "software-plain-ram",
                    "implementationPlatform": "unknown",
                    "certificationLevel": [],
                    "mode": "unknown",
                    "padding": "unknown",
                },
            }
        return {key: value for key, value in component.items() if value is not None}
