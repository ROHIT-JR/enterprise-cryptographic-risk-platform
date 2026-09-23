"""Entry-point scanner discovery is opt-in: it runs code from any installed package, so
build_default_registry() must only call ScannerRegistry.discover() when the operator has
explicitly asked for it via ECDAT_ENABLE_SCANNER_DISCOVERY.
"""

from __future__ import annotations

from scanners.base import ScannerPlugin, ScanResult
from scanners.registry import ScannerRegistry, build_default_registry


class _ThirdPartyScanner(ScannerPlugin):
    source_type = "third-party-example"
    name = "Third-party example scanner"
    version = "0.1.0"

    async def scan(self, target, **options) -> ScanResult:  # pragma: no cover - not exercised
        return ScanResult(source=self.source_type, target=str(target))


class _FakeEntryPoint:
    name = "third_party_example"

    def load(self):
        return _ThirdPartyScanner


def test_discover_registers_every_plugin_in_the_entry_point_group(monkeypatch):
    monkeypatch.setattr(
        "scanners.registry.entry_points", lambda group: [_FakeEntryPoint()], raising=True
    )
    registry = ScannerRegistry()

    registry.discover()

    assert "third-party-example" in registry.available()


def test_discover_rejects_an_entry_point_that_is_not_a_scanner_plugin(monkeypatch):
    class _NotAPlugin:
        name = "not-a-plugin"

        def load(self):
            return dict  # any callable whose result is not a ScannerPlugin

    monkeypatch.setattr(
        "scanners.registry.entry_points", lambda group: [_NotAPlugin()], raising=True
    )
    registry = ScannerRegistry()

    try:
        registry.discover()
    except TypeError:
        pass
    else:
        raise AssertionError("expected discover() to reject a non-ScannerPlugin entry point")


def test_build_default_registry_does_not_discover_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(ScannerRegistry, "discover", lambda self, **kw: calls.append(kw))

    build_default_registry()

    assert calls == [], "discover() must be opt-in, not run on every registry build"


def test_build_default_registry_discovers_when_explicitly_enabled(monkeypatch):
    calls = []
    monkeypatch.setattr(ScannerRegistry, "discover", lambda self, **kw: calls.append(kw))

    build_default_registry(enable_discovery=True)

    assert len(calls) == 1
