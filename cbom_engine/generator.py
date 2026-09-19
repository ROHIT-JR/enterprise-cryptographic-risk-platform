from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

CRYPTO_ASSET_TYPES = {"algorithm", "certificate", "protocol"}
TOOL_VERSION = "0.3.0"

# CycloneDX 1.6 nistQuantumSecurityLevel: 1=AES-128 key search, 2=SHA-256 collision,
# 3=AES-192 key search, 4=SHA-384 collision, 5=AES-256 key search.
_AES_QUANTUM_LEVEL = {128: 1, 192: 3, 256: 5}
_SHA_PROFILE = {
    "1": (63, None),
    "224": (112, None),
    "256": (128, 2),
    "384": (192, 4),
    "512": (256, None),
}
_RSA_CLASSICAL_LEVEL = {1024: 80, 2048: 112, 3072: 128, 4096: 152}
_CURVES = {
    "P-256": ("secp256r1", 128),
    "P-384": ("secp384r1", 192),
    "P-521": ("secp521r1", 256),
}


class CBOMGenerator:
    """Generate a CycloneDX 1.6 CBOM (Cryptography Bill of Materials) document.

    ECDAT-X specific data (risk scores, evidence, scan provenance) is carried in
    namespaced ``ecdat:`` properties so the output validates against the stock
    CycloneDX schema.
    """

    format_name = "CycloneDX"
    spec_version = "1.6"

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

        components_by_ref = {component["bom-ref"]: component for component in components}
        dependency_map: dict[str, set[str]] = {ref: set() for ref in ref_by_id.values()}
        for relationship in relationships:
            source = ref_by_id.get(str(relationship["source_asset_id"]))
            target = ref_by_id.get(str(relationship["target_asset_id"]))
            if not source or not target:
                continue
            relationship_type = str(relationship.get("relationship_type", "DEPENDS_ON")).upper()
            # "A PROTECTS B" means B depends on A; every other type reads source -> target.
            depends, provider = (
                (target, source)
                if relationship_type == "PROTECTS"
                else (
                    source,
                    target,
                )
            )
            dependency_map[depends].add(provider)
            components_by_ref[source]["properties"].append(
                {"name": f"ecdat:relationship:{relationship_type.lower()}", "value": target}
            )

        scan_id = str(scan["id"])
        return {
            "bomFormat": self.format_name,
            "specVersion": self.spec_version,
            "serialNumber": f"urn:uuid:{uuid5(NAMESPACE_URL, f'ecdat-scan:{scan_id}')}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(UTC).isoformat(),
                "tools": {
                    "components": [
                        {
                            "type": "application",
                            "manufacturer": {"name": "ECDAT-X"},
                            "name": "Cryptographic Discovery Engine",
                            "version": TOOL_VERSION,
                        }
                    ]
                },
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
                "properties": self._risk_summary(asset_list),
            },
            "components": components,
            "dependencies": [
                {"ref": ref, "dependsOn": sorted(targets)}
                for ref, targets in dependency_map.items()
            ],
            "properties": [
                {"name": "ecdat:scan-id", "value": scan_id},
                {"name": "ecdat:target", "value": str(scan.get("target", ""))},
            ],
        }

    @staticmethod
    def _risk_summary(assets: list[Mapping[str, Any]]) -> list[dict[str, str]]:
        scored = [asset for asset in assets if asset.get("risk_score") is not None]
        properties = [
            {"name": "ecdat:components-total", "value": str(len(assets))},
            {"name": "ecdat:components-risk-scored", "value": str(len(scored))},
        ]
        if scored:
            scores = [float(asset["risk_score"]) for asset in scored]
            severities = Counter(str(asset.get("risk_severity", "unknown")) for asset in scored)
            properties.extend(
                [
                    {"name": "ecdat:risk-score-max", "value": f"{max(scores):.1f}"},
                    {
                        "name": "ecdat:risk-score-average",
                        "value": f"{sum(scores) / len(scores):.1f}",
                    },
                ]
            )
            properties.extend(
                {"name": f"ecdat:risk-count-{severity}", "value": str(count)}
                for severity, count in sorted(severities.items())
            )
        return properties

    def _component(self, asset: Mapping[str, Any], bom_ref: str) -> dict[str, Any]:
        asset_type = str(asset.get("asset_type", "cryptographic-asset"))
        algorithm = asset.get("algorithm")
        properties = [
            {"name": "ecdat:asset-type", "value": asset_type},
            {"name": "ecdat:location", "value": str(asset.get("location", ""))},
            {"name": "ecdat:evidence", "value": str(asset.get("evidence", ""))},
            {"name": "ecdat:confidence", "value": str(asset.get("confidence", 0))},
        ]
        if algorithm:
            properties.append({"name": "ecdat:algorithm", "value": str(algorithm)})
        if asset.get("risk_score") is not None:
            properties.extend(
                [
                    {"name": "ecdat:risk-score", "value": str(asset["risk_score"])},
                    {"name": "ecdat:risk-severity", "value": str(asset.get("risk_severity", ""))},
                ]
            )

        component: dict[str, Any] = {
            "bom-ref": bom_ref,
            "type": self._component_type(asset_type),
            "name": asset["name"],
            "version": asset.get("version"),
            "properties": properties,
        }
        location = str(asset.get("location") or "")
        if location:
            component["evidence"] = {"occurrences": [{"location": location}]}
        if asset_type in CRYPTO_ASSET_TYPES:
            component["cryptoProperties"] = self._crypto_properties(asset, asset_type, algorithm)
        return {key: value for key, value in component.items() if value is not None}

    @staticmethod
    def _component_type(asset_type: str) -> str:
        return {
            "library": "library",
            "application": "application",
            "configuration": "file",
        }.get(asset_type, "cryptographic-asset")

    def _crypto_properties(
        self, asset: Mapping[str, Any], asset_type: str, algorithm: Any
    ) -> dict[str, Any]:
        name = str(asset.get("name", ""))
        if asset_type == "certificate":
            return {
                "assetType": "certificate",
                "certificateProperties": {"certificateFormat": "X.509"},
            }
        if asset_type == "protocol":
            match = re.search(r"(TLS|SSL|SSH|IPSEC)\s*v?([\d.]+)?", name, re.IGNORECASE)
            protocol = match.group(1).lower() if match else "other"
            properties: dict[str, Any] = {"type": protocol if match else "other"}
            if match and match.group(2):
                properties["version"] = match.group(2)
            return {"assetType": "protocol", "protocolProperties": properties}
        return {
            "assetType": "algorithm",
            "algorithmProperties": self._algorithm_properties(str(algorithm or name)),
        }

    @staticmethod
    def _algorithm_properties(label: str) -> dict[str, Any]:
        upper = label.upper().replace("_", "-")
        properties: dict[str, Any] = {
            "primitive": "unknown",
            "executionEnvironment": "unknown",
            "implementationPlatform": "unknown",
        }

        rsa = re.search(r"RSA[- ]?(\d{3,5})?", upper)
        aes = re.search(r"AES[- ]?(128|192|256)", upper)
        sha = re.search(r"SHA[- ]?(?:2[- ]?)?(1|224|256|384|512)\b", upper)
        curve = re.search(r"P-?(256|384|521)", upper)

        if aes:
            bits = int(aes.group(1))
            mode = re.search(r"\b(GCM|CBC|CTR|CCM|ECB|CFB|OFB)\b", upper)
            properties.update(
                {
                    "primitive": "ae"
                    if mode and mode.group(1) in {"GCM", "CCM"}
                    else "block-cipher",
                    "parameterSetIdentifier": str(bits),
                    "classicalSecurityLevel": bits,
                    "nistQuantumSecurityLevel": _AES_QUANTUM_LEVEL[bits],
                    "cryptoFunctions": ["encrypt", "decrypt"],
                }
            )
            if mode:
                properties["mode"] = mode.group(1).lower()
        elif upper.startswith("HMAC"):
            properties.update({"primitive": "mac", "cryptoFunctions": ["tag"]})
            if sha:
                properties["classicalSecurityLevel"] = _SHA_PROFILE[sha.group(1)][0]
        elif sha:
            classical, quantum = _SHA_PROFILE[sha.group(1)]
            properties.update(
                {
                    "primitive": "hash",
                    "parameterSetIdentifier": sha.group(1),
                    "classicalSecurityLevel": classical,
                    "cryptoFunctions": ["digest"],
                }
            )
            if quantum is not None:
                properties["nistQuantumSecurityLevel"] = quantum
        elif rsa:
            bits = int(rsa.group(1)) if rsa.group(1) else None
            properties.update(
                {
                    "primitive": "pke",
                    "cryptoFunctions": ["keygen", "encrypt", "decrypt", "sign", "verify"],
                    "nistQuantumSecurityLevel": 0,
                }
            )
            if bits:
                properties["parameterSetIdentifier"] = str(bits)
                if bits in _RSA_CLASSICAL_LEVEL:
                    properties["classicalSecurityLevel"] = _RSA_CLASSICAL_LEVEL[bits]
        elif curve or re.search(r"\b(ECC|ECDSA|ECDH|EC)\b", upper):
            key_agreement = "ECDH" in upper
            properties.update(
                {
                    "primitive": "key-agree" if key_agreement else "signature",
                    "cryptoFunctions": (
                        ["keygen", "keyderive"] if key_agreement else ["keygen", "sign", "verify"]
                    ),
                    "nistQuantumSecurityLevel": 0,
                }
            )
            if curve:
                curve_name, classical = _CURVES[f"P-{curve.group(1)}"]
                properties["curve"] = curve_name
                properties["classicalSecurityLevel"] = classical
        elif "DIFFIE" in upper or re.search(r"\bDHE?\b", upper):
            properties.update(
                {
                    "primitive": "key-agree",
                    "cryptoFunctions": ["keygen", "keyderive"],
                    "nistQuantumSecurityLevel": 0,
                }
            )
        return properties
