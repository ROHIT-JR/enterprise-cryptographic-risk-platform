# Scanner development

A scanner finds cryptography in one kind of place (a repository, a container image, a TLS
endpoint) and reports what it found in a common shape. Everything after that, including risk
scoring, the CBOM, the graph and migration planning, works on that shape and never needs to know
which scanner produced it. So adding a scanner is additive: you write one class.

- [The contract](#the-contract)
- [A complete example](#a-complete-example)
- [Registering your scanner](#registering-your-scanner)
- [Security checklist](#security-checklist)
- [Testing](#testing)

## The contract

Subclass `scanners.plugins.Scanner`, set three attributes, and implement one async method.

| Member | Purpose |
|---|---|
| `source_type` | A unique string naming the kind of target (`repository`, `docker`, `tls` are taken). |
| `name`, `version` | Human-readable identity, shown in health output. |
| `async scan(target, **options)` | Analyze the target and return a `ScanResult`. |
| `health()` | Optional. Return `{"status": "healthy", ...}`; the default is fine. |

A `ScanResult` carries what you found:

| Type | Fields you fill in |
|---|---|
| `DiscoveredAsset` | `asset_type` (`algorithm`, `library`, `certificate`, `protocol`, `application`, `configuration`), `name`, `algorithm`, `location`, `evidence`, `confidence` (0 to 1), optional `version`, `dependencies`, `details` |
| `DiscoveredRelationship` | `source_ref`, `target_ref`, `relationship_type` (`USES`, `CONTAINS`, `DEPENDS_ON`, `PROTECTS`), optional `evidence` |
| `ScanResult` | `source`, `target`, `assets`, `relationships`, `warnings`, `metadata` |

Every asset needs **evidence**: the literal thing you saw (a line of code, a certificate field), and
a **location** an analyst can go and look at. Findings are identified by a fingerprint of type,
name, location and evidence, so the same finding on a re-scan is recognized as the same asset.

## A complete example

This scanner walks a directory of PEM files, reads each X.509 certificate, and reports its public
key algorithm. It is deliberately small but follows every rule in the [checklist](#security-checklist):
it validates its target first, bounds what it reads, and treats every file as untrusted.

<!-- scanner-example -->
```python
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from scanners.base import DiscoveredAsset, ScanResult
from scanners.plugins import Scanner

MAX_FILES = 500
MAX_BYTES = 256 * 1024


class PemCertificateScanner(Scanner):
    source_type = "pem-directory"
    name = "PEM certificate scanner"
    version = "1.0.0"

    async def scan(self, target, **options) -> ScanResult:
        root = Path(target).resolve()
        if not root.is_dir():  # validate the target before touching anything
            raise ValueError("target must be a directory")

        result = ScanResult(source=str(self.source_type), target=str(root))
        for path in sorted(root.rglob("*.pem"))[:MAX_FILES]:  # bound how much we read
            if path.is_symlink() or path.stat().st_size > MAX_BYTES:
                result.warnings.append(f"{path.name}: skipped (symlink or too large)")
                continue
            try:
                certificate = x509.load_pem_x509_certificate(path.read_bytes())
            except ValueError:  # untrusted input: a bad file is a warning, not a crash
                result.warnings.append(f"{path.name}: not a certificate")
                continue

            key = certificate.public_key()
            if isinstance(key, rsa.RSAPublicKey):
                algorithm = f"RSA-{key.key_size}"
            elif isinstance(key, ec.EllipticCurvePublicKey):
                algorithm = f"ECC {key.curve.name}"
            else:
                algorithm = type(key).__name__
            signature = getattr(certificate.signature_hash_algorithm, "name", "none")

            result.assets.append(
                DiscoveredAsset(
                    asset_type="certificate",
                    name=certificate.subject.rfc4514_string() or path.name,
                    algorithm=algorithm,
                    location=str(path.relative_to(root)),
                    evidence=f"{algorithm} public key, signed with {signature}",
                    confidence=0.99,
                    details={"not_valid_after": certificate.not_valid_after_utc.isoformat()},
                )
            )
        return result
```

## Registering your scanner

Scanners are registered by source type, and the registry refuses a duplicate. To make a scanner
part of the application:

1. Put the class in the `scanners/` package.
2. Add it to the list in `build_default_registry()` in `scanners/registry.py`. The scan
   orchestrator looks a scan's `source_type` up in that registry, so from then on a scan with that
   source type is scanned by your class and flows through risk scoring, the CBOM and the graph
   unchanged.
3. Give users a way to start one. Scans are started by endpoints in `backend/app/api/upload.py`, one
   per source (`/scans/repository`, `/docker`, `/tls`). Copy `scan_tls`: add a request model,
   create the scan with `source_type="pem-directory"`, and queue `run_scan_job`. Gate it with
   `require_permissions(Permission.RUN_SCANS)` and give it a docstring; the
   [API docs tests](development.md#adding-an-api-endpoint) enforce both.

**Known gap: entry-point plugins are not loaded yet.** `ScannerRegistry.discover()` can load
scanners published under the `ecdat_x.scanners` entry-point group, but the application never calls
it, so a scanner installed from a separate package is not picked up. Until that is wired in,
register scanners in `build_default_registry()` as above. Wiring it in is a deliberate decision
for the maintainers because it means running code from any installed package.

## Security checklist

Scanners read attacker-influenced input (someone else's repository, image or server), so treat
every target and every file as hostile.

- **Validate the target first**, before opening, connecting or running anything.
- **Never use a shell.** Do not build command strings; pass argument lists to `subprocess` if you
  must run a program at all.
- **Bound everything:** time, number of files, file size, output size, recursion depth, and network
  reach. The built-in scanners take their limits from settings (`ECDAT_MAX_ARCHIVE_FILES`,
  `ECDAT_SCANNER_TIMEOUT_SECONDS`, and so on).
- **Do not follow symlinks** out of the target, and reject path traversal.
- **Never return secrets.** If you find a key or password, report that one exists and where, not its
  value.
- **A bad input is a warning, not an exception.** Add to `result.warnings` and carry on; raise only
  if the target itself is unusable.
- **Set `confidence` honestly.** A regex hit on a variable name is not the same as a parsed
  certificate.

## Testing

Test a scanner against adversarial input as well as the happy path. The example above is exercised
by `tests/test_scanner_guide.py`, which runs the code in this page, so it cannot drift from the
real contract. That test shows the pattern:

- feed it real fixtures (generate certificates in the test rather than committing them),
- feed it garbage, an oversized file, a symlink, and a target that is not a directory,
- check the registry rejects a duplicate `source_type`, and
- run a scan through the real pipeline and assert the asset lands in the inventory with a risk
  finding.
