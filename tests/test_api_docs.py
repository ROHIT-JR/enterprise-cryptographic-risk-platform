import base64
import hashlib
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.assets import LifecycleTransitionBody
from backend.app.api.benchmarks import BenchmarkRunRequest
from backend.app.auth.service import AuthenticationService
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.openapi_docs import COMMON_RESPONSES, OPENAPI_TAGS
from backend.app.schemas.auth import (
    LoginRequest,
    OrganizationUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserCreate,
)
from backend.app.schemas.intelligence import BusinessContextUpdate
from backend.app.schemas.mosca import MoscaSimulateRequest
from backend.app.schemas.project import ProjectCreate
from backend.app.schemas.scan import DockerScanRequest, ScanResponse, TLSScanRequest
from backend.app.security import RateLimitMiddleware
from backend.app.seed import seed_securebank_demo
from lifecycle_engine import LifecycleState

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
# No bearer token needed: register/login/refresh document their own 401s, and /health is
# outside the rate limiter.
PUBLIC_PATHS = {"/health", "/health/full", "/api/v1/auth/register", "/api/v1/auth/login"}
RATE_LIMIT_EXEMPT = {"/health", "/health/full"}

# Every schema whose example is shown as the pre-filled body in "Try it out".
EXAMPLE_MODELS = [
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    UserCreate,
    OrganizationUpdate,
    DockerScanRequest,
    TLSScanRequest,
    ProjectCreate,
    BusinessContextUpdate,
    MoscaSimulateRequest,
    BenchmarkRunRequest,
    LifecycleTransitionBody,
    TokenResponse,
    ScanResponse,
]


@pytest.fixture(scope="module")
def spec():
    return app.openapi()


def operations(spec):
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


# --- completeness ---------------------------------------------------------------------------
def test_every_operation_has_a_description_and_a_declared_tag(spec):
    declared = {tag["name"] for tag in OPENAPI_TAGS}
    problems = []
    for path, method, operation in operations(spec):
        label = f"{method.upper()} {path}"
        if not (operation.get("description") or "").strip():
            problems.append(f"{label}: no description")
        tags = set(operation.get("tags", []))
        if not tags:
            problems.append(f"{label}: no tag")
        elif not tags <= declared:
            problems.append(f"{label}: undeclared tag(s) {sorted(tags - declared)}")
    assert not problems, "\n".join(problems)


def test_every_declared_tag_is_used_and_described(spec):
    used = {tag for _, _, operation in operations(spec) for tag in operation.get("tags", [])}
    for tag in OPENAPI_TAGS:
        assert tag["description"].strip(), tag["name"]
        assert tag["name"] in used, f"tag {tag['name']!r} is declared but no endpoint uses it"
    # the four feature areas the docs promise, as top-level groups
    assert {"Discovery", "Intelligence", "Migration", "Enterprise"} <= used


def test_api_metadata_explains_authentication(spec):
    info = spec["info"]
    assert "Authorization: Bearer" in info["description"]
    assert "/api/v1/auth/login" in info["description"]
    assert info["license"]["name"] == "Apache-2.0"
    assert info["contact"]["url"].startswith("https://github.com/")
    assert "HTTPBearer" in spec["components"]["securitySchemes"]


def test_operations_document_how_they_fail(spec):
    missing = []
    for path, method, operation in operations(spec):
        codes = set(operation["responses"])
        if path not in PUBLIC_PATHS and "401" not in codes:
            missing.append(f"{method.upper()} {path}: no 401 (has {sorted(codes)})")
        if path not in RATE_LIMIT_EXEMPT and "429" not in codes:
            missing.append(f"{method.upper()} {path}: no 429 (has {sorted(codes)})")
    assert not missing, "\n".join(missing)


# --- examples -------------------------------------------------------------------------------
@pytest.mark.parametrize("model", EXAMPLE_MODELS, ids=lambda m: m.__name__)
def test_schema_examples_are_valid_inputs_to_their_own_model(model):
    """A "Try it out" body that the API itself rejects would be worse than no example."""
    examples = model.model_json_schema().get("examples")
    assert examples, f"{model.__name__} has no example"
    for example in examples:
        model.model_validate(example)


def test_lifecycle_example_uses_a_real_state():
    example = LifecycleTransitionBody.model_json_schema()["examples"][0]
    assert LifecycleState(example["target_state"])


def test_examples_contain_no_secret_shaped_values():
    """Placeholders only: a realistic token in source would be flagged by the secret scanner."""
    for model in (LoginRequest, RegisterRequest, RefreshRequest, UserCreate, TokenResponse):
        text = str(model.model_json_schema()["examples"])
        assert "eyJ" not in text  # JWT header prefix
        assert "<" in text  # password / token fields are visibly placeholders


# --- documented errors match real behaviour --------------------------------------------------
@pytest.fixture
def client():
    return TestClient(app)


def test_documented_401_matches_the_real_response(client):
    documented = COMMON_RESPONSES[401]["content"]["application/json"]["example"]
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json() == documented
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_documented_login_and_refresh_errors_match_the_real_responses(client, spec):
    with SessionLocal() as db:
        seed_securebank_demo(db)

    login_doc = spec["paths"]["/api/v1/auth/login"]["post"]["responses"]["401"]
    wrong = client.post(
        "/api/v1/auth/login",
        json={"organization": "SecureBank", "username": "security-analyst", "password": "wrong"},
    )
    assert wrong.status_code == 401
    assert wrong.json() == login_doc["content"]["application/json"]["example"]

    good = client.post(
        "/api/v1/auth/login",
        json={
            "organization": "SecureBank",
            "username": "security-analyst",
            "password": get_settings().demo_password,
        },
    ).json()
    assert good["expires_in"] == get_settings().access_token_minutes * 60  # "15 minutes"
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": good["refresh_token"]})
    assert first.status_code == 200
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": good["refresh_token"]})
    refresh_doc = spec["paths"]["/api/v1/auth/refresh"]["post"]["responses"]["401"]
    assert replay.status_code == 401
    assert replay.json() == refresh_doc["content"]["application/json"]["example"]


def test_documented_403_matches_the_real_response(client):
    """The roles table promises viewers cannot run scans."""
    with SessionLocal() as db:
        seed_securebank_demo(db)
        # only three demo users exist; the auditor is read-only for scans
        auditor = AuthenticationService().login(
            db,
            LoginRequest(
                organization="SecureBank",
                username="security-auditor",
                password=get_settings().demo_password,
            ),
        )
    response = client.post(
        "/api/v1/scans/tls",
        headers={"Authorization": f"Bearer {auditor.access_token}"},
        json={"endpoint": "example.com:443", "project_name": "Portal"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Your role does not permit this operation"}


def _bearer(username: str) -> dict[str, str]:
    with SessionLocal() as db:
        tokens = AuthenticationService().login(
            db,
            LoginRequest(
                organization="SecureBank",
                username=username,
                password=get_settings().demo_password,
            ),
        )
    return {"Authorization": f"Bearer {tokens.access_token}"}


def test_lifecycle_transition_docs_match_the_real_role_rules(client, spec):
    """The endpoint enforces roles inside a service, so its docs are declared by hand; pin them."""
    with SessionLocal() as db:
        seed_securebank_demo(db)
    operation = spec["paths"]["/api/v1/assets/{asset_id}/lifecycle/transition"]["post"]
    assert operation["x-minimum-role"] == "security_analyst"
    assert {"400", "403", "404"} <= set(operation["responses"])

    analyst, auditor = _bearer("security-analyst"), _bearer("security-auditor")
    assets = client.get("/api/v1/assets?page_size=100", headers=analyst).json()["items"]
    discovered = next(
        a["id"]
        for a in assets
        if client.get(f"/api/v1/assets/{a['id']}/lifecycle", headers=analyst).json()[
            "lifecycle_state"
        ]
        == "DISCOVERED"
    )
    url = f"/api/v1/assets/{discovered}/lifecycle/transition"

    read_only = client.post(url, headers=auditor, json={"target_state": "ASSESSED"})
    assert read_only.status_code == 403
    documented_403 = operation["responses"]["403"]["content"]["application/json"]["example"]
    assert read_only.json() == documented_403

    skipped = client.post(url, headers=analyst, json={"target_state": "RETIRED"})
    assert skipped.status_code == 400
    documented_400 = operation["responses"]["400"]["content"]["application/json"]["example"]
    assert skipped.json() == documented_400

    forced = client.post(
        url,
        headers=analyst,
        json={"target_state": "RETIRED", "force_override": True, "reason": "x"},
    )
    assert forced.status_code == 403  # only administrators may force a jump


def test_documented_429_matches_the_real_rate_limiter():
    probe = FastAPI()
    probe.add_middleware(RateLimitMiddleware, requests_per_minute=1)

    @probe.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    limited = TestClient(probe)
    assert limited.get("/ping").status_code == 200
    blocked = limited.get("/ping")
    assert blocked.status_code == 429
    assert blocked.json() == COMMON_RESPONSES[429]["content"]["application/json"]["example"]
    assert int(blocked.headers["Retry-After"]) >= 1


# --- the docs pages actually run --------------------------------------------------------------
def _inline_script_hashes(html: str) -> set[str]:
    bodies = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.DOTALL)
    return {
        "'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'"
        for b in bodies
    }


def test_swagger_page_is_served_under_a_csp_that_lets_it_run(client):
    """Regression: the API-wide CSP (`default-src 'self'`) left /docs blank."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    csp = response.headers["content-security-policy"]
    script_src = next(d for d in csp.split("; ") if d.startswith("script-src"))

    assert "https://cdn.jsdelivr.net" in script_src  # where swagger-ui-bundle.js comes from
    assert "'unsafe-inline'" not in script_src  # inline init is allowed by hash only
    hashes = _inline_script_hashes(response.text)
    assert hashes, "expected Swagger UI's inline initializer"
    assert hashes <= set(script_src.split()), "the CSP must allow the exact inline script served"
    assert "frame-ancestors 'none'" in csp
    assert "/api/v1/openapi.json" in response.text


def test_redoc_page_is_served_under_its_own_csp(client):
    response = client.get("/redoc")
    assert response.status_code == 200
    csp = response.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in csp
    assert "worker-src blob:" in csp  # ReDoc parses the spec in a web worker
    script_src = next(d for d in csp.split("; ") if d.startswith("script-src"))
    assert "'unsafe-inline'" not in script_src


def test_every_other_route_keeps_the_strict_csp(client):
    strict = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    for path in ("/health", "/api/v1/openapi.json", "/api/v1/dashboard"):
        assert client.get(path).headers["content-security-policy"] == strict, path


def test_docs_and_spec_need_no_authentication_and_the_spec_is_valid_json(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    body = client.get("/api/v1/openapi.json").json()
    assert body["openapi"].startswith("3.")
    assert len(body["paths"]) >= 50
