"""Determine the cryptographic function performed by a discovered algorithm.

Resolves what an algorithm *does* (sign, key establishment, or both) 
to inform PQC selection. Returns both the identified functions and a 
classification confidence score.

Resolution order:
    1. Explicit ``use_case`` metadata (highest confidence)
    2. Asset type inference (e.g. certificate key usage)
    3. Algorithm name pattern matching
    4. Conservative fallback
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

KEY_ESTABLISHMENT = "key_establishment"
DIGITAL_SIGNATURE = "digital_signature"
DUAL_PUBLIC_KEY = "dual_public_key"
SYMMETRIC_CRYPTO = "symmetric_crypto"
HASH_CRYPTO = "hash_crypto"
UNKNOWN_FUNCTION = "unknown"

_USE_CASE_MAP: dict[str, list[str]] = {
    "encryption": [KEY_ESTABLISHMENT],
    "key_exchange": [KEY_ESTABLISHMENT],
    "key_encapsulation": [KEY_ESTABLISHMENT],
    "kem": [KEY_ESTABLISHMENT],
    "signing": [DIGITAL_SIGNATURE],
    "signature": [DIGITAL_SIGNATURE],
    "digital_signature": [DIGITAL_SIGNATURE],
    "authentication": [DIGITAL_SIGNATURE],
    "code_signing": [DIGITAL_SIGNATURE],
    "tls": [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE],
    "vpn": [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE],
    "ipsec": [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE],
}

_ALGORITHM_PATTERNS: list[tuple[str, list[str]]] = [
    (r"\bECDH\b", [KEY_ESTABLISHMENT]),
    (r"\bDIFFIE[- ]?HELLMAN\b|\bDH\b", [KEY_ESTABLISHMENT]),
    (r"\bML[- ]?KEM\b", [KEY_ESTABLISHMENT]),
    (r"\bECDSA\b", [DIGITAL_SIGNATURE]),
    (r"\bED(?:DSA|25519|448)\b", [DIGITAL_SIGNATURE]),
    (r"\bDSA\b", [DIGITAL_SIGNATURE]),
    (r"\bML[- ]?DSA\b", [DIGITAL_SIGNATURE]),
    (r"\bSLH[- ]?DSA\b", [DIGITAL_SIGNATURE]),
    (r"\bECC\b|\bP-256\b|\bSECP\b|\bCURVE25519\b", [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE]),
    (r"\bRSA\b", [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE]),
    (r"\bAES\b|\bCHACHA\b|\b3DES\b|\bCAMELLIA\b|\bBLOWFISH\b", [SYMMETRIC_CRYPTO]),
    (r"\bSHA[- ]?\d", [HASH_CRYPTO]),
    (r"\bBLAKE\b|\bMD5\b", [HASH_CRYPTO]),
    (r"\bHMAC\b", [HASH_CRYPTO]),
]


def classify_crypto_function(
    *,
    algorithm: str,
    use_case: str | None = None,
    asset_type: str | None = None,
) -> tuple[list[str], float]:
    """Return the cryptographic function(s) and confidence score (0.0-1.0)."""
    
    # 1. Explicit use-case takes highest priority
    if use_case:
        normalised = use_case.strip().lower().replace("-", "_").replace(" ", "_")
        mapped = _USE_CASE_MAP.get(normalised)
        if mapped:
            return mapped, 0.95

    # 2. Algorithm name pattern matching
    subject = algorithm.upper().replace("_", "-")
    detected_funcs = None
    for pattern, functions in _ALGORITHM_PATTERNS:
        if re.search(pattern, subject):
            detected_funcs = functions
            break

    if detected_funcs:
        # If it's explicitly symmetric or hash, we are highly confident
        if SYMMETRIC_CRYPTO in detected_funcs or HASH_CRYPTO in detected_funcs:
            return detected_funcs, 0.99
            
        # Refine ambiguous asymmetric keys using asset_type
        if len(detected_funcs) > 1 and asset_type:
            at = asset_type.lower()
            if at == "certificate":
                # A certificate could be both, but we are less confident without extendedKeyUsage
                return detected_funcs, 0.60
            if at == "protocol":
                return detected_funcs, 0.85
                
        # Known single function
        if len(detected_funcs) == 1:
            return detected_funcs, 0.90
            
        # Ambiguous dual function (e.g. "RSA" with no context)
        return detected_funcs, 0.50

    # 3. Asset-type heuristic fallback
    if asset_type:
        at = asset_type.lower()
        if at == "certificate":
            return [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE], 0.40
        if at == "protocol":
            return [KEY_ESTABLISHMENT, DIGITAL_SIGNATURE], 0.40

    logger.debug("Could not classify crypto function for algorithm=%s", algorithm)
    return [UNKNOWN_FUNCTION], 0.10
