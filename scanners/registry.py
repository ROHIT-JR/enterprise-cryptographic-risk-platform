from __future__ import annotations

from collections.abc import Iterable
from importlib.metadata import entry_points

from scanners.base import ScannerPlugin, ScanSource
from scanners.docker import DockerScanner
from scanners.source_scanner import SourceCodeScanner
from scanners.tls import TLSScanner


class ScannerRegistry:
    """Registry-based extension point for discovery plugins."""

    def __init__(self, plugins: Iterable[ScannerPlugin] = ()) -> None:
        self._plugins: dict[str, ScannerPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: ScannerPlugin) -> None:
        key = str(plugin.source_type)
        if key in self._plugins:
            raise ValueError(f"Scanner source type already registered: {key}")
        self._plugins[key] = plugin

    def get(self, source_type: ScanSource | str) -> ScannerPlugin:
        key = str(source_type)
        try:
            return self._plugins[key]
        except KeyError as exc:
            raise LookupError(f"No scanner registered for {key}") from exc

    def available(self) -> list[str]:
        return sorted(self._plugins)

    def describe(self) -> list[dict[str, str]]:
        return [
            {
                "source_type": source,
                "name": plugin.name,
                "version": plugin.version,
                "status": plugin.health().get("status", "unknown"),
            }
            for source, plugin in sorted(self._plugins.items())
        ]

    def discover(self, group: str = "ecdat_x.scanners") -> None:
        for entry_point in entry_points(group=group):
            plugin = entry_point.load()()
            if not isinstance(plugin, ScannerPlugin):
                raise TypeError(
                    f"Scanner plugin {entry_point.name} does not implement ScannerPlugin"
                )
            self.register(plugin)


def build_default_registry(
    *,
    docker_enabled: bool = True,
    timeout_seconds: int = 45,
    tls_timeout_seconds: float = 8,
    tls_allow_private_targets: bool = False,
    enable_discovery: bool = False,
) -> ScannerRegistry:
    registry = ScannerRegistry(
        [
            SourceCodeScanner(),
            DockerScanner(enabled=docker_enabled, timeout_seconds=timeout_seconds),
            TLSScanner(
                timeout_seconds=tls_timeout_seconds,
                allow_private_targets=tls_allow_private_targets,
            ),
        ]
    )
    # Off by default: an entry-point scanner runs arbitrary code from any installed package,
    # so loading one is an explicit operator choice (ECDAT_ENABLE_SCANNER_DISCOVERY), not the
    # default behaviour of a fresh install.
    if enable_discovery:
        registry.discover()
    return registry
