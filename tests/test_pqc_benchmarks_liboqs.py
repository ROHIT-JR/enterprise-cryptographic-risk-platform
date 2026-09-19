"""Integration tests against the real liboqs library.

Skipped unless ``oqs`` (liboqs-python plus the native liboqs) is importable, so CI without liboqs
is unaffected. To run them: build liboqs, ``pip install liboqs-python``, then
``pytest tests/test_pqc_benchmarks_liboqs.py``.
"""

import secrets

import pytest

pytest.importorskip("oqs", reason="liboqs is not installed")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.api import benchmarks as benchmarks_api  # noqa: E402
from backend.app.auth.service import AuthenticationService  # noqa: E402
from backend.app.database import SessionLocal  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.schemas.auth import RegisterRequest  # noqa: E402
from benchmarks import pqc_benchmarks  # noqa: E402

PQC = ("ML-KEM-768", "ML-KEM-1024", "ML-DSA-65", "ML-DSA-87")


@pytest.fixture(scope="module")
def reference():
    return pqc_benchmarks.load_reference()


@pytest.fixture(scope="module")
def live_run(reference):
    return pqc_benchmarks.run_benchmark(reference, iterations=20)


def test_real_liboqs_measures_every_pqc_algorithm(live_run):
    assert live_run["environment"]["oqs_available"] is True
    assert live_run["skipped"] == {}
    for name in PQC:
        timings = live_run["measured"][name]
        expected = (
            {"keygen_us", "encaps_us", "decaps_us"}
            if name.startswith("ML-KEM")
            else {"keygen_us", "sign_us", "verify_us"}
        )
        assert set(timings) == expected, name
        assert all(value > 0 for value in timings.values()), name


def test_real_measurements_agree_with_reference_data_in_shape(live_run, reference):
    """The reference figures should describe the same world the real library shows."""
    measured, ref = live_run["measured"], reference["algorithms"]
    # lattice keygen is orders of magnitude faster than RSA keygen
    assert measured["ML-KEM-768"]["keygen_us"] * 100 < measured["RSA-2048"]["keygen_us"]
    # larger parameter sets cost more, as in the reference data
    assert measured["ML-KEM-1024"]["encaps_us"] > measured["ML-KEM-768"]["encaps_us"] * 0.8
    assert measured["ML-DSA-87"]["sign_us"] > measured["ML-DSA-65"]["sign_us"]
    # the derived ML-DSA-87 figures are ratios of ML-DSA-65 measured with real liboqs
    for op in ("keygen_us", "sign_us", "verify_us"):
        real_ratio = measured["ML-DSA-87"][op] / measured["ML-DSA-65"][op]
        ref_ratio = ref["ML-DSA-87"][op] / ref["ML-DSA-65"][op]
        assert ref_ratio == pytest.approx(real_ratio, rel=0.5), op


def test_api_run_reports_pqc_as_measured_when_liboqs_is_installed():
    benchmarks_api._latest_runs.clear()
    with SessionLocal() as db:
        token = (
            AuthenticationService()
            .register(
                db,
                RegisterRequest(
                    organization_name="Liboqs Org",
                    industry="Technology",
                    username="oqs-admin",
                    email="oqs-admin@example.test",
                    password=secrets.token_urlsafe(24),
                ),
            )
            .access_token
        )
    response = TestClient(app).post(
        "/api/v1/benchmarks/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"iterations": 3, "include_pqc": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latest_run"]["skipped"] == {}
    measured = {row["name"]: row["measured_us"] for row in body["algorithms"]}
    assert all(measured[name] is not None for name in PQC)
    benchmarks_api._latest_runs.clear()
