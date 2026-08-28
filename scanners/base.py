from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ScanSource(StrEnum):
    REPOSITORY = "repository"
    DOCKER = "docker"
    TLS = "tls"


class DiscoveredAsset(BaseModel):
    asset_type: str
    name: str
    algorithm: str | None = None
    version: str | None = None
    location: str
    evidence: str
    confidence: float = Field(default=0.8, ge=0, le=1)
    dependencies: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    def fingerprint(self) -> str:
        material = "\x1f".join([self.asset_type, self.name, self.location, self.evidence]).encode(
            "utf-8", errors="replace"
        )
        return hashlib.sha256(material).hexdigest()[:24]


class DiscoveredRelationship(BaseModel):
    source_ref: str
    target_ref: str
    relationship_type: str
    evidence: str | None = None


class ScanResult(BaseModel):
    source: ScanSource
    target: str
    assets: list[DiscoveredAsset] = Field(default_factory=list)
    relationships: list[DiscoveredRelationship] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ScannerPlugin(ABC):
    source_type: ScanSource

    @abstractmethod
    async def scan(self, target: str | Path, **options: Any) -> ScanResult:
        """Analyze a target and return normalized discovery findings."""
