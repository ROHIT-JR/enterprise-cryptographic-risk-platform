"""PQC vs classical benchmark data, scoring, live measurement and TLS migration impact.

Reference numbers live in ``config/pqc_benchmarks.json``. Live measurement uses the
``cryptography`` package for classical algorithms and ``oqs`` (liboqs-python) for the
post-quantum ones when it is installed; without ``oqs`` the PQC rows simply stay on
reference data and the run reports them as skipped.
"""

from __future__ import annotations

import json
import math
import platform
import statistics
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "pqc_benchmarks.json"

MAX_ITERATIONS = 200
# RSA key generation is slow and highly variable; a handful of samples is enough.
RSA_KEYGEN_SAMPLES = {"RSA-2048": 3, "RSA-4096": 1}
MAX_CHAIN_CERTS = 4

TIMING_KEYS = {
    "kem": ("keygen_us", "encaps_us", "decaps_us"),
    "signature": ("keygen_us", "sign_us", "verify_us"),
}
SIZE_KEYS = {
    "kem": ("pk_bytes", "sk_bytes", "ct_bytes"),
    "signature": ("pk_bytes", "sk_bytes", "sig_bytes"),
}
# Score for a quantum-safe algorithm is its NIST security category scaled to 0-100.
QUANTUM_SCORE_PER_CATEGORY = 20
# Maturity: years since standardisation, 4 points each, capped at 100 (25 years).
MATURITY_POINTS_PER_YEAR = 4

OQS_ALIASES = {
    "ML-KEM-768": ("ML-KEM-768", "Kyber768"),
    "ML-KEM-1024": ("ML-KEM-1024", "Kyber1024"),
    "ML-DSA-65": ("ML-DSA-65", "Dilithium3"),
    "ML-DSA-87": ("ML-DSA-87", "Dilithium5"),
}
_MESSAGE = b"ECDAT-X benchmark message" * 4


def load_reference(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def handshake_ops_us(entry: dict[str, Any]) -> float:
    """CPU time of the operations a peer pair performs per handshake (keygen excluded)."""
    if entry["kind"] == "kem":
        return float(entry["encaps_us"] + entry["decaps_us"])
    return float(entry["sign_us"] + entry["verify_us"])


def wire_bytes(entry: dict[str, Any]) -> float:
    """Bytes that cross the wire for one use of the algorithm."""
    tail = entry["ct_bytes"] if entry["kind"] == "kem" else entry["sig_bytes"]
    return float(entry["pk_bytes"] + tail)


def _log_score(value: float, low: float, high: float) -> float:
    """100 for the smallest value in the set, 0 for the largest (log scale)."""
    if high <= low:
        return 100.0
    return round(
        100 * (math.log10(high) - math.log10(value)) / (math.log10(high) - math.log10(low)), 1
    )


def score_algorithms(reference: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the reference data into per-algorithm rows with 0-100 radar scores.

    speed and compactness are log-scaled relative to the other algorithms in the set
    (100 = best in set); maturity is years since standardisation; quantum_security is the
    NIST category for PQC algorithms and 0 for anything Shor's algorithm breaks.
    """
    algorithms = reference["algorithms"]
    year = reference["maturity_reference_year"]
    ops = {name: handshake_ops_us(entry) for name, entry in algorithms.items()}
    sizes = {name: wire_bytes(entry) for name, entry in algorithms.items()}
    ops_lo, ops_hi = min(ops.values()), max(ops.values())
    size_lo, size_hi = min(sizes.values()), max(sizes.values())

    rows: list[dict[str, Any]] = []
    for name, entry in algorithms.items():
        kind = entry["kind"]
        maturity = min(100, max(0, (year - entry["standard_year"]) * MATURITY_POINTS_PER_YEAR))
        quantum = (
            (entry["nist_category"] or 0) * QUANTUM_SCORE_PER_CATEGORY
            if entry["quantum_safe"]
            else 0
        )
        rows.append(
            {
                "name": name,
                "family": entry["family"],
                "kind": kind,
                "standard": entry["standard"],
                "standard_year": entry["standard_year"],
                "quantum_safe": entry["quantum_safe"],
                "nist_category": entry["nist_category"],
                "classical_security_bits": entry["classical_security_bits"],
                "timings_us": {key: entry[key] for key in TIMING_KEYS[kind]},
                "sizes_bytes": {key: entry[key] for key in SIZE_KEYS[kind]},
                "handshake_ops_us": ops[name],
                "wire_bytes": sizes[name],
                "timing_source": entry["timing_source"],
                "size_source": entry["size_source"],
                "scores": {
                    "speed": _log_score(ops[name], ops_lo, ops_hi),
                    "compactness": _log_score(sizes[name], size_lo, size_hi),
                    "maturity": float(maturity),
                    "quantum_security": float(quantum),
                },
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Live measurement
# ---------------------------------------------------------------------------
def _median_us(action: Callable[[], object], samples: int, warmup: int = 1) -> float:
    for _ in range(warmup):
        action()
    timings: list[float] = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        action()
        timings.append((time.perf_counter_ns() - started) / 1000)
    return round(statistics.median(timings), 2)


def _measure_rsa(bits: int, iterations: int) -> dict[str, float]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    name = f"RSA-{bits}"
    keygen_samples = min(iterations, RSA_KEYGEN_SAMPLES[name])
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    signature = key.sign(_MESSAGE, padding.PKCS1v15(), hashes.SHA256())
    public = key.public_key()
    return {
        "keygen_us": _median_us(
            lambda: rsa.generate_private_key(public_exponent=65537, key_size=bits),
            keygen_samples,
            warmup=0,
        ),
        "sign_us": _median_us(
            lambda: key.sign(_MESSAGE, padding.PKCS1v15(), hashes.SHA256()), iterations
        ),
        "verify_us": _median_us(
            lambda: public.verify(signature, _MESSAGE, padding.PKCS1v15(), hashes.SHA256()),
            iterations,
        ),
    }


def _measure_ecdsa(iterations: int) -> dict[str, float]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    scheme = ec.ECDSA(hashes.SHA256())
    signature = key.sign(_MESSAGE, scheme)
    public = key.public_key()
    return {
        "keygen_us": _median_us(lambda: ec.generate_private_key(ec.SECP256R1()), iterations),
        "sign_us": _median_us(lambda: key.sign(_MESSAGE, scheme), iterations),
        "verify_us": _median_us(lambda: public.verify(signature, _MESSAGE, scheme), iterations),
    }


def _measure_ecdh(iterations: int) -> dict[str, float]:
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    peer = ec.generate_private_key(ec.SECP256R1()).public_key()

    def encapsulate() -> object:
        ephemeral = ec.generate_private_key(ec.SECP256R1())
        return ephemeral.exchange(ec.ECDH(), peer)

    return {
        "keygen_us": _median_us(lambda: ec.generate_private_key(ec.SECP256R1()), iterations),
        "encaps_us": _median_us(encapsulate, iterations),
        "decaps_us": _median_us(lambda: key.exchange(ec.ECDH(), peer), iterations),
    }


def _load_oqs() -> Any | None:
    try:
        import oqs  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - a broken native library must not break the API
        return None
    return oqs


def _oqs_mechanism(name: str, enabled: list[str]) -> str | None:
    return next((alias for alias in OQS_ALIASES[name] if alias in enabled), None)


def _measure_oqs_kem(oqs: Any, mechanism: str, iterations: int) -> dict[str, float]:
    with oqs.KeyEncapsulation(mechanism) as client, oqs.KeyEncapsulation(mechanism) as server:
        public = client.generate_keypair()
        ciphertext, _ = server.encap_secret(public)
        # Decapsulate before the keygen loop: generate_keypair replaces the client's secret key.
        decaps_us = _median_us(lambda: client.decap_secret(ciphertext), iterations)
        return {
            "keygen_us": _median_us(client.generate_keypair, iterations),
            "encaps_us": _median_us(lambda: server.encap_secret(public), iterations),
            "decaps_us": decaps_us,
        }


def _measure_oqs_sig(oqs: Any, mechanism: str, iterations: int) -> dict[str, float]:
    with oqs.Signature(mechanism) as signer, oqs.Signature(mechanism) as verifier:
        public = signer.generate_keypair()
        signature = signer.sign(_MESSAGE)
        return {
            "keygen_us": _median_us(signer.generate_keypair, iterations),
            "sign_us": _median_us(lambda: signer.sign(_MESSAGE), iterations),
            "verify_us": _median_us(
                lambda: verifier.verify(_MESSAGE, signature, public), iterations
            ),
        }


def _environment(oqs: Any | None) -> dict[str, Any]:
    from importlib.metadata import PackageNotFoundError, version

    def package_version(name: str) -> str | None:
        try:
            return version(name)
        except PackageNotFoundError:
            return None

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cryptography": package_version("cryptography"),
        "liboqs_python": package_version("liboqs-python"),
        "oqs_available": oqs is not None,
    }


def run_benchmark(
    reference: dict[str, Any] | None = None,
    iterations: int = 20,
    include_pqc: bool = True,
) -> dict[str, Any]:
    """Measure what this host can measure and report the rest as skipped."""
    if not 1 <= iterations <= MAX_ITERATIONS:
        raise ValueError(f"iterations must be between 1 and {MAX_ITERATIONS}")
    reference = reference or load_reference()
    started = time.perf_counter()
    started_at = datetime.now(UTC)

    measured: dict[str, dict[str, float]] = {
        "RSA-2048": _measure_rsa(2048, iterations),
        "RSA-4096": _measure_rsa(4096, iterations),
        "ECDSA-P256": _measure_ecdsa(iterations),
        "ECDH-P256": _measure_ecdh(iterations),
    }
    skipped: dict[str, str] = {}

    oqs = _load_oqs() if include_pqc else None
    pqc_names = [name for name in reference["algorithms"] if name in OQS_ALIASES]
    if not include_pqc:
        skipped.update({name: "PQC measurement not requested" for name in pqc_names})
    elif oqs is None:
        skipped.update(
            {name: "liboqs (oqs) is not installed; showing reference data" for name in pqc_names}
        )
    else:
        kems = list(oqs.get_enabled_kem_mechanisms())
        sigs = list(oqs.get_enabled_sig_mechanisms())
        for name in pqc_names:
            kind = reference["algorithms"][name]["kind"]
            mechanism = _oqs_mechanism(name, kems if kind == "kem" else sigs)
            if mechanism is None:
                skipped[name] = "not enabled in this liboqs build"
                continue
            measure = _measure_oqs_kem if kind == "kem" else _measure_oqs_sig
            measured[name] = measure(oqs, mechanism, iterations)

    return {
        "started_at": started_at.isoformat(),
        "duration_s": round(time.perf_counter() - started, 2),
        "iterations": iterations,
        "environment": _environment(oqs),
        "measured": measured,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# TLS migration impact
# ---------------------------------------------------------------------------
def supports_key_exchange(entry: dict[str, Any]) -> bool:
    """KEMs, plus RSA used the legacy way (client encrypts the pre-master secret)."""
    return entry["kind"] == "kem" or entry["family"] == "RSA"


def _key_exchange_costs(entry: dict[str, Any]) -> dict[str, Any]:
    if entry["kind"] == "kem":
        return {
            "mode": "kem",
            "client_us": entry["keygen_us"] + entry["decaps_us"],
            "server_us": entry["encaps_us"],
            "client_bytes": entry["pk_bytes"],
            "server_bytes": entry["ct_bytes"],
        }
    # RSA key transport (TLS 1.2 style): the server's static key is already in its certificate,
    # so there is no key generation and no key share coming back. RSA's public operation costs
    # about a signature verification and its private operation about a signature.
    return {
        "mode": "rsa-key-transport",
        "client_us": entry["verify_us"],
        "server_us": entry["sign_us"],
        "client_bytes": entry["sig_bytes"],
        "server_bytes": 0,
    }


def _handshake_profile(
    reference: dict[str, Any], kex: str, auth: str, chain_certs: int
) -> dict[str, Any]:
    """Cost of one full server-authenticated TLS handshake.

    The chain is ``chain_certs`` certificates (leaf first, root not sent) all using the
    ``auth`` algorithm: the client verifies one issuer signature per certificate plus the
    server's CertificateVerify; the server produces one signature.
    """
    algorithms = reference["algorithms"]
    model = reference["tls_model"]
    key_exchange, authentication = algorithms[kex], algorithms[auth]
    exchange = _key_exchange_costs(key_exchange)

    client_us = exchange["client_us"] + authentication["verify_us"] * (chain_certs + 1)
    server_us = exchange["server_us"] + authentication["sign_us"]

    cert_bytes = chain_certs * (
        authentication["pk_bytes"] + authentication["sig_bytes"] + model["cert_overhead_bytes"]
    )
    client_flight = exchange["client_bytes"]
    server_flight = exchange["server_bytes"] + cert_bytes + authentication["sig_bytes"]
    return {
        "key_exchange": kex,
        "key_exchange_mode": exchange["mode"],
        "authentication": auth,
        "client_cpu_us": round(client_us, 2),
        "server_cpu_us": round(server_us, 2),
        "total_cpu_us": round(client_us + server_us, 2),
        "certificate_chain_bytes": cert_bytes,
        "client_flight_bytes": client_flight,
        "server_flight_bytes": server_flight,
        "total_bytes": client_flight + server_flight,
        "exceeds_initial_cwnd": server_flight > model["initial_congestion_window_bytes"],
        "key_exchange_quantum_safe": key_exchange["quantum_safe"],
        "authentication_quantum_safe": authentication["quantum_safe"],
    }


def _percent_change(before: float, after: float) -> float:
    return round((after - before) / before * 100, 1) if before else 0.0


def migration_impact(
    reference: dict[str, Any],
    kex_from: str,
    kex_to: str,
    auth_from: str,
    auth_to: str,
    chain_certs: int | None = None,
) -> dict[str, Any]:
    algorithms = reference["algorithms"]
    model = reference["tls_model"]
    chain_certs = model["default_chain_certs"] if chain_certs is None else chain_certs
    if not 1 <= chain_certs <= MAX_CHAIN_CERTS:
        raise ValueError(f"chain_certs must be between 1 and {MAX_CHAIN_CERTS}")
    for label, name, role in (
        ("kex_from", kex_from, "key exchange"),
        ("kex_to", kex_to, "key exchange"),
        ("auth_from", auth_from, "authentication"),
        ("auth_to", auth_to, "authentication"),
    ):
        entry = algorithms.get(name)
        if entry is None:
            raise ValueError(f"{label}: unknown algorithm {name!r}")
        usable = (
            supports_key_exchange(entry) if role == "key exchange" else entry["kind"] == "signature"
        )
        if not usable:
            raise ValueError(f"{label}: {name} cannot be used for {role}")

    before = _handshake_profile(reference, kex_from, auth_from, chain_certs)
    after = _handshake_profile(reference, kex_to, auth_to, chain_certs)
    return {
        "chain_certs": chain_certs,
        "assumptions": {
            "cert_overhead_bytes": model["cert_overhead_bytes"],
            "initial_congestion_window_bytes": model["initial_congestion_window_bytes"],
            "note": (
                "CPU time only (no network latency); every certificate in the chain uses the "
                "same signature algorithm; KEM keys are freshly generated per handshake. RSA "
                "key exchange means legacy key transport (TLS 1.2 style), not a TLS 1.3 option."
            ),
        },
        "before": before,
        "after": after,
        "delta": {
            "cpu_percent": _percent_change(before["total_cpu_us"], after["total_cpu_us"]),
            "cpu_us": round(after["total_cpu_us"] - before["total_cpu_us"], 2),
            "bytes": after["total_bytes"] - before["total_bytes"],
            "bytes_percent": _percent_change(before["total_bytes"], after["total_bytes"]),
            "certificate_chain_bytes": after["certificate_chain_bytes"]
            - before["certificate_chain_bytes"],
            "certificate_chain_percent": _percent_change(
                before["certificate_chain_bytes"], after["certificate_chain_bytes"]
            ),
        },
    }
