import copy
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api import benchmarks as benchmarks_api
from backend.app.auth.service import AuthenticationService
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import AuditLog
from backend.app.schemas.auth import RegisterRequest
from benchmarks import pqc_benchmarks

# Generated per run so no credential-shaped literal lives in the repo (secret scanners flag them).
PASSWORD = secrets.token_urlsafe(24)


@pytest.fixture
def reference():
    return pqc_benchmarks.load_reference()


@pytest.fixture(autouse=True)
def reset_latest_runs():
    benchmarks_api._latest_runs.clear()
    yield
    benchmarks_api._latest_runs.clear()


def _token(org: str = "Bench Org", username: str = "bench-admin") -> str:
    with SessionLocal() as db:
        return (
            AuthenticationService()
            .register(
                db,
                RegisterRequest(
                    organization_name=org,
                    industry="Technology",
                    username=username,
                    email=f"{username}@example.test",
                    password=PASSWORD,
                ),
            )
            .access_token
        )


# --- reference data ---------------------------------------------------------------------
def test_reference_sizes_match_fips_203_and_204(reference):
    a = reference["algorithms"]
    assert (
        a["ML-KEM-768"]["pk_bytes"],
        a["ML-KEM-768"]["sk_bytes"],
        a["ML-KEM-768"]["ct_bytes"],
    ) == (
        1184,
        2400,
        1088,
    )
    assert (
        a["ML-KEM-1024"]["pk_bytes"],
        a["ML-KEM-1024"]["sk_bytes"],
        a["ML-KEM-1024"]["ct_bytes"],
    ) == (
        1568,
        3168,
        1568,
    )
    assert (
        a["ML-DSA-65"]["pk_bytes"],
        a["ML-DSA-65"]["sk_bytes"],
        a["ML-DSA-65"]["sig_bytes"],
    ) == (
        1952,
        4032,
        3309,
    )
    assert (
        a["ML-DSA-87"]["pk_bytes"],
        a["ML-DSA-87"]["sk_bytes"],
        a["ML-DSA-87"]["sig_bytes"],
    ) == (
        2592,
        4896,
        4627,
    )


def test_reference_sizes_for_ml_kem_512_and_slh_dsa_match_fips(reference):
    a = reference["algorithms"]
    assert (
        a["ML-KEM-512"]["pk_bytes"],
        a["ML-KEM-512"]["sk_bytes"],
        a["ML-KEM-512"]["ct_bytes"],
    ) == (
        800,
        1632,
        768,
    )
    slh = a["SLH-DSA-SHA2-128f"]
    assert (slh["pk_bytes"], slh["sk_bytes"], slh["sig_bytes"]) == (32, 64, 17088)  # FIPS 205


def test_reference_covers_issue_algorithms_with_complete_fields(reference):
    algorithms = reference["algorithms"]
    assert {
        "ML-KEM-768",
        "ML-KEM-1024",
        "ML-DSA-65",
        "ML-DSA-87",
        "RSA-2048",
        "RSA-4096",
        "ECDSA-P256",
        "ECDH-P256",
    } <= set(algorithms)
    for name, entry in algorithms.items():
        for key in (
            *pqc_benchmarks.TIMING_KEYS[entry["kind"]],
            *pqc_benchmarks.SIZE_KEYS[entry["kind"]],
        ):
            assert entry[key] > 0, f"{name}.{key}"
        assert entry["timing_source"] in reference["sources"], name
        assert entry["size_source"], name
        # every quantum-safe algorithm names its NIST category; classical ones never do
        assert (entry["nist_category"] is not None) == entry["quantum_safe"], name


# --- scoring ----------------------------------------------------------------------------
def test_scores_are_bounded_and_quantum_security_separates_pqc_from_classical(reference):
    rows = {row["name"]: row for row in pqc_benchmarks.score_algorithms(reference)}
    for row in rows.values():
        assert set(row["scores"]) == {"speed", "compactness", "maturity", "quantum_security"}
        assert all(0 <= value <= 100 for value in row["scores"].values()), row["name"]
    for classical in ("RSA-2048", "RSA-4096", "ECDSA-P256", "ECDH-P256"):
        assert rows[classical]["scores"]["quantum_security"] == 0
    assert rows["ML-KEM-768"]["scores"]["quantum_security"] == 60
    assert rows["ML-KEM-1024"]["scores"]["quantum_security"] == 100
    # fastest and slowest handshake operations anchor the log scale
    assert max(r["scores"]["speed"] for r in rows.values()) == 100
    assert min(r["scores"]["speed"] for r in rows.values()) == 0
    assert rows["RSA-2048"]["scores"]["maturity"] > rows["ML-KEM-768"]["scores"]["maturity"]


# --- migration impact -------------------------------------------------------------------
def test_migration_impact_matches_hand_calculation(reference):
    a = reference["algorithms"]
    overhead = reference["tls_model"]["cert_overhead_bytes"]
    result = pqc_benchmarks.migration_impact(
        reference, "ECDH-P256", "ML-KEM-768", "ECDSA-P256", "ML-DSA-65", chain_certs=1
    )
    before, after = result["before"], result["after"]

    kem, sig = a["ML-KEM-768"], a["ML-DSA-65"]
    assert after["total_cpu_us"] == (
        kem["keygen_us"]
        + kem["decaps_us"]
        + kem["encaps_us"]
        + sig["sign_us"]
        + 2 * sig["verify_us"]  # one certificate signature + CertificateVerify
    )
    assert after["certificate_chain_bytes"] == sig["pk_bytes"] + sig["sig_bytes"] + overhead
    assert after["server_flight_bytes"] == (
        kem["ct_bytes"] + after["certificate_chain_bytes"] + sig["sig_bytes"]
    )
    assert after["total_bytes"] == kem["pk_bytes"] + after["server_flight_bytes"]
    assert result["delta"]["bytes"] == after["total_bytes"] - before["total_bytes"]
    assert result["delta"]["bytes"] > 0  # PQC costs bytes
    assert after["key_exchange_quantum_safe"] and after["authentication_quantum_safe"]
    assert not before["key_exchange_quantum_safe"] and not before["authentication_quantum_safe"]


def test_migration_impact_identity_and_congestion_window_flag(reference):
    same = pqc_benchmarks.migration_impact(
        reference, "ECDH-P256", "ECDH-P256", "RSA-2048", "RSA-2048"
    )
    assert same["delta"]["cpu_percent"] == 0 and same["delta"]["bytes"] == 0

    big = pqc_benchmarks.migration_impact(
        reference, "ECDH-P256", "ML-KEM-1024", "RSA-2048", "ML-DSA-87", chain_certs=4
    )
    assert big["after"]["exceeds_initial_cwnd"] is True
    assert big["before"]["exceeds_initial_cwnd"] is False


def test_migration_impact_supports_the_issue_example_rsa_2048_to_ml_kem_768(reference):
    """Issue #17: "if you migrate RSA-2048 -> ML-KEM-768 ..." (RSA as legacy key transport)."""
    a = reference["algorithms"]
    result = pqc_benchmarks.migration_impact(
        reference, "RSA-2048", "ML-KEM-768", "RSA-2048", "RSA-2048", chain_certs=2
    )
    before, after = result["before"], result["after"]
    assert before["key_exchange_mode"] == "rsa-key-transport"
    assert after["key_exchange_mode"] == "kem"

    rsa, kem = a["RSA-2048"], a["ML-KEM-768"]
    # key transport: client encrypts (public op), server decrypts (private op); no keygen
    assert before["client_cpu_us"] - after["client_cpu_us"] == (
        rsa["verify_us"] - (kem["keygen_us"] + kem["decaps_us"])
    )
    assert before["server_cpu_us"] - after["server_cpu_us"] == rsa["sign_us"] - kem["encaps_us"]
    assert before["client_flight_bytes"] == rsa["sig_bytes"]  # encrypted pre-master secret
    assert after["client_flight_bytes"] == kem["pk_bytes"]
    # only the key exchange changed, so the certificate chain is identical
    assert result["delta"]["certificate_chain_bytes"] == 0
    assert result["delta"]["bytes"] == ((kem["pk_bytes"] + kem["ct_bytes"]) - rsa["sig_bytes"])
    assert after["key_exchange_quantum_safe"] and not before["key_exchange_quantum_safe"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kex_to": "ML-KEM-9999"}, "unknown algorithm"),
        ({"kex_to": "ML-DSA-65"}, "cannot be used for key exchange"),
        ({"auth_to": "ML-KEM-768"}, "cannot be used for authentication"),
        ({"chain_certs": 0}, "chain_certs"),
        ({"chain_certs": pqc_benchmarks.MAX_CHAIN_CERTS + 1}, "chain_certs"),
    ],
)
def test_migration_impact_rejects_invalid_input(reference, kwargs, message):
    args = {
        "kex_from": "ECDH-P256",
        "kex_to": "ML-KEM-768",
        "auth_from": "RSA-2048",
        "auth_to": "ML-DSA-65",
        **kwargs,
    }
    with pytest.raises(ValueError, match=message):
        pqc_benchmarks.migration_impact(reference, **args)


# --- live measurement -------------------------------------------------------------------
def test_live_run_measures_classical_and_reports_pqc_as_skipped(reference, monkeypatch):
    monkeypatch.setattr(pqc_benchmarks, "_load_oqs", lambda: None)
    result = pqc_benchmarks.run_benchmark(reference, iterations=1)

    assert set(result["measured"]) == {"RSA-2048", "RSA-4096", "ECDSA-P256", "ECDH-P256"}
    for name, timings in result["measured"].items():
        assert all(value > 0 for value in timings.values()), name
    # RSA private-key operations are far slower than verification
    assert result["measured"]["RSA-2048"]["sign_us"] > result["measured"]["RSA-2048"]["verify_us"]
    assert set(result["skipped"]) == {
        "ML-KEM-512",
        "ML-KEM-768",
        "ML-KEM-1024",
        "ML-DSA-65",
        "ML-DSA-87",
        "SLH-DSA-SHA2-128f",
    }
    assert all("not installed" in reason for reason in result["skipped"].values())
    assert result["environment"]["oqs_available"] is False


def test_live_run_uses_liboqs_when_available(reference, monkeypatch):
    class FakeKEM:
        def __init__(self, mechanism):
            self.mechanism = mechanism

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def generate_keypair(self):
            return b"pk"

        def encap_secret(self, public):
            return b"ct", b"ss"

        def decap_secret(self, ciphertext):
            return b"ss"

    class FakeSig(FakeKEM):
        def sign(self, message):
            return b"sig"

        def verify(self, message, signature, public):
            return True

    class FakeOqs:
        KeyEncapsulation = FakeKEM
        Signature = FakeSig

        @staticmethod
        def get_enabled_kem_mechanisms():
            return ["Kyber768", "ML-KEM-1024"]  # ML-KEM-768 only under its legacy name

        @staticmethod
        def get_enabled_sig_mechanisms():
            return ["ML-DSA-65"]  # ML-DSA-87 not built in

    monkeypatch.setattr(pqc_benchmarks, "_load_oqs", lambda: FakeOqs)
    monkeypatch.setattr(pqc_benchmarks, "_measure_rsa", lambda bits, iterations: {"sign_us": 1.0})
    result = pqc_benchmarks.run_benchmark(reference, iterations=2)

    assert {"ML-KEM-768", "ML-KEM-1024", "ML-DSA-65"} <= set(result["measured"])
    assert set(result["measured"]["ML-KEM-768"]) == {"keygen_us", "encaps_us", "decaps_us"}
    assert set(result["measured"]["ML-DSA-65"]) == {"keygen_us", "sign_us", "verify_us"}
    not_built = "not enabled in this liboqs build"
    assert result["skipped"] == {
        "ML-KEM-512": not_built,
        "ML-DSA-87": not_built,
        "SLH-DSA-SHA2-128f": not_built,
    }
    assert result["environment"]["oqs_available"] is True


@pytest.mark.parametrize("iterations", [0, pqc_benchmarks.MAX_ITERATIONS + 1])
def test_live_run_rejects_out_of_range_iterations(reference, iterations):
    with pytest.raises(ValueError, match="iterations"):
        pqc_benchmarks.run_benchmark(reference, iterations=iterations)


# --- HTTP API ---------------------------------------------------------------------------
def test_api_requires_authentication():
    client = TestClient(app)
    for method, path in (
        ("get", "/api/v1/benchmarks/pqc"),
        ("post", "/api/v1/benchmarks/run"),
        ("get", "/api/v1/benchmarks/migration-impact"),
    ):
        assert getattr(client, method)(path).status_code == 401, path


def test_api_serves_reference_data_runs_benchmark_and_audits_it(monkeypatch):
    monkeypatch.setattr(pqc_benchmarks, "_load_oqs", lambda: None)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_token()}"}

    before = client.get("/api/v1/benchmarks/pqc", headers=headers)
    assert before.status_code == 200
    body = before.json()
    assert body["latest_run"] is None
    names = [row["name"] for row in body["algorithms"]]
    assert names[:3] == ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]
    assert all(row["measured_us"] is None for row in body["algorithms"])
    assert body["sources"]["FIPS-203"]

    ran = client.post(
        "/api/v1/benchmarks/run", headers=headers, json={"iterations": 1, "include_pqc": False}
    )
    assert ran.status_code == 200
    run = ran.json()
    assert run["latest_run"]["iterations"] == 1
    measured = {row["name"]: row["measured_us"] for row in run["algorithms"]}
    assert measured["ECDSA-P256"]["sign_us"] > 0
    assert measured["ML-KEM-768"] is None  # PQC stays on reference data

    # the run is remembered for later GETs
    again = client.get("/api/v1/benchmarks/pqc", headers=headers).json()
    assert again["latest_run"]["started_at"] == run["latest_run"]["started_at"]

    with SessionLocal() as db:
        actions = db.scalars(select(AuditLog.action)).all()
    assert "benchmark.run" in actions


def test_api_latest_run_is_private_to_the_organisation_that_ran_it(monkeypatch):
    monkeypatch.setattr(pqc_benchmarks, "_load_oqs", lambda: None)
    client = TestClient(app)
    alpha = {"Authorization": f"Bearer {_token('Alpha Org', 'alpha-admin')}"}
    beta = {"Authorization": f"Bearer {_token('Beta Org', 'beta-admin')}"}

    ran = client.post(
        "/api/v1/benchmarks/run", headers=alpha, json={"iterations": 1, "include_pqc": False}
    )
    assert ran.status_code == 200 and ran.json()["latest_run"] is not None

    seen_by_beta = client.get("/api/v1/benchmarks/pqc", headers=beta).json()
    assert seen_by_beta["latest_run"] is None  # host details are not shared across tenants
    assert all(row["measured_us"] is None for row in seen_by_beta["algorithms"])
    assert client.get("/api/v1/benchmarks/pqc", headers=alpha).json()["latest_run"] is not None


def test_api_run_rejects_bad_iterations_and_concurrent_runs():
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_token()}"}
    assert (
        client.post("/api/v1/benchmarks/run", headers=headers, json={"iterations": 0}).status_code
        == 422
    )
    assert benchmarks_api._run_lock.acquire(blocking=False)
    try:
        busy = client.post("/api/v1/benchmarks/run", headers=headers, json={"iterations": 1})
    finally:
        benchmarks_api._run_lock.release()
    assert busy.status_code == 409


def test_api_migration_impact_defaults_and_validation():
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_token()}"}
    ok = client.get("/api/v1/benchmarks/migration-impact", headers=headers)
    assert ok.status_code == 200
    body = ok.json()
    assert body["before"]["key_exchange"] == "ECDH-P256"
    assert body["after"]["authentication"] == "ML-DSA-65"
    assert body["delta"]["certificate_chain_bytes"] > 0

    issue_example = client.get(
        "/api/v1/benchmarks/migration-impact",
        headers=headers,
        params={"kex_from": "RSA-2048", "kex_to": "ML-KEM-768"},
    )
    assert issue_example.status_code == 200
    assert issue_example.json()["before"]["key_exchange_mode"] == "rsa-key-transport"

    bad = client.get(
        "/api/v1/benchmarks/migration-impact", headers=headers, params={"kex_to": "ML-DSA-65"}
    )
    assert bad.status_code == 422
    assert "key exchange" in bad.json()["detail"]
    assert (
        client.get(
            "/api/v1/benchmarks/migration-impact", headers=headers, params={"chain_certs": 9}
        ).status_code
        == 422
    )


def test_reference_data_is_not_mutated_by_scoring(reference):
    snapshot = copy.deepcopy(reference)
    pqc_benchmarks.score_algorithms(reference)
    pqc_benchmarks.migration_impact(reference, "ECDH-P256", "ML-KEM-768", "RSA-2048", "ML-DSA-65")
    assert reference == snapshot
