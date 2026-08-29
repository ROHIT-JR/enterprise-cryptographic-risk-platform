from __future__ import annotations

from collections.abc import Iterable

from scanners.base import ScannerPlugin, ScanSource
from scanners.docker import DockerScanner
from scanners.source_scanner import SourceCodeScanner
from scanners.tls import TLSScanner


class ScannerRegistry:
    """Registry-based extension point for discovery plugins."""

    def __init__(self, plugins: Iterable[ScannerPlugin] = ()) -> None:
        self._plugins: dict[ScanSource, ScannerPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: ScannerPlugin) -> None:
        self._plugins[plugin.source_type] = plugin

    def get(self, source_type: ScanSource | str) -> ScannerPlugin:
        key = ScanSource(source_type)
        try:
            return self._plugins[key]
        except KeyError as exc:
            raise LookupError(f"No scanner registered for {key.value}") from exc

    def available(self) -> list[str]:
        return sorted(source.value for source in self._plugins)


def build_default_registry(
    *,
    docker_enabled: bool = True,
    timeout_seconds: int = 45,
    tls_timeout_seconds: float = 8,
    tls_allow_private_targets: bool = False,
) -> ScannerRegistry:
    return ScannerRegistry(
        [
            SourceCodeScanner(),
            DockerScanner(enabled=docker_enabled, timeout_seconds=timeout_seconds),
            TLSScanner(
                timeout_seconds=tls_timeout_seconds,
                allow_private_targets=tls_allow_private_targets,
            ),
        ]
    )
