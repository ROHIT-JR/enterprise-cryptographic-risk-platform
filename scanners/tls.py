from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from scanners.base import (
    DiscoveredAsset,
    DiscoveredRelationship,
    ScannerPlugin,
    ScanResult,
    ScanSource,
)
from scanners.exceptions import InvalidScanTargetError, ScannerError


class TLSScanner(ScannerPlugin):
    source_type = ScanSource.TLS

    def __init__(self, *, timeout_seconds: float = 8, allow_private_targets: bool = False) -> None:
        self.timeout_seconds = timeout_seconds
        self.allow_private_targets = allow_private_targets

    async def scan(self, target: str | Path, **options: Any) -> ScanResult:
        return await asyncio.to_thread(self._scan_sync, str(target))

    def _scan_sync(self, endpoint: str) -> ScanResult:
        host, port = parse_tls_endpoint(endpoint)
        addresses = self._resolve(host, port)
        selected_ip = addresses[0]

        verification_error: str | None = None
        try:
            connection = self._connect(host, selected_ip, port, verify=True)
        except ssl.SSLCertVerificationError as exc:
            verification_error = str(exc.verify_message or exc)[:240]
            connection = self._connect(host, selected_ip, port, verify=False)
        except (OSError, ssl.SSLError) as exc:
            raise ScannerError(f"TLS connection failed: {str(exc)[:240]}") from exc

        with connection as tls_socket:
            protocol = tls_socket.version() or "Unknown TLS"
            cipher_info = tls_socket.cipher()
            cipher = cipher_info[0] if cipher_info else "Unknown cipher"
            der_certificate = tls_socket.getpeercert(binary_form=True)

        if not der_certificate:
            raise ScannerError("The endpoint did not present a certificate")
        certificate = x509.load_der_x509_certificate(der_certificate)
        cert_asset, public_key_name = self._certificate_asset(
            host, port, certificate, verification_error
        )

        endpoint_asset = DiscoveredAsset(
            asset_type="application",
            name=f"{host}:{port}",
            location=f"tls://{host}:{port}",
            evidence=f"Resolved to {selected_ip}",
            confidence=1.0,
            details={"host": host, "port": port, "resolved_ip": selected_ip},
        )
        protocol_asset = DiscoveredAsset(
            asset_type="protocol",
            name=protocol,
            algorithm=protocol,
            location=f"tls://{host}:{port}",
            evidence=f"Negotiated protocol: {protocol}",
            confidence=1.0,
        )
        cipher_asset = DiscoveredAsset(
            asset_type="algorithm",
            name=normalize_cipher_name(cipher),
            algorithm=normalize_cipher_name(cipher),
            location=f"tls://{host}:{port}",
            evidence=f"Negotiated cipher suite: {cipher}",
            confidence=1.0,
            details={"cipher_suite": cipher},
        )
        key_asset = DiscoveredAsset(
            asset_type="algorithm",
            name=public_key_name,
            algorithm=public_key_name,
            location=f"tls://{host}:{port}/certificate",
            evidence=f"Certificate public key: {public_key_name}",
            confidence=1.0,
        )
        assets = [endpoint_asset, protocol_asset, cipher_asset, cert_asset, key_asset]
        relationships = [
            DiscoveredRelationship(
                source_ref=endpoint_asset.fingerprint(),
                target_ref=protocol_asset.fingerprint(),
                relationship_type="USES",
            ),
            DiscoveredRelationship(
                source_ref=protocol_asset.fingerprint(),
                target_ref=cipher_asset.fingerprint(),
                relationship_type="USES",
            ),
            DiscoveredRelationship(
                source_ref=cert_asset.fingerprint(),
                target_ref=endpoint_asset.fingerprint(),
                relationship_type="PROTECTS",
            ),
            DiscoveredRelationship(
                source_ref=cert_asset.fingerprint(),
                target_ref=key_asset.fingerprint(),
                relationship_type="CONTAINS",
            ),
        ]
        warnings = (
            [f"Certificate verification failed: {verification_error}"] if verification_error else []
        )
        return ScanResult(
            source=self.source_type,
            target=f"{host}:{port}",
            assets=assets,
            relationships=relationships,
            metadata={
                "host": host,
                "port": port,
                "resolved_ip": selected_ip,
                "protocol": protocol,
                "cipher_suite": cipher,
                "certificate_verified": verification_error is None,
            },
            warnings=warnings,
        )

    def _resolve(self, host: str, port: int) -> list[str]:
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise InvalidScanTargetError(f"Unable to resolve TLS host: {host}") from exc
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses:
            raise InvalidScanTargetError(f"Unable to resolve TLS host: {host}")
        if not self.allow_private_targets:
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if not ip.is_global:
                    raise InvalidScanTargetError(
                        "Private, loopback, link-local, and reserved TLS targets are disabled"
                    )
        return addresses

    def _connect(self, host: str, address: str, port: int, *, verify: bool) -> ssl.SSLSocket:
        context = ssl.create_default_context()
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        raw_socket = socket.create_connection((address, port), timeout=self.timeout_seconds)
        try:
            return context.wrap_socket(raw_socket, server_hostname=host)
        except Exception:
            raw_socket.close()
            raise

    @staticmethod
    def _certificate_asset(
        host: str,
        port: int,
        certificate: x509.Certificate,
        verification_error: str | None,
    ) -> tuple[DiscoveredAsset, str]:
        public_key = certificate.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key_name = f"RSA-{public_key.key_size}"
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key_name = f"ECC-{public_key.curve.name}"
        else:
            public_key_name = public_key.__class__.__name__.removesuffix("PublicKey")

        not_before = certificate.not_valid_before_utc
        not_after = certificate.not_valid_after_utc
        if not_before.tzinfo is None:
            not_before = not_before.replace(tzinfo=UTC)
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        status = "valid" if not_before <= now <= not_after else "expired-or-not-yet-valid"

        details = {
            "subject": certificate.subject.rfc4514_string(),
            "issuer": certificate.issuer.rfc4514_string(),
            "serial_number": format(certificate.serial_number, "x"),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "signature_algorithm": getattr(certificate.signature_hash_algorithm, "name", None),
            "public_key": public_key_name,
            "status": status,
            "verification_error": verification_error,
        }
        asset = DiscoveredAsset(
            asset_type="certificate",
            name=_certificate_common_name(certificate) or host,
            algorithm=public_key_name,
            location=f"tls://{host}:{port}/certificate",
            evidence=f"X.509 certificate issued by {details['issuer']}",
            confidence=1.0,
            details=details,
        )
        return asset, public_key_name


def parse_tls_endpoint(endpoint: str) -> tuple[str, int]:
    value = endpoint.strip()
    if not value:
        raise InvalidScanTargetError("TLS endpoint is required")
    if "://" not in value:
        value = f"tls://{value}"
    parsed = urlsplit(value)
    if parsed.scheme not in {"tls", "ssl", "https"} or not parsed.hostname:
        raise InvalidScanTargetError("Use a TLS endpoint such as example.com:443")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise InvalidScanTargetError("TLS endpoint port is invalid") from exc
    if not 1 <= port <= 65535:
        raise InvalidScanTargetError("TLS endpoint port must be between 1 and 65535")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise InvalidScanTargetError("TLS endpoint must not contain a path, query, or fragment")
    return parsed.hostname.rstrip("."), port


def normalize_cipher_name(cipher: str) -> str:
    upper = cipher.upper().replace("_", "-")
    if "CHACHA20" in upper:
        return "ChaCha20-Poly1305"
    if "AES" in upper:
        size = "256" if "256" in upper else "128" if "128" in upper else None
        mode = "GCM" if "GCM" in upper else "CCM" if "CCM" in upper else None
        return "-".join(part for part in ("AES", size, mode) if part)
    return cipher


def _certificate_common_name(certificate: x509.Certificate) -> str | None:
    attributes = certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    return attributes[0].value if attributes else None
