# Development guide

Everything you need to run, change and test ECDAT-X. For how the system fits together read
[architecture.md](architecture.md); for using the API read [api-guide.md](api-guide.md).

- [Quick start (Docker)](#quick-start-docker)
- [Run the backend and frontend separately](#run-the-backend-and-frontend-separately)
- [Demo users](#demo-users)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Database and migrations](#database-and-migrations)
- [Tests and quality checks](#tests-and-quality-checks)
- [Adding an API endpoint](#adding-an-api-endpoint)
- [Adding a scanner](#adding-a-scanner)
- [Regenerating the docs](#regenerating-the-docs)
- [Troubleshooting](#troubleshooting)

## Quick start (Docker)

Prerequisites: Docker with Compose v2 and about 4 GiB of free memory.

```bash
git clone https://github.com/ROHIT-JR/enterprise-cryptographic-risk-platform.git
cd enterprise-cryptographic-risk-platform
cp .env.example .env && docker compose up -d
```

Open <http://localhost:5173> once `docker compose ps` shows every service `healthy` (the first
build takes a few minutes). The SecureBank demo organization is seeded automatically. On Linux the
API container also needs the Docker socket's group ID for image scanning; the README's
[first-time setup](../README.md#first-time-setup) shows the one extra command.

This starts PostgreSQL 16, Neo4j 5.26, the API on port 8000 and the Vite dev server on port 5173,
with the source mounted so edits reload. Stop with `docker compose down` (data is kept in volumes;
add `-v` to wipe it).

## Run the backend and frontend separately

This needs no Docker, PostgreSQL or Neo4j: the backend falls back to a local SQLite file and serves
the graph from the database. You need Python 3.11+ (the production image uses 3.12) and Node 22+.

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -r backend/requirements-dev.txt

export ECDAT_DATABASE_URL=sqlite+pysqlite:///./ecdat.db
export ECDAT_NEO4J_ENABLED=false
export ECDAT_SEED_DEMO=true
uvicorn backend.app.main:app --reload --port 8000
```

On Windows PowerShell set the variables with `$env:ECDAT_NEO4J_ENABLED = "false"` and so on. The
API is then at <http://localhost:8000> (interactive docs at `/docs`).

If you already copied `.env.example` to `.env` for Docker, note that its `DATABASE_URL` points at the
`postgres` container. The `ECDAT_DATABASE_URL` variable above takes priority, so exporting it is
enough. `Neo4j: degraded` in `/health/full` is expected here.

**Frontend**

```bash
cd frontend
npm ci
npm run dev
```

The dev server is on <http://localhost:5173> and calls the API at `VITE_API_URL` (default
`http://localhost:8000`). Because the browser calls the API directly, the API must allow the
frontend's origin: `ECDAT_CORS_ORIGINS` defaults to `http://localhost:5173`. If you serve the
frontend from another port, add that origin there too, or the browser will block every request.

## Demo users

With `ECDAT_SEED_DEMO=true` the app creates the **SecureBank** organization once, with three users
that share the `ECDAT_DEMO_PASSWORD` value from your `.env`:

| Organization | Username | Role |
|---|---|---|
| `SecureBank` | `securebank-admin` | administrator |
| `SecureBank` | `security-analyst` | security analyst |
| `SecureBank` | `security-auditor` | auditor |

Sign in as the analyst to try scans. The auditor is read-only, which is useful for checking that a
page respects permissions. Replace or disable these accounts before exposing an instance.

## Configuration

Settings are read from environment variables and from a `.env` file in the working directory. The
application variables below are `ECDAT_`-prefixed; where a plain alias also works, both are listed
(the prefixed one wins). The table is generated from the settings class, so it is always complete.

<!-- settings:start -->
| Variable | Default | Purpose |
| --- | --- | --- |
| `ECDAT_APP_NAME` | `ECDAT-X API` | Title shown in the API documentation. |
| `ECDAT_ENVIRONMENT` | `development` | `production` enables startup checks (a strong secret key, no wildcard CORS) and HSTS. |
| `ECDAT_DEBUG` | `False` | Reserved. Currently has no effect. |
| `ECDAT_API_PREFIX` | `/api/v1` | URL prefix of the versioned API. |
| `ECDAT_DATABASE_URL`, `DATABASE_URL` | `sqlite+pysqlite:///./ecdat.db` | SQLAlchemy URL. SQLite for local use, `postgresql+psycopg://...` for the stack. |
| `ECDAT_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed to call the API (exact match; `*` is refused in production). |
| `ECDAT_SCAN_STORAGE_PATH` | `scan-data` | Where uploaded archives are unpacked during a scan. |
| `ECDAT_MAX_UPLOAD_BYTES` | `52428800` | Largest accepted repository upload (compressed). |
| `ECDAT_MAX_ARCHIVE_FILES` | `20000` | Most files a repository archive may contain. |
| `ECDAT_MAX_ARCHIVE_UNCOMPRESSED_BYTES` | `262144000` | Most bytes a repository archive may expand to (zip-bomb guard). |
| `ECDAT_SCANNER_TIMEOUT_SECONDS` | `45` | Time budget for one scanner run. |
| `ECDAT_TLS_CONNECT_TIMEOUT_SECONDS` | `8.0` | Connect timeout for TLS endpoint scans. |
| `ECDAT_TLS_ALLOW_PRIVATE_TARGETS` | `False` | Allow TLS scans of private and loopback addresses. Off by default to prevent SSRF. |
| `ECDAT_DOCKER_ENABLED` | `True` | Enable the Docker image scanner (needs access to the Docker socket). |
| `ECDAT_ENABLE_SCANNER_DISCOVERY` | `False` | Load third-party scanners published under the `ecdat_x.scanners` entry-point group at startup. Off by default: this runs code from any installed package. |
| `ECDAT_NEO4J_ENABLED` | `True` | Project the graph into Neo4j. When off, the graph is served from the database. |
| `ECDAT_NEO4J_URI`, `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt endpoint. |
| `ECDAT_NEO4J_USER`, `NEO4J_USERNAME`, `NEO4J_USER` | `neo4j` | Neo4j user. |
| `ECDAT_NEO4J_PASSWORD`, `NEO4J_PASSWORD` | set in `.env` | Neo4j password. |
| `ECDAT_SEED_DEMO` | `False` | Load the SecureBank demo organization on startup (once). |
| `ECDAT_SECRET_KEY` | set in `.env` | Signs JWTs. Must be a random value of 32+ characters in production. |
| `ECDAT_JWT_ISSUER` | `ecdat-x` | `iss` claim of issued tokens. |
| `ECDAT_JWT_AUDIENCE` | `ecdat-x-api` | `aud` claim of issued tokens. |
| `ECDAT_ACCESS_TOKEN_MINUTES` | `15` | Access token lifetime. |
| `ECDAT_REFRESH_TOKEN_DAYS` | `7` | Refresh token lifetime. |
| `ECDAT_RATE_LIMIT_PER_MINUTE` | `120` | Requests per minute allowed from one client before `429`. |
| `ECDAT_DEMO_PASSWORD` | set in `.env` | Password given to the seeded demo users. |
| `ECDAT_LOG_LEVEL` | `INFO` | Python logging level. |
<!-- settings:end -->

Variables used by Docker Compose and the frontend rather than the application:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | API address the frontend calls. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `ecdat`, `ecdat_user`, from `.env` | Database created by the Compose Postgres service. |
| `DATABASE_URL` | `postgresql+psycopg://...@postgres:5432/ecdat` | How the API container reaches Postgres. |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | `bolt://neo4j:7687`, `neo4j` | How the API container reaches Neo4j. |
| `DOCKER_GID` | `999` | Group ID of the Docker socket, so the API can scan images (Linux). |
| `ECDAT_HTTP_PORT` | `8080` | Port the production gateway listens on. |

**Production.** Set `ECDAT_ENVIRONMENT=production`. The API then refuses to start with a weak
`ECDAT_SECRET_KEY` (under 32 characters, or a placeholder such as `change-me`) or a wildcard CORS
origin, and sends HSTS. Use the production Compose file (`deployment/docker-compose.prod.yml`),
which adds the gateway and keeps the databases on an internal-only network.

## Project layout

| Path | What lives there |
|---|---|
| `backend/app/api/` | FastAPI routers, one file per feature area. Thin: validate, authorize, delegate. |
| `backend/app/services/` | Orchestration and persistence (scan orchestrator, intelligence, reports). |
| `backend/app/auth/`, `security/` | JWT, roles and permissions, rate limiting. |
| `backend/app/models/`, `schemas/` | SQLAlchemy tables and Pydantic request/response models. |
| `backend/migrations/` | Alembic revisions. |
| `scanners/` | Scanner plugins (repository, Docker, TLS) and their registry. |
| `risk_engine/` | Quantum risk, HNDL, centrality, Mosca, crypto-agility scoring. |
| `migration_engine/` | PQC knowledge base, TOPSIS, roadmap optimizer, verification. |
| `cbom_engine/`, `lifecycle_engine/`, `graph_analysis/`, `knowledge_graph/` | CBOM generation, the asset state machine, NetworkX metrics, Neo4j projection. |
| `benchmarks/`, `config/` | PQC benchmark runner and the JSON data the engines read. |
| `frontend/src/` | React app: `pages/`, `components/`, `api/client.ts`, `types/api.ts`. |
| `sample_enterprise/`, `sample_data/` | Demo repositories and seed data. |
| `docs/`, `scripts/` | Documentation and the generator for its derived blocks. |

The engines (`risk_engine`, `migration_engine`, ...) are plain Python with no HTTP or database
imports. Keep it that way: it is what makes them easy to test.

## Database and migrations

- **Development:** the API creates any missing tables at startup (`Base.metadata.create_all`), so a
  fresh SQLite file just works.
- **Production:** the Compose file runs `alembic upgrade head` before starting the API, so schema
  changes need a migration.

```bash
alembic upgrade head        # apply migrations (safe to repeat)
alembic current             # which revision is the database on
alembic heads               # must print exactly one head
alembic revision --autogenerate -m "describe the change"
```

Set `ECDAT_DATABASE_URL` first so Alembic targets the database you mean. Two rules:

1. **Keep the chain linked.** A revision's `down_revision` must be the `revision` ID of its parent,
   not its file name. `tests/test_migrations.py` fails if the chain breaks or forks.
2. **Make a revision safe on a fresh database.** The first revision builds the *current* schema on an
   empty database, so later revisions must skip a column or table that already exists. Check with
   the inspector before `add_column` or `create_table`, as the existing revisions do.

## Tests and quality checks

CI runs exactly this; run it locally before you push:

```bash
# backend
ruff check backend scanners cbom_engine knowledge_graph risk_engine migration_engine tests
pytest --cov=backend --cov=scanners --cov=cbom_engine --cov=risk_engine --cov=migration_engine

# frontend
cd frontend
npm run typecheck
npm run test -- --run
npm run build
```

Backend tests use an in-memory SQLite database and need neither Docker nor Neo4j. The liboqs
integration tests (`tests/test_pqc_benchmarks_liboqs.py`) are skipped unless the native liboqs
library is installed. Live TLS and Docker scanning are not covered by the unit tests, so exercise
them in an isolated environment.

`make install`, `make test`, `make lint` and `make dev` wrap the common commands.

## Adding an API endpoint

1. Put the route in the router for its feature area (`backend/app/api/`). Keep it thin and put the
   logic in a service or engine.
2. **Write the docstring.** It becomes the description in `/docs`; lead with one sentence saying what
   it does. A test fails if any operation has no description.
3. Use one of the existing tags (`Discovery`, `Intelligence`, `Migration`, `Enterprise`, `Research &
   Validation`, `Platform`), declared in `backend/app/openapi_docs.py`.
4. **Authorize it.** Gate it with `Depends(require_permissions(Permission.X))`; that also records the
   requirement in the OpenAPI spec, which the generated endpoint reference reads. If you enforce
   roles inside a service instead, declare it with `openapi_extra={"x-minimum-role": "..."}`.
5. Filter every query by the caller's `organization_id`. Return `404`, not `403`, for another
   organization's objects.
6. Give request models an example (`model_config = ConfigDict(json_schema_extra={"examples":
   [...]})`) with placeholder values such as `<your password>`, never a realistic secret.
7. Document non-obvious failures with `responses={...}`. `401` and `429` are added for you.
8. Add tests, then run `python scripts/generate_docs.py --write` so the endpoint reference updates.

## Adding a scanner

See [Scanner development](scanner-development.md) for the contract, a complete working example and
the security checklist.

## Regenerating the docs

Some documentation is generated from the code so it cannot go stale: the database diagram and TOPSIS
example in [architecture.md](architecture.md), the endpoint reference and role matrix in
[api-guide.md](api-guide.md), and the settings table above. After changing models, endpoints,
permissions, settings or the PQC knowledge base, refresh them:

```bash
python scripts/generate_docs.py --write
```

`tests/test_documentation.py` fails if a generated block is out of date, if a Mermaid diagram is
malformed, or if a relative link in the docs is broken. Diagrams are Mermaid, so GitHub renders
them; preview one at <https://mermaid.live>.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Every browser request fails with a CORS error | The frontend's origin is not in `ECDAT_CORS_ORIGINS`. Add it (comma-separated) and restart the API. |
| `Port 5173 is reserved` (Windows) | Windows can reserve port ranges (`netsh int ipv4 show excludedportrange protocol=tcp`). Run the dev server on another port (`npm run dev -- --port 5200`) and add that origin to `ECDAT_CORS_ORIGINS`. |
| `401 Valid authentication is required` after a while | Access tokens last 15 minutes. Log in again, or use the refresh token. |
| `/docs` is a blank page | The interactive docs load Swagger UI or ReDoc from a CDN; check your internet connection. |
| `neo4j: degraded` in `/health/full` | Neo4j is off or unreachable. Harmless: the graph is served from the database. |
| Docker image scans fail on Linux | The API container cannot read the Docker socket. Set `DOCKER_GID` in `.env` to the socket's group ID. |
| `429 Rate limit exceeded` in a script | The default is 120 requests a minute per client. Slow down, or raise `ECDAT_RATE_LIMIT_PER_MINUTE`. |
| `alembic` says `KeyError` about a revision | A `down_revision` points at an ID that does not exist. See [Database and migrations](#database-and-migrations). |

## Logging

Logs are single-line with timestamp, level and logger name. Every response carries an
`X-Request-ID` header (a caller-supplied value is honored), and each request log line includes it,
so one ID ties a client report to the server log. Avoid logging uploaded source, certificates,
secrets or raw environment variables.
