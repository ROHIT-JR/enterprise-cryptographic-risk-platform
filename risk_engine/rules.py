from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlgorithmProfile:
    points: int
    reason: str
    rule_id: str


ALGORITHM_PROFILES: tuple[tuple[tuple[str, ...], AlgorithmProfile], ...] = (
    (
        ("3DES", "TRIPLEDES", "DESEDE"),
        AlgorithmProfile(65, "Deprecated 3DES provides an inadequate security margin", "ALG-3DES"),
    ),
    (("DES",), AlgorithmProfile(75, "DES is deprecated and computationally breakable", "ALG-DES")),
    (
        ("RSA-1024",),
        AlgorithmProfile(
            75, "RSA-1024 is below accepted classical security levels", "ALG-RSA-1024"
        ),
    ),
    (
        ("RSA",),
        AlgorithmProfile(
            55, "RSA is vulnerable to cryptographically relevant quantum computers", "ALG-RSA-Q"
        ),
    ),
    (
        ("ECC", "ECDSA", "ECDH", "P-256", "SECP"),
        AlgorithmProfile(50, "Elliptic-curve cryptography is quantum-vulnerable", "ALG-ECC-Q"),
    ),
    (
        ("DIFFIE-HELLMAN", "DH"),
        AlgorithmProfile(50, "Classical Diffie-Hellman is quantum-vulnerable", "ALG-DH-Q"),
    ),
    (
        ("SHA-1", "SHA1"),
        AlgorithmProfile(55, "SHA-1 has practical collision attacks and is deprecated", "ALG-SHA1"),
    ),
    (("MD5",), AlgorithmProfile(70, "MD5 is cryptographically broken", "ALG-MD5")),
    (
        ("RC4", "ARC4", "ARCFOUR"),
        AlgorithmProfile(90, "RC4 is classically broken and deprecated by RFC 7465", "ALG-RC4"),
    ),
    (
        ("HARDCODED KEY",),
        AlgorithmProfile(
            85, "A cryptographic secret is hardcoded directly in source code", "ALG-HARDCODED-KEY"
        ),
    ),
    (
        ("TLSV1", "TLS1.0", "TLS 1.0"),
        AlgorithmProfile(65, "TLS 1.0 is deprecated", "PROTOCOL-TLS10"),
    ),
    (
        ("TLSV1.1", "TLS1.1", "TLS 1.1"),
        AlgorithmProfile(55, "TLS 1.1 is deprecated", "PROTOCOL-TLS11"),
    ),
    (
        ("AES-128",),
        AlgorithmProfile(
            15,
            "AES-128 has reduced security margin under Grover-style quantum search",
            "ALG-AES128",
        ),
    ),
    (
        ("AES",),
        AlgorithmProfile(
            8, "AES remains suitable when configured with strong key sizes and modes", "ALG-AES"
        ),
    ),
    (
        ("CHACHA20",),
        AlgorithmProfile(
            5, "ChaCha20-Poly1305 has no known practical quantum break", "ALG-CHACHA20"
        ),
    ),
    (
        ("SHA-256", "SHA-384", "SHA-512", "SHA-3", "HMAC"),
        AlgorithmProfile(
            5, "Modern hash or MAC construction with no known practical break", "ALG-MODERN-HASH"
        ),
    ),
    (
        ("TLSV1.3", "TLS1.3", "TLS 1.3"),
        AlgorithmProfile(5, "TLS 1.3 is the preferred deployed TLS protocol", "PROTOCOL-TLS13"),
    ),
    (
        ("TLSV1.2", "TLS1.2", "TLS 1.2"),
        AlgorithmProfile(
            15, "TLS 1.2 security depends on cipher-suite configuration", "PROTOCOL-TLS12"
        ),
    ),
)


CRITICALITY_POINTS = {
    "low": 0,
    "medium": 10,
    "high": 20,
    "critical": 25,
}
