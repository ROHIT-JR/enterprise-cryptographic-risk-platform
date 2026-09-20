"""Crypto-Agility Score: how easily an organization can swap cryptographic
algorithms without breaking systems.

Heuristics run against the same evidence lines and file locations the
scanners already captured — no separate scanning pass is required. Known
limitation: a hash algorithm name such as "SHA-256" can be mistaken for a
hardcoded 256-bit key size by the key-management-flexibility heuristic,
since both look like a bare number in the evidence text. This only affects
one of five factors (15% weight) and is disclosed here rather than hidden.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- factor 1

_ABSTRACTION_HIGH = re.compile(
    r"getInstance\(\s*[A-Za-z_][A-Za-z0-9_.]*\s*\)"  # Java: getInstance(algorithmVar)
    r"|createCipheriv\(\s*[A-Za-z_][A-Za-z0-9_.]*\s*[,)]"  # Node: createCipheriv(algoVar, ...)
    r"|createHash\(\s*[A-Za-z_][A-Za-z0-9_.]*\s*\)"  # Node: createHash(algoVar)
    r"|crypto\.subtle|SubtleCrypto|window\.crypto"  # Web Crypto API - standardized provider
    r"|os\.environ|getenv\(|process\.env|config\.|settings\."
)
_ABSTRACTION_MEDIUM = re.compile(
    r"getInstance\(\s*[\"']|createCipheriv\(\s*[\"']|createHash\(\s*[\"']"
    r"|hashlib\.new\(|EVP_get_\w+by"
)


def _abstraction_score(evidence: str) -> int:
    if _ABSTRACTION_HIGH.search(evidence):
        return 100
    if _ABSTRACTION_MEDIUM.search(evidence):
        return 60
    return 20


# ---------------------------------------------------------------- factor 2

_CONFIG_REFERENCE = re.compile(r"os\.environ|getenv\(|process\.env|config\.|settings\.")
_CONFIG_FILE_LOCATION = re.compile(
    r"config|settings|constants|\.env\b|\.ya?ml\b|\.toml\b|\.conf\b|\.cnf\b|\.ini\b",
    re.IGNORECASE,
)


def _hardcoding_score(evidence: str, location: str) -> int:
    if _CONFIG_REFERENCE.search(evidence):
        return 100
    if _CONFIG_FILE_LOCATION.search(location):
        return 60
    return 20


# ---------------------------------------------------------------- factor 3


def _coupling_score(distinct_libraries: int) -> int:
    if distinct_libraries >= 4:
        return 100
    if distinct_libraries >= 2:
        return 60
    return 20


# ---------------------------------------------------------------- factor 4

_KEY_CONFIG_REFERENCE = _CONFIG_REFERENCE
_HARDCODED_KEY_SIZE = re.compile(r"\b(512|1024|2048|3072|4096|8192|128|192|256)\b")


def _key_flexibility_score(evidence: str) -> int:
    if _KEY_CONFIG_REFERENCE.search(evidence):
        return 100
    if _HARDCODED_KEY_SIZE.search(evidence):
        return 20
    return 60


# ---------------------------------------------------------------- factor 5


def _protocol_score(protocol_names: set[str]) -> int:
    upper_names = {name.upper() for name in protocol_names}
    if any("HYBRID" in name or "ML-KEM" in name or "ML-DSA" in name for name in upper_names):
        return 100
    if len(protocol_names) >= 2:
        return 60
    if len(protocol_names) == 1:
        return 20
    return 60  # no TLS protocol assets discovered - neutral, not penalized


WEIGHTS = {
    "abstraction_layer_usage": 0.25,
    "algorithm_hardcoding": 0.25,
    "dependency_coupling": 0.20,
    "key_management_flexibility": 0.15,
    "protocol_version_support": 0.15,
}

_BAND_CEILINGS = (
    (30, "crypto-rigid", "Major rearchitecture needed for PQC migration"),
    (60, "crypto-aware", "Moderate effort to migrate"),
    (80, "crypto-ready", "Abstraction layers exist, migration is planned"),
    (100, "crypto-agile", "Can swap algorithms with configuration changes"),
)


def _band(score: float) -> tuple[str, str]:
    for ceiling, label, description in _BAND_CEILINGS:
        if score <= ceiling:
            return label, description
    return _BAND_CEILINGS[-1][1], _BAND_CEILINGS[-1][2]


class AgilityAssetEvidence(BaseModel):
    evidence: str
    location: str


class CryptoAgilityInput(BaseModel):
    algorithm_assets: list[AgilityAssetEvidence] = Field(default_factory=list)
    library_names: list[str] = Field(default_factory=list)
    protocol_names: list[str] = Field(default_factory=list)


class AgilityFactorResult(BaseModel):
    factor: str
    label: str
    weight: float
    score: int
    explanation: str


class CryptoAgilityAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    band: str
    description: str
    factors: list[AgilityFactorResult]
    recommendations: list[str]


class CryptoAgilityEngine:
    def assess(self, value: CryptoAgilityInput) -> CryptoAgilityAssessment:
        assets = value.algorithm_assets
        if assets:
            abstraction = round(sum(_abstraction_score(a.evidence) for a in assets) / len(assets))
            hardcoding = round(
                sum(_hardcoding_score(a.evidence, a.location) for a in assets) / len(assets)
            )
            key_flex = round(sum(_key_flexibility_score(a.evidence) for a in assets) / len(assets))
        else:
            abstraction = hardcoding = key_flex = 0

        coupling = _coupling_score(len(set(value.library_names)))
        protocol = _protocol_score(set(value.protocol_names))

        factors = [
            AgilityFactorResult(
                factor="abstraction_layer_usage",
                label="Abstraction Layer Usage",
                weight=WEIGHTS["abstraction_layer_usage"],
                score=abstraction,
                explanation=(
                    "Crypto calls go through configurable providers (e.g. Web Crypto API, "
                    "env-driven getInstance)"
                    if abstraction >= 80
                    else "Some calls use factory methods (getInstance/createHash) with literal "
                    "algorithm names"
                    if abstraction >= 40
                    else "Most crypto calls construct algorithm classes directly, with no "
                    "abstraction layer"
                ),
            ),
            AgilityFactorResult(
                factor="algorithm_hardcoding",
                label="Algorithm Hardcoding",
                weight=WEIGHTS["algorithm_hardcoding"],
                score=hardcoding,
                explanation=(
                    "Algorithm choice is read from environment or settings at runtime"
                    if hardcoding >= 80
                    else "Algorithm choice lives in a config/deployment file, editable without "
                    "a code change"
                    if hardcoding >= 40
                    else "Algorithm names are hardcoded string literals inside application code"
                ),
            ),
            AgilityFactorResult(
                factor="dependency_coupling",
                label="Dependency Coupling",
                weight=WEIGHTS["dependency_coupling"],
                score=coupling,
                explanation=(
                    f"{len(set(value.library_names))} distinct cryptographic libraries in use "
                    f"across the estate"
                ),
            ),
            AgilityFactorResult(
                factor="key_management_flexibility",
                label="Key Management Flexibility",
                weight=WEIGHTS["key_management_flexibility"],
                score=key_flex,
                explanation=(
                    "Key sizes are sourced from configuration, not hardcoded"
                    if key_flex >= 80
                    else "Key sizes are mostly hardcoded numeric literals in constructor calls"
                    if key_flex <= 40
                    else "Key size configurability is mixed"
                ),
            ),
            AgilityFactorResult(
                factor="protocol_version_support",
                label="Protocol Version Support",
                weight=WEIGHTS["protocol_version_support"],
                score=protocol,
                explanation=(
                    f"{len(set(value.protocol_names))} distinct TLS protocol version(s) "
                    f"discovered: {', '.join(sorted(set(value.protocol_names))) or 'none'}"
                ),
            ),
        ]
        weighted_score = sum(factor.score * factor.weight for factor in factors)
        score = round(weighted_score)
        label, description = _band(score)
        return CryptoAgilityAssessment(
            score=score,
            band=label,
            description=description,
            factors=factors,
            recommendations=self._recommendations(factors),
        )

    @staticmethod
    def _recommendations(factors: list[AgilityFactorResult]) -> list[str]:
        tips = {
            "abstraction_layer_usage": (
                "Route cryptographic calls through a provider abstraction "
                "(e.g. a Web Crypto API-style interface) instead of instantiating "
                "algorithm classes directly."
            ),
            "algorithm_hardcoding": (
                "Move algorithm names out of source code into environment variables "
                "or a settings module so they can change without a redeploy."
            ),
            "dependency_coupling": (
                "Standardize on fewer, well-maintained crypto libraries with a thin "
                "wrapper layer so a future swap touches one place, not every call site."
            ),
            "key_management_flexibility": (
                "Parameterize key sizes and curve names instead of hardcoding numeric "
                "literals in constructor calls."
            ),
            "protocol_version_support": (
                "Add support for a second TLS version (or a PQC hybrid mode) so the "
                "estate is not locked to a single protocol negotiation path."
            ),
        }
        return [tips[factor.factor] for factor in sorted(factors, key=lambda f: f.score)[:3]]
