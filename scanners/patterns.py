from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionPattern:
    name: str
    asset_type: str
    expression: re.Pattern[str]
    confidence: float
    algorithm: str | None = None


def _compile(value: str) -> re.Pattern[str]:
    return re.compile(value, re.IGNORECASE)


ALGORITHM_PATTERNS = (
    DetectionPattern(
        "3DES",
        "algorithm",
        _compile(r"\b(?:3DES|TripleDES|DESede|des3)\b"),
        0.95,
        "3DES",
    ),
    DetectionPattern(
        "RSA",
        "algorithm",
        _compile(
            r"\b(?:RSA(?:\.generate|\.new|_generate|EncryptionPadding|/ECB)|rsa\.generate_private_key|getInstance\s*\(\s*[\"']RSA)"
        ),
        0.96,
        "RSA",
    ),
    DetectionPattern(
        "ECC",
        "algorithm",
        _compile(r"\b(?:ECDSA|ECDH|secp256r1|prime256v1|P-256|ec\.generate_private_key)\b"),
        0.93,
        "ECC",
    ),
    DetectionPattern(
        "AES",
        "algorithm",
        _compile(
            r"\b(?:AES(?:[-_/ ]?(?:128|192|256))?|AES\.new|EVP_aes_|getInstance\s*\(\s*[\"']AES)\b"
        ),
        0.96,
        "AES",
    ),
    DetectionPattern(
        "DES",
        "algorithm",
        _compile(r"\b(?:DES\.new|EVP_des_|getInstance\s*\(\s*[\"']DES[\"'/])"),
        0.96,
        "DES",
    ),
    DetectionPattern(
        "SHA-1",
        "algorithm",
        _compile(r"\b(?:SHA[-_ ]?1|sha1\s*\(|EVP_sha1)\b"),
        0.97,
        "SHA-1",
    ),
    DetectionPattern(
        "SHA-256",
        "algorithm",
        _compile(r"\b(?:SHA[-_ ]?256|sha256\s*\(|EVP_sha256)\b"),
        0.97,
        "SHA-256",
    ),
    DetectionPattern(
        "SHA-384",
        "algorithm",
        _compile(r"\b(?:SHA[-_ ]?384|sha384\s*\(|EVP_sha384)\b"),
        0.97,
        "SHA-384",
    ),
    DetectionPattern(
        "SHA-512",
        "algorithm",
        _compile(r"\b(?:SHA[-_ ]?512|sha512\s*\(|EVP_sha512)\b"),
        0.97,
        "SHA-512",
    ),
    DetectionPattern(
        "SHA-3",
        "algorithm",
        _compile(r"\b(?:SHA3[-_ ]?(?:224|256|384|512)?|sha3_(?:224|256|384|512))\b"),
        0.96,
        "SHA-3",
    ),
    DetectionPattern(
        "Diffie-Hellman",
        "algorithm",
        _compile(r"\b(?:Diffie[- ]?Hellman|DH_generate_key|KeyAgreement.*[\"']DH)\b"),
        0.93,
        "Diffie-Hellman",
    ),
    DetectionPattern(
        "HMAC",
        "algorithm",
        _compile(r"\b(?:HMAC|hmac\.new|createHmac|HmacSHA(?:1|256|384|512))\b"),
        0.96,
        "HMAC",
    ),
)


LIBRARY_PATTERNS = (
    DetectionPattern(
        "OpenSSL",
        "library",
        _compile(r"\b(?:OpenSSL|openssl/|<openssl/|libssl|libcrypto)\b"),
        0.95,
    ),
    DetectionPattern(
        "Bouncy Castle",
        "library",
        _compile(r"\b(?:BouncyCastle|bouncycastle|org\.bouncycastle)\b"),
        0.98,
    ),
    DetectionPattern(
        "Crypto++",
        "library",
        _compile(r"\b(?:Crypto\+\+|cryptopp|CryptoPP)\b"),
        0.98,
    ),
    DetectionPattern(
        "libsodium",
        "library",
        _compile(r"\b(?:libsodium|sodium\.h|sodium_init|PyNaCl)\b"),
        0.98,
    ),
    DetectionPattern(
        "Python cryptography",
        "library",
        _compile(r"\b(?:from|import)\s+cryptography\b|cryptography\.hazmat"),
        0.97,
    ),
    DetectionPattern(
        "PyCryptodome",
        "library",
        _compile(r"\b(?:from|import)\s+Crypto\b|pycryptodome"),
        0.96,
    ),
)


DEPENDENCY_LIBRARY_NAMES: dict[str, str] = {
    "cryptography": "Python cryptography",
    "pycryptodome": "PyCryptodome",
    "pycrypto": "PyCrypto",
    "pynacl": "libsodium",
    "openssl": "OpenSSL",
    "libssl": "OpenSSL",
    "bouncycastle": "Bouncy Castle",
    "cryptopp": "Crypto++",
    "libsodium": "libsodium",
}


def infer_algorithm_name(pattern: DetectionPattern, evidence: str) -> str:
    base = pattern.algorithm or pattern.name
    upper = evidence.upper().replace("_", "-").replace("/", "-")
    if base == "AES":
        for size in (256, 192, 128):
            if str(size) in upper:
                return f"AES-{size}"
    if base == "RSA":
        match = re.search(r"\b(1024|2048|3072|4096|8192)\b", upper)
        if match:
            return f"RSA-{match.group(1)}"
    return base
