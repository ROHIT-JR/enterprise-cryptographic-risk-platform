"""OpenAPI metadata for the interactive docs (/docs, /redoc) and their Content-Security-Policy."""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Any

API_DESCRIPTION = """\
ECDAT-X finds cryptography across an organization's repositories, container images and TLS
endpoints, scores how exposed each asset is to quantum attack, and plans the order in which to
migrate to post-quantum algorithms. This API is multi-tenant: every request only ever sees the
caller's own organization.

## Authenticating

Every endpoint except registration, login, refresh and `/health` needs a bearer token.

```bash
# 1. Log in (organization + username + password) and read the access token from the response
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"organization": "SecureBank", "username": "security-analyst", "password": "<your password>"}'

# 2. Send it on every request
curl -s http://localhost:8000/api/v1/dashboard -H 'Authorization: Bearer <access_token>'
```

In Swagger UI (`/docs`), click **Authorize**, paste the `access_token` (it adds the `Bearer`
prefix), then use **Try it out** on any endpoint. Access tokens last 15 minutes; exchange the
`refresh_token` at `POST /api/v1/auth/refresh` for a new pair. Refresh tokens rotate, so a token
that has been used once is rejected.

## Roles

| Role | Can do |
|---|---|
| `administrator` | Everything, including users and organization settings |
| `security_analyst` | Run scans, analyze risk, plan migrations, export reports |
| `auditor` | Read scans, reports and the audit trail; export findings |
| `viewer` | Read scans and dashboards |

A request the caller's role does not permit returns `403`.

## Conventions

- **Versioning:** endpoints live under `/api/v1`. A small set of `/api/...` aliases exists for
  older clients and is marked *Compatibility*.
- **Pagination:** list endpoints take `page` and `page_size` (default 25, maximum 100).
- **Errors:** every error is JSON with a `detail` field. Validation errors (`422`) also list the
  offending fields and carry a `request_id` you can quote when reporting a problem.
- **Rate limiting:** 120 requests per minute per client by default. Beyond that the API returns
  `429` with a `Retry-After` header.
- **Long-running work:** scans return `202` immediately. Poll `GET /scans/{scan_id}` or follow
  `GET /scans/{scan_id}/stream` (Server-Sent Events) for live progress.
"""

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "Authentication",
        "description": "Register an organization, log in, rotate tokens and inspect the current "
        "user. These are the only endpoints that do not need a bearer token (except `logout` "
        "and `me`).",
    },
    {
        "name": "Discovery",
        "description": "Find cryptography and inventory it: start repository, container and TLS "
        "scans, follow their progress, and browse the resulting projects, assets, lifecycle and "
        "dependency graph.",
    },
    {
        "name": "Intelligence",
        "description": "Understand the risk: the explainable quantum-risk score, "
        "harvest-now-decrypt-later exposure, blast radius, business context, the Mosca "
        "inequality and the analyst dashboard.",
    },
    {
        "name": "Migration",
        "description": "Decide what to migrate and in what order: the PQC recommendation for "
        "each asset (ranked with TOPSIS) and the dependency-ordered migration roadmap.",
    },
    {
        "name": "Enterprise",
        "description": "Run it as a shared service: organizations and users, the audit trail, "
        "executive and technical reports, CBOM export, and India NQM compliance.",
    },
    {
        "name": "Research & Validation",
        "description": "Evidence that the analysis holds up: PQC vs classical benchmarks, "
        "per-migration verification checklists with hybrid rollout plans, and the graph "
        "scalability results.",
    },
    {
        "name": "Compatibility",
        "description": "Unversioned `/api/...` aliases kept for older clients. Prefer the "
        "`/api/v1` equivalents.",
    },
    {
        "name": "Platform",
        "description": "Liveness, readiness and component health for orchestrators and "
        "monitoring. `/health` and `/health/full` need no authentication.",
    },
]

RATE_LIMITED: dict[int | str, dict[str, Any]] = {
    429: {
        "description": "Too many requests from this client. Wait for `Retry-After` seconds.",
        "content": {"application/json": {"example": {"detail": "Rate limit exceeded"}}},
    },
}

# Applied to every authenticated router so each operation documents how it can fail.
COMMON_RESPONSES: dict[int | str, dict[str, Any]] = {
    **RATE_LIMITED,
    401: {
        "description": "The bearer token is missing, invalid or expired. Log in again, or "
        "exchange the refresh token.",
        "content": {
            "application/json": {"example": {"detail": "Valid authentication is required"}}
        },
    },
}

_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL)


def _script_hashes(html: str) -> list[str]:
    """CSP source expressions for every inline <script> in ``html``."""
    hashes = []
    for body in _INLINE_SCRIPT.findall(html):
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        hashes.append(f"'sha256-{base64.b64encode(digest).decode('ascii')}'")
    return hashes


def docs_content_security_policy(html: str, *, redoc: bool = False) -> str:
    """The narrowest CSP under which the given docs page still runs.

    Scripts and styles come from the jsDelivr CDN; inline scripts are allowed only by hash.
    """
    scripts = " ".join(["'self'", "https://cdn.jsdelivr.net", *_script_hashes(html)])
    directives = [
        "default-src 'self'",
        f"script-src {scripts}",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
        + (" https://fonts.googleapis.com" if redoc else ""),
        "img-src 'self' data: https://fastapi.tiangolo.com" + (" https:" if redoc else ""),
        "font-src 'self' data:" + (" https://fonts.gstatic.com" if redoc else ""),
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
    ]
    if redoc:
        directives.append("worker-src blob:")
    return "; ".join(directives)
