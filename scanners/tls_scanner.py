from scanners.tls import TLSScanner, normalize_cipher_name, parse_tls_endpoint


class TLSEndpointAnalyzer(TLSScanner):
    """Compatibility name for the Phase 1.5 TLS endpoint analyzer."""


__all__ = ["TLSScanner", "TLSEndpointAnalyzer", "normalize_cipher_name", "parse_tls_endpoint"]
