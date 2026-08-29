from __future__ import annotations

import re
from pathlib import Path

from scanners.base import DiscoveredAsset
from scanners.docker import DockerScanner

_FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(?P<image>\S+)", re.IGNORECASE)
_PACKAGE = re.compile(
    r"\b(?P<name>openssl|libssl(?:-dev)?|libcrypto(?:-dev)?|gnutls|libsodium|cryptopp)\b",
    re.IGNORECASE,
)
_PACKAGE_NAMES = {
    "openssl": "OpenSSL",
    "libssl": "OpenSSL",
    "libssl-dev": "OpenSSL",
    "libcrypto": "OpenSSL",
    "libcrypto-dev": "OpenSSL",
    "gnutls": "GnuTLS",
    "libsodium": "libsodium",
    "cryptopp": "Crypto++",
}


class DockerfileAnalyzer:
    """Statically discover base images and declared crypto packages in Dockerfiles."""

    def analyze_file(self, path: str | Path) -> list[DiscoveredAsset]:
        dockerfile = Path(path)
        return self.analyze_text(
            dockerfile.read_text(encoding="utf-8", errors="replace"),
            location=dockerfile.as_posix(),
        )

    def analyze_text(self, text: str, *, location: str = "Dockerfile") -> list[DiscoveredAsset]:
        assets: list[DiscoveredAsset] = []
        seen_packages: set[str] = set()
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            evidence = raw_line.strip()
            if not evidence or evidence.startswith("#"):
                continue
            base_match = _FROM.search(evidence)
            if base_match:
                image = base_match.group("image")
                assets.append(
                    DiscoveredAsset(
                        asset_type="application",
                        name=image,
                        version=_image_version(image),
                        location=f"{location}:{line_number}",
                        evidence=evidence[:240],
                        confidence=1.0,
                        details={
                            "language": "dockerfile",
                            "detector": "dockerfile-base-image",
                            "role": "base-image",
                        },
                    )
                )
            for match in _PACKAGE.finditer(evidence):
                token = match.group("name").lower()
                name = _PACKAGE_NAMES[token]
                if name in seen_packages:
                    continue
                seen_packages.add(name)
                assets.append(
                    DiscoveredAsset(
                        asset_type="library",
                        name=name,
                        version="unknown",
                        location=f"{location}:{line_number}",
                        evidence=evidence[:240],
                        confidence=0.95,
                        details={
                            "language": "dockerfile",
                            "detector": "dockerfile-package",
                        },
                    )
                )
        return assets


def _image_version(image: str) -> str | None:
    if "@" in image:
        return image.split("@", 1)[1]
    final_segment = image.rsplit("/", 1)[-1]
    return final_segment.rsplit(":", 1)[1] if ":" in final_segment else None


__all__ = ["DockerScanner", "DockerfileAnalyzer"]
