from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from scanners.base import (
    DiscoveredAsset,
    DiscoveredRelationship,
    ScannerPlugin,
    ScanResult,
    ScanSource,
)
from scanners.docker_scanner import DockerfileAnalyzer
from scanners.exceptions import InvalidScanTargetError
from scanners.patterns import (
    ALGORITHM_PATTERNS,
    DEPENDENCY_LIBRARY_NAMES,
    LIBRARY_PATTERNS,
    infer_algorithm_name,
)

logger = logging.getLogger(__name__)

SOURCE_SUFFIXES = {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".c", ".cc", ".cpp", ".h", ".hpp"}
CONFIG_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".conf",
    ".properties",
    ".xml",
    ".gradle",
    ".pem",
    ".crt",
}
DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "conanfile.txt",
    "conanfile.py",
    "CMakeLists.txt",
}
IGNORED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    "__pycache__",
    "graphify-out",
}
LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
}


class RepositoryScanner(ScannerPlugin):
    name = "Source Code Cryptographic Discovery"
    version = "3.0.0"
    source_type = ScanSource.REPOSITORY

    def __init__(self, *, max_file_bytes: int = 2 * 1024 * 1024) -> None:
        self.max_file_bytes = max_file_bytes

    async def scan(self, target: str | Path, **options: Any) -> ScanResult:
        return await asyncio.to_thread(self.scan_directory, Path(target), **options)

    def scan_directory(self, target: str | Path, **options: Any) -> ScanResult:
        """Synchronous entry point for CLI use and deterministic unit tests."""

        return self._scan_sync(Path(target), options)

    def _scan_sync(self, root: Path, options: dict[str, Any]) -> ScanResult:
        root = root.resolve()
        if not root.is_dir():
            raise InvalidScanTargetError("Repository scan target must be a directory")

        display_name = str(options.get("display_name") or root.name)
        application = DiscoveredAsset(
            asset_type="application",
            name=display_name,
            location="/",
            evidence="Repository scan root",
            confidence=1.0,
            details={"source": "repository"},
        )
        assets: list[DiscoveredAsset] = [application]
        warnings: list[str] = []
        scanned_files = 0
        skipped_files = 0

        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(
                part in IGNORED_PARTS for part in path.relative_to(root).parts
            ):
                continue
            is_dockerfile = (
                path.name.lower() == "dockerfile" or path.suffix.lower() == ".dockerfile"
            )
            if (
                path.suffix.lower() not in SOURCE_SUFFIXES | CONFIG_SUFFIXES
                and path.name not in DEPENDENCY_FILES
                and not is_dockerfile
            ):
                continue
            try:
                if path.stat().st_size > self.max_file_bytes:
                    skipped_files += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("Unable to read %s: %s", path, exc)
                warnings.append(f"Could not read {path.relative_to(root)}")
                continue

            scanned_files += 1
            relative = path.relative_to(root).as_posix()
            assets.extend(self._scan_lines(relative, text))
            if is_dockerfile:
                assets.extend(DockerfileAnalyzer().analyze_text(text, location=relative))
            if path.name in DEPENDENCY_FILES:
                assets.extend(self._scan_dependencies(relative, text, path.name))

        assets = self._deduplicate(assets)
        relationships = self._relationships(application, assets)
        return ScanResult(
            source=self.source_type,
            target=display_name,
            assets=assets,
            relationships=relationships,
            metadata={
                "files_scanned": scanned_files,
                "files_skipped": skipped_files,
                "repository_root": display_name,
            },
            warnings=warnings,
        )

    def _scan_lines(self, relative: str, text: str) -> list[DiscoveredAsset]:
        findings: list[DiscoveredAsset] = []
        language = self._language(relative)
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            evidence = raw_line.strip()
            if not evidence or evidence.startswith(("//", "*")):
                continue
            if evidence.startswith("#") and not evidence.startswith("#include"):
                continue
            clipped = evidence[:240]
            for pattern in (*ALGORITHM_PATTERNS, *LIBRARY_PATTERNS):
                if not pattern.expression.search(evidence):
                    continue
                name = infer_algorithm_name(pattern, evidence)
                findings.append(
                    DiscoveredAsset(
                        asset_type=pattern.asset_type,
                        name=name,
                        algorithm=name
                        if pattern.asset_type in {"algorithm", "protocol"}
                        else None,
                        location=f"{relative}:{line_number}",
                        evidence=clipped,
                        confidence=pattern.confidence,
                        details={
                            "file": relative,
                            "line": line_number,
                            "language": language,
                            "detector": "pattern",
                        },
                    )
                )
        return findings

    def _scan_dependencies(self, relative: str, text: str, filename: str) -> list[DiscoveredAsset]:
        findings: list[DiscoveredAsset] = []
        normalized = text.lower()
        for token, library_name in DEPENDENCY_LIBRARY_NAMES.items():
            if not re.search(
                rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])",
                normalized,
            ):
                continue
            version = self._dependency_version(text, token, filename)
            findings.append(
                DiscoveredAsset(
                    asset_type="library",
                    name=library_name,
                    version=version,
                    location=relative,
                    evidence=f"Dependency declaration contains '{token}'",
                    confidence=0.99,
                    details={
                        "file": relative,
                        "language": self._language(relative),
                        "detector": "dependency-manifest",
                    },
                )
            )
        return findings

    @staticmethod
    def _language(relative: str) -> str:
        path = Path(relative)
        if path.name in {"requirements.txt", "pyproject.toml", "poetry.lock"}:
            return "python"
        if path.name in {"pom.xml", "build.gradle", "build.gradle.kts"}:
            return "java"
        if path.name in {"package.json", "package-lock.json"}:
            return "javascript"
        if path.name.startswith("conanfile") or path.name == "CMakeLists.txt":
            return "cpp"
        return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "configuration")

    @staticmethod
    def _dependency_version(text: str, token: str, filename: str) -> str | None:
        if filename == "package.json":
            try:
                payload = json.loads(text)
                for group in ("dependencies", "devDependencies", "optionalDependencies"):
                    for name, version in payload.get(group, {}).items():
                        if token in name.lower():
                            return str(version)
            except (json.JSONDecodeError, AttributeError):
                return None
        match = re.search(
            rf"{re.escape(token)}[^\n\r0-9]{{0,12}}([0-9]+(?:\.[0-9A-Za-z-]+)+)",
            text,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    @staticmethod
    def _deduplicate(assets: list[DiscoveredAsset]) -> list[DiscoveredAsset]:
        seen: set[tuple[str, str, str, str]] = set()
        result: list[DiscoveredAsset] = []
        for asset in assets:
            key = (asset.asset_type, asset.name, asset.location, asset.evidence)
            if key not in seen:
                seen.add(key)
                result.append(asset)
        return result

    @staticmethod
    def _relationships(
        application: DiscoveredAsset, assets: list[DiscoveredAsset]
    ) -> list[DiscoveredRelationship]:
        relationships: list[DiscoveredRelationship] = []
        by_file: dict[str, list[DiscoveredAsset]] = defaultdict(list)
        for asset in assets:
            if asset is application:
                continue
            relationships.append(
                DiscoveredRelationship(
                    source_ref=application.fingerprint(),
                    target_ref=asset.fingerprint(),
                    relationship_type="USES",
                    evidence=asset.location,
                )
            )
            by_file[asset.location.split(":", 1)[0]].append(asset)

        for file_assets in by_file.values():
            libraries = [asset for asset in file_assets if asset.asset_type == "library"]
            algorithms = [asset for asset in file_assets if asset.asset_type == "algorithm"]
            for library in libraries:
                for algorithm in algorithms:
                    relationships.append(
                        DiscoveredRelationship(
                            source_ref=library.fingerprint(),
                            target_ref=algorithm.fingerprint(),
                            relationship_type="CONTAINS",
                            evidence=f"Co-located in {algorithm.location.split(':', 1)[0]}",
                        )
                    )
        return relationships
