# API guide

How to use the ECDAT-X API: sign in, scan something, read the results, and handle errors. Every
command here was run against a live server. The endpoint tables and the role matrix are generated
from the running API, so they cannot drift (a test fails if they do).

- [Ways to explore the API](#ways-to-explore-the-api)
- [Five-minute tour](#five-minute-tour)
- [Authentication and roles](#authentication-and-roles)
- [Endpoint reference](#endpoint-reference)
- [Common tasks](#common-tasks)
- [Following a scan live](#following-a-scan-live)
- [Errors](#errors)
- [A Python client](#a-python-client)

For discovery-specific response contracts see [api.md](api.md); for the older summary tables see
[api-reference.md](api-reference.md). To see how the pieces fit together, read
[architecture.md](architecture.md).

## Ways to explore the API

With the stack running (`docker compose up -d`, then the API is on port 8000):

| What | Where | Good for |
|---|---|---|
| Swagger UI | <http://localhost:8000/docs> | Trying calls in the browser: click **Authorize**, paste an access token, then **Try it out**. Request bodies are pre-filled with working examples. |
| ReDoc | <http://localhost:8000/redoc> | Reading: a searchable three-pane reference. |
| OpenAPI document | <http://localhost:8000/api/v1/openapi.json> | Generating clients or importing into Postman or Insomnia. |

The interactive pages load their scripts from the jsDelivr CDN, so they need an internet
connection. The API itself does not.

## Five-minute tour

Set the base URL and your demo password once. The password is the `ECDAT_DEMO_PASSWORD` value in
your `.env` (copied from `.env.example`):

```bash
export BASE=http://localhost:8000/api/v1
export ECDAT_DEMO_PASSWORD=$(grep '^ECDAT_DEMO_PASSWORD=' .env | cut -d= -f2)
```

**1. Check the service is up.** No authentication needed. `neo4j: degraded` just means the optional
graph database is not running; everything still works from PostgreSQL.

```bash
curl -s http://localhost:8000/health/full
# {"backend":"healthy","postgres":"healthy","neo4j":"degraded","scanner_engine":"healthy",
#  "scanners":["docker","repository","tls"]}
```

**2. Log in and keep the access token.**

```bash
TOKEN=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
  -d "{\"organization\":\"SecureBank\",\"username\":\"security-analyst\",\"password\":\"$ECDAT_DEMO_PASSWORD\"}" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

The response also holds a `refresh_token`, `expires_in` (900 seconds) and the `user`.

**3. Confirm who you are.**

```bash
curl -s $BASE/auth/me -H "Authorization: Bearer $TOKEN"
# {"id":"...","username":"security-analyst","role":"security_analyst","is_active":true,...}
```

**4. Upload a repository for scanning.** This zips the bundled sample and returns `202 Accepted`
immediately; the analysis runs in the background.

```bash
(cd sample_enterprise && zip -qr ../secure-bank.zip secure-bank)
curl -s -X POST $BASE/scans/repository -H "Authorization: Bearer $TOKEN" \
  -F file=@secure-bank.zip -F project_name="Tour" -F criticality=high
# {"id":"<scan id>","status":"queued","progress":0,...}
```

No `zip` command (Windows)? Use PowerShell instead:
`Compress-Archive -Path sample_enterprise\secure-bank -DestinationPath secure-bank.zip`.

**5. Wait for it.** A scan goes `queued`, `running`, then `completed` or `failed`, with `progress`
climbing from 0 to 100. Poll, or [stream it](#following-a-scan-live):

```bash
SCAN=<scan id from the previous step>
curl -s $BASE/scans/$SCAN -H "Authorization: Bearer $TOKEN"
# "status":"completed","progress":100,"summary":{"assets_discovered":40,
#   "risk_severity":{"low":1,"medium":34,"high":5},
#   "quantum_intelligence":{"critical_quantum_risks":5,...},...}
```

**6. Read the results.**

```bash
# Inventory: filter, search and page
curl -s "$BASE/assets?search=RSA&severity=high&page_size=5" -H "Authorization: Bearer $TOKEN"

# The explainable risk score for every asset, worst first
curl -s $BASE/intelligence/risk -H "Authorization: Bearer $TOKEN"

# What breaks if the most-connected asset is compromised (two hops out)
curl -s "$BASE/intelligence/blast-radius?depth=2" -H "Authorization: Bearer $TOKEN"

# Which assets must start migrating before quantum computers arrive in 2032?
curl -s -X POST $BASE/mosca/simulate -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"quantum_arrival_year": 2032}'

# What to migrate, and in what order
curl -s $BASE/migration/recommendations -H "Authorization: Bearer $TOKEN"
curl -s $BASE/migration/roadmap -H "Authorization: Bearer $TOKEN"
```

**7. Export a report.**

```bash
curl -s "$BASE/reports/executive-summary?format=pdf" -H "Authorization: Bearer $TOKEN" -o summary.pdf
curl -s "$BASE/reports/inventory?format=cbom"        -H "Authorization: Bearer $TOKEN" -o cbom.json
```

Report types are `executive-summary`, `technical`, `inventory`, `quantum-risk` and `migration`.
Formats are `json`, `pdf`, `cbom` (CycloneDX 1.6) and `cbom-pdf`. Every export is written to the
audit trail.

## Authentication and roles

Every endpoint except register, login, refresh and `/health` needs `Authorization: Bearer
<access token>`.

- **Access tokens** are short-lived JWTs (15 minutes) carrying your role and organization.
- **Refresh tokens** last 7 days and **rotate**: exchanging one at `POST /auth/refresh` returns a new
  pair and revokes the old token. Using a revoked token again returns `401`, so never reuse one.
- **Logout** (`POST /auth/logout` with the refresh token) revokes it. The matching access token
  keeps working until it expires, so keep access tokens short-lived.
- Everything is scoped to your **organization**. You cannot see, and cannot ask for, another
  organization's data, and looking up another organization's ID returns `404`, not `403`.

```bash
# Get a new pair before the access token expires
curl -s -X POST $BASE/auth/refresh -H 'Content-Type: application/json' \
  -d '{"refresh_token": "<refresh token>"}'
```

Roles are cumulative: each role can do everything the one before it can. The `Needs` column in the
endpoint reference below says which role an endpoint requires.

<!-- role-matrix:start -->
| Permission | Grants | `viewer` | `auditor` | `security_analyst` | `administrator` |
| --- | --- | --- | --- | --- | --- |
| `manage_users` | List and create users |  |  |  | yes |
| `configure_organization` | Change organization settings |  |  |  | yes |
| `view_scans` | Read scans and inventory | yes | yes | yes | yes |
| `run_scans` | Start scans, create projects, run benchmarks |  |  | yes | yes |
| `analyze_risks` | Set business context for an asset |  |  | yes | yes |
| `create_migration_plans` | Create migration plans *(no endpoint requires it yet)* |  |  | yes | yes |
| `view_reports` | Read the audit trail and reports |  | yes | yes | yes |
| `export_findings` | Export reports and the CBOM |  | yes | yes | yes |
| `view_dashboard` | Dashboards, benchmarks, verification, compliance | yes | yes | yes | yes |
<!-- role-matrix:end -->

Insufficient permission returns `403`. Lifecycle changes are also role-checked inside the service
(`viewer` and `auditor` are read-only; forcing an override is administrator-only).

## Endpoint reference

Generated from the live OpenAPI document. Paths are relative to the server root; `{name}` is a
path parameter.

<!-- endpoint-map:start -->
#### Authentication

Register an organization, log in, rotate tokens and inspect the current user. These are the only endpoints that do not need a bearer token (except `logout` and `me`).

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `POST /api/v1/auth/login` | Exchange organization, username and password for an access and refresh token pair. | Nothing (public) |
| `POST /api/v1/auth/logout` | Revoke a refresh token. | Any signed-in user |
| `GET /api/v1/auth/me` | Return the profile, role and organization of the authenticated user. | Any signed-in user |
| `POST /api/v1/auth/refresh` | Exchange a refresh token for a new token pair. | Nothing (public) |
| `POST /api/v1/auth/register` | Create an organization and its first administrator, and return a token pair. | Nothing (public) |

#### Discovery

Find cryptography and inventory it: start repository, container and TLS scans, follow their progress, and browse the resulting projects, assets, lifecycle and dependency graph.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/assets` | List discovered cryptographic assets, newest first. | Any signed-in user |
| `GET /api/v1/assets/{asset_id}` | Return one asset with its project context and current risk finding. | Any signed-in user |
| `GET /api/v1/assets/{asset_id}/lifecycle` | Return an asset's lifecycle state, governance status and full transition history. | Any signed-in user |
| `POST /api/v1/assets/{asset_id}/lifecycle/transition` | Move an asset to a new lifecycle state or governance status. | `security_analyst` and above |
| `GET /api/v1/graph` | Return the cryptographic dependency graph as nodes and edges. | Any signed-in user |
| `GET /api/v1/projects` | List this organization's projects, most recently updated first. | Any signed-in user |
| `POST /api/v1/projects` | Create a project. | `security_analyst` and above |
| `GET /api/v1/projects/{project_id}` | Return one project by ID. | Any signed-in user |
| `GET /api/v1/scans` | List this organization's scans, newest first, optionally filtered by project. | `viewer` and above |
| `POST /api/v1/scans/docker` | Start a discovery scan of a container image. | `security_analyst` and above |
| `POST /api/v1/scans/repository` | Upload a ZIP archive of a repository and start a discovery scan. | `security_analyst` and above |
| `POST /api/v1/scans/tls` | Start a discovery scan of a TLS endpoint. | `security_analyst` and above |
| `GET /api/v1/scans/{scan_id}` | Return one scan with its status, progress and summary. | `viewer` and above |
| `GET /api/v1/scans/{scan_id}/cbom` | Return the cryptographic bill of materials produced by a completed scan. | `viewer` and above |
| `GET /api/v1/scans/{scan_id}/stream` | Live scan progress as Server-Sent Events. | `viewer` and above |

#### Intelligence

Understand the risk: the explainable quantum-risk score, harvest-now-decrypt-later exposure, blast radius, business context, the Mosca inequality and the analyst dashboard.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/dashboard` | Return headline metrics for the analyst dashboard. | Any signed-in user |
| `GET /api/v1/intelligence/agility` | Crypto-Agility Score: how easily this organization can swap algorithms. | Any signed-in user |
| `GET /api/v1/intelligence/blast-radius` | Return the dependency blast radius of the highest-impact asset. | Any signed-in user |
| `PUT /api/v1/intelligence/business-context/{asset_id}` | Set the business context of an asset: criticality, data sensitivity and exposure. | `security_analyst` and above |
| `GET /api/v1/intelligence/hndl` | Return assets exposed to harvest-now-decrypt-later attacks. | Any signed-in user |
| `GET /api/v1/intelligence/risk` | Return the full quantum risk analysis for every analyzed asset. | Any signed-in user |
| `POST /api/v1/mosca/simulate` | Evaluate the Mosca inequality (X + Y > Z) for every analyzed asset. | Any signed-in user |
| `GET /api/v1/risks` | List risk findings, highest score first, with their asset and project context. | Any signed-in user |
| `GET /api/v1/risks/distribution` | Return finding counts per severity (critical, high, medium, low). | Any signed-in user |

#### Migration

Decide what to migrate and in what order: the PQC recommendation for each asset (ranked with TOPSIS) and the dependency-ordered migration roadmap.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/migration/recommendations` | Return the PQC migration recommendation for every planned asset. | Any signed-in user |
| `GET /api/v1/migration/roadmap` | Return the migration plan grouped into dependency-ordered waves. | Any signed-in user |

#### Enterprise

Run it as a shared service: organizations and users, the audit trail, executive and technical reports, CBOM export, and India NQM compliance.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/audit-logs` | Return the organization's audit trail, newest first. | `auditor` and above |
| `GET /api/v1/compliance/nqm` | India NQM phase alignment, computed from this organization's live inventory. | `viewer` and above |
| `GET /api/v1/enterprise/overview` | Return organization-wide totals for the administrator dashboard. | Any signed-in user |
| `GET /api/v1/organizations` | List every organization on the platform, alphabetically. | Any signed-in user |
| `POST /api/v1/organizations` | Create a new organization. | Any signed-in user |
| `GET /api/v1/organizations/current` | Return the caller's organization, including its industry and settings. | Any signed-in user |
| `PUT /api/v1/organizations/current` | Update the caller's organization. | `administrator` |
| `GET /api/v1/reports/{report_type}` | Export a report. | `auditor` and above |
| `GET /api/v1/users` | List the users in the caller's organization. | `administrator` |
| `POST /api/v1/users` | Add a user to the caller's organization with one of the four roles. | `administrator` |

#### Research & Validation

Evidence that the analysis holds up: PQC vs classical benchmarks, per-migration verification checklists with hybrid rollout plans, and the graph scalability results.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/analytics/validation` | Read-only endpoint exposing pre-generated benchmark results. | `viewer` and above |
| `GET /api/v1/analytics/validation/migrations` | Verification checklist, hybrid path and test results for each PQC migration task. | `viewer` and above |
| `GET /api/v1/benchmarks/migration-impact` | Estimate what a TLS 1.3 handshake costs before and after migrating. | `viewer` and above |
| `GET /api/v1/benchmarks/pqc` | Reference PQC/classical benchmark data, plus this organisation's latest live run. | `viewer` and above |
| `POST /api/v1/benchmarks/run` | Measure this host now. | `security_analyst` and above |

#### Platform

Liveness, readiness and component health for orchestrators and monitoring. `/health` and `/health/full` need no authentication.

| Endpoint | What it does | Needs |
| --- | --- | --- |
| `GET /api/v1/health/live` | Liveness probe: returns `ok` as soon as the process is serving requests. | Any signed-in user |
| `GET /api/v1/health/ready` | Readiness probe for load balancers and orchestrators. | Any signed-in user |
| `GET /health` | Report whether PostgreSQL and Neo4j are reachable. | Nothing (public) |
| `GET /health/full` | Report backend, database, graph and scanner-engine health together. | Nothing (public) |

#### Compatibility aliases

Unversioned paths kept for older clients: `/api/assets`, `/api/cbom/{project_id}`, `/api/graph`, `/api/risk`, `/api/upload/repository`.
<!-- endpoint-map:end -->

## Common tasks

**Set an asset's business context**, which feeds its risk score. Requires `security_analyst`:

```bash
curl -s -X PUT $BASE/intelligence/business-context/<asset id> \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"criticality":"critical","owner":"Payments engineering","data_lifetime_years":15,
       "data_sensitivity":"financial","downtime_requirement":"zero",
       "compatibility":"limited","legacy_technology":true}'
```

**Inspect and change an asset's lifecycle.** History is newest first. Moving forward needs
`security_analyst`; an administrator can force a jump with a `reason`:

```bash
curl -s $BASE/assets/<asset id>/lifecycle -H "Authorization: Bearer $TOKEN"
curl -s -X POST $BASE/assets/<asset id>/lifecycle/transition \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_governance_status": "DEFERRED", "reason": "Vendor fix due next quarter"}'
```

**Scan a live TLS endpoint or a container image:**

```bash
curl -s -X POST $BASE/scans/tls -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"endpoint":"example.com:443","project_name":"Website","criticality":"high"}'
curl -s -X POST $BASE/scans/docker -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"image":"nginx:1.27-alpine","project_name":"Edge proxy","criticality":"medium"}'
```

**Check that migrations hold up.** Each recommendation gets a verification checklist, a hybrid
rollout plan and test results; no test result marked `simulated` ever counts toward "verified":

```bash
curl -s $BASE/analytics/validation/migrations -H "Authorization: Bearer $TOKEN"
```

**Compare PQC with classical algorithms.** `GET /benchmarks/pqc` returns reference data;
`POST /benchmarks/run` (`security_analyst`) measures your own server; the migration-impact
estimate models a TLS handshake before and after a change:

```bash
curl -s "$BASE/benchmarks/migration-impact?kex_from=RSA-2048&kex_to=ML-KEM-768" \
  -H "Authorization: Bearer $TOKEN"
```

**Filter by project.** Most list and analysis endpoints accept `?project_id=<id>`; get IDs from
`GET /projects`.

**Paginate.** List endpoints that return many rows take `page` (from 1) and `page_size` (default
25, at most 100) and reply with `items`, `total`, `page` and `page_size`.

## Following a scan live

`GET /scans/{scan_id}/stream` pushes each stage as it happens, as Server-Sent Events. Send your
token in the header, and use `-N` so curl does not buffer:

```bash
curl -N $BASE/scans/$SCAN/stream -H "Authorization: Bearer $TOKEN"
# data: {"type": "stage", "progress": 20, "message": "Scanning repository target..."}
# data: {"type": "stage", "progress": 65, "message": "Calculating risk scores..."}
# data: {"type": "completed", "progress": 100, ...}
```

Event `type` is `stage`, `asset`, `completed` or `failed`, and the stream ends after the last two.
If you connect after a scan has finished you still get its current state, then the final event.
A `: keep-alive` comment is sent every 15 seconds on quiet connections. Browsers' `EventSource`
cannot send an `Authorization` header, so a web client should read the stream with `fetch`.

## Errors

Every error is JSON with a `detail` field. These are the real bodies:

| Status | When | Body |
|---|---|---|
| `401` | Missing, invalid or expired token; login with wrong credentials; a used or revoked refresh token | `{"detail": "Valid authentication is required"}` (also `Invalid organization, username, or password` and `Refresh token is expired or revoked`) |
| `403` | Your role does not permit the operation | `{"detail": "Your role does not permit this operation"}` |
| `404` | The thing does not exist **or belongs to another organization** | `{"detail": "Scan not found"}` |
| `409` | State conflict: registering an existing organization, or reading a CBOM before the scan completes | `{"detail": "CBOM is not available until the scan completes"}` |
| `422` | The request body or parameters are invalid | see below |
| `429` | More than 120 requests a minute from one client | `{"detail": "Rate limit exceeded"}` plus a `Retry-After` header |

Validation errors list every problem and carry a `request_id` you can quote when asking for help:

```json
{
  "detail": "Request validation failed",
  "errors": [
    {"type": "greater_than_equal", "loc": ["body", "quantum_arrival_year"],
     "msg": "Input should be greater than or equal to 2026", "input": 1999, "ctx": {"ge": 2026}}
  ],
  "request_id": "b7b8ed6e-d149-4a3b-b149-cb6c255d9ce7"
}
```

Every response also carries an `X-Request-ID` header (send your own to correlate logs).

## A Python client

A complete script: log in, upload a repository, wait for the scan, and print the riskiest assets.
It needs only `pip install requests`.

```python
import sys
import time

import requests

BASE = "http://localhost:8000/api/v1"

session = requests.Session()
login = session.post(
    f"{BASE}/auth/login",
    json={"organization": "SecureBank", "username": "security-analyst", "password": sys.argv[1]},
)
login.raise_for_status()
session.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

with open(sys.argv[2], "rb") as archive:
    scan = session.post(
        f"{BASE}/scans/repository",
        files={"file": archive},
        data={"project_name": "Python client demo", "criticality": "high"},
    )
scan.raise_for_status()
scan_id = scan.json()["id"]

while True:  # queued -> running -> completed | failed
    state = session.get(f"{BASE}/scans/{scan_id}").json()
    print(f"{state['status']:>9} {state['progress']:>3}%")
    if state["status"] in {"completed", "failed"}:
        break
    time.sleep(1)

risk = session.get(f"{BASE}/intelligence/risk").json()
for item in risk["items"][:3]:
    print(f"{item['final_score']:>5.1f}  {item['severity']:<8} {item['asset_name']} ({item['algorithm']})")
```

```text
$ python client.py "$ECDAT_DEMO_PASSWORD" secure-bank.zip
  running  10%
completed 100%
 94.0  critical SecureBank RSA-2048 Certificate (RSA-2048)
 90.0  critical RSA-2048 (RSA-2048)
 81.0  critical RSA-2048 (RSA-2048)
```
