from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scanners.base import (
    DiscoveredAsset,
    DiscoveredRelationship,
    ScannerPlugin,
    ScanResult,
    ScanSource,
)
from scanners.exceptions import InvalidScanTargetError, ScannerError, ScannerUnavailableError

IMAGE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,254}$")
CRYPTO_PACKAGES = re.compile(
    r"(?:openssl|libssl|libcrypto|gnutls|libgcrypt|libsodium|nss|boringssl|wolfssl)",
    re.IGNORECASE,
)


class DockerScanner(ScannerPlugin):
    source_type = ScanSource.DOCKER

    def __init__(self, *, enabled: bool = True, timeout_seconds: int = 45) -> None:
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    async def scan(self, target: str | Path, **options: Any) -> ScanResult:
        return await asyncio.to_thread(self._scan_sync, str(target))

    def _scan_sync(self, image: str) -> ScanResult:
        image = image.strip()
        if not self.enabled:
            raise ScannerUnavailableError("Docker scanning is disabled by configuration")
        if not IMAGE_REFERENCE.fullmatch(image):
            raise InvalidScanTargetError("Docker image reference contains unsupported characters")
        if not shutil.which("docker"):
            raise ScannerUnavailableError("Docker CLI is not available to the backend")

        inspect = self._command(["docker", "image", "inspect", image], timeout=15)
        if inspect.returncode != 0:
            pull = self._command(["docker", "pull", image], timeout=max(60, self.timeout_seconds))
            if pull.returncode != 0:
                raise ScannerError(
                    f"Unable to inspect or pull image: {self._safe_error(pull.stderr)}"
                )
            inspect = self._command(["docker", "image", "inspect", image], timeout=15)
        if inspect.returncode != 0:
            raise ScannerError(f"Unable to inspect image: {self._safe_error(inspect.stderr)}")

        try:
            info = json.loads(inspect.stdout)[0]
        except (json.JSONDecodeError, IndexError, TypeError) as exc:
            raise ScannerError("Docker returned malformed image metadata") from exc

        container = DiscoveredAsset(
            asset_type="application",
            name=image,
            version=(info.get("Id") or "")[:19] or None,
            location=f"docker://{image}",
            evidence="Docker image metadata",
            confidence=1.0,
            details={
                "os": info.get("Os"),
                "architecture": info.get("Architecture"),
                "digest": (info.get("RepoDigests") or [None])[0],
            },
        )

        probe = self._command(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "256m",
                "--cpus",
                "0.5",
                "--entrypoint",
                "/bin/sh",
                image,
                "-c",
                _PROBE_SCRIPT,
            ],
            timeout=self.timeout_seconds,
        )

        assets = [container]
        warnings: list[str] = []
        if probe.returncode == 0:
            assets.extend(self._parse_probe(image, probe.stdout))
        else:
            warnings.append(
                "Runtime package probe was unavailable; results are limited to image metadata"
            )

        relationships = [
            DiscoveredRelationship(
                source_ref=container.fingerprint(),
                target_ref=asset.fingerprint(),
                relationship_type="CONTAINS",
                evidence="Discovered inside container image",
            )
            for asset in assets[1:]
        ]
        return ScanResult(
            source=self.source_type,
            target=image,
            assets=assets,
            relationships=relationships,
            metadata={
                "image_id": info.get("Id"),
                "repo_digests": info.get("RepoDigests") or [],
                "created": info.get("Created"),
                "os": info.get("Os"),
                "architecture": info.get("Architecture"),
            },
            warnings=warnings,
        )

    def _parse_probe(self, image: str, output: str) -> list[DiscoveredAsset]:
        assets: list[DiscoveredAsset] = []
        seen: set[tuple[str, str | None]] = set()
        for raw_line in output.splitlines():
            parts = raw_line.strip().split("|", 2)
            if len(parts) < 2:
                continue
            record_type = parts[0]
            if record_type == "OPENSSL":
                version_text = parts[1].strip()
                match = re.search(r"OpenSSL\s+([^\s]+)", version_text, re.IGNORECASE)
                version = match.group(1) if match else None
                key = ("OpenSSL", version)
                if key not in seen:
                    seen.add(key)
                    assets.append(
                        DiscoveredAsset(
                            asset_type="library",
                            name="OpenSSL",
                            version=version,
                            location=f"docker://{image}/usr/bin/openssl",
                            evidence=version_text[:240],
                            confidence=0.99,
                        )
                    )
            elif record_type == "PACKAGE" and len(parts) == 3:
                name, version = parts[1].strip(), parts[2].strip() or None
                if CRYPTO_PACKAGES.search(name) and (name, version) not in seen:
                    seen.add((name, version))
                    assets.append(
                        DiscoveredAsset(
                            asset_type="library",
                            name=name,
                            version=version,
                            location=f"docker://{image}/packages",
                            evidence=f"Installed package: {name} {version or ''}".strip(),
                            confidence=0.98,
                        )
                    )
            elif record_type == "CONFIG":
                path = parts[1].strip()
                assets.append(
                    DiscoveredAsset(
                        asset_type="configuration",
                        name=Path(path).name,
                        location=f"docker://{image}{path}",
                        evidence="Cryptographic configuration file",
                        confidence=0.85,
                    )
                )
        return assets

    @staticmethod
    def _command(args: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScannerError(f"Docker operation timed out after {timeout} seconds") from exc

    @staticmethod
    def _safe_error(value: str) -> str:
        return " ".join(value.strip().split())[:300] or "unknown Docker error"


_PROBE_SCRIPT = r"""
if command -v openssl >/dev/null 2>&1; then
  printf 'OPENSSL|%s\n' "$(openssl version 2>/dev/null)"
fi
if command -v dpkg-query >/dev/null 2>&1; then
  dpkg-query -W -f='PACKAGE|${binary:Package}|${Version}\n' 2>/dev/null | head -n 4000
elif command -v apk >/dev/null 2>&1; then
  apk info -v 2>/dev/null | sed -n '1,4000p' | sed -E 's/^(.+)-([0-9][^-]*)-r[0-9]+$/PACKAGE|\1|\2/'
elif command -v rpm >/dev/null 2>&1; then
  rpm -qa --qf 'PACKAGE|%{NAME}|%{VERSION}-%{RELEASE}\n' 2>/dev/null | head -n 4000
fi
find /etc -maxdepth 4 -type f \
  \( -iname 'openssl.cnf' -o -iname '*tls*.conf' -o -iname '*ssl*.conf' \) \
  2>/dev/null | head -n 100 | sed 's/^/CONFIG|/'
"""
