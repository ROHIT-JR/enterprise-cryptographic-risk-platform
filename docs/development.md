# Development guide

## Prerequisites

- Python 3.11 or newer (the production image uses 3.12)
- Node.js 22 or newer
- Docker Engine and Compose v2 for the full stack
- PostgreSQL 16 and Neo4j 5.26 when running services outside Compose

## Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

For a dependency-free local database and graph fallback:

```bash
ECDAT_DATABASE_URL=sqlite+pysqlite:///./ecdat.db \
ECDAT_NEO4J_ENABLED=false \
ECDAT_SEED_DEMO=true \
uvicorn backend.app.main:app --reload --port 8000
```

Configuration uses the `ECDAT_` prefix. Important values include:

| Setting | Default | Purpose |
|---|---:|---|
| `ECDAT_DATABASE_URL` | SQLite development file | SQLAlchemy database URL |
| `ECDAT_SCAN_STORAGE_PATH` | `./scan-data` | Temporary upload workspace |
| `ECDAT_MAX_UPLOAD_BYTES` | 50 MiB | Compressed upload limit |
| `ECDAT_NEO4J_ENABLED` | `true` | Enable Neo4j projection |
| `ECDAT_TLS_ALLOW_PRIVATE_TARGETS` | `false` | Permit non-global TLS destinations |
| `ECDAT_DOCKER_ENABLED` | `true` | Enable Docker plugin |
| `ECDAT_SEED_DEMO` | `false` | Load SecureBank once on startup |

## Frontend setup

```bash
cd frontend
npm ci
npm run dev
```

The development server proxies `/api` to port 8000. Use `VITE_API_BASE_URL` for a separately hosted backend.

## Adding a scanner

Create a scanner implementing the contract in `scanners/base.py`:

```python
class InfrastructureScanner(ScannerPlugin):
    source_type = ScanSource("infrastructure")

    async def scan(self, target: str | Path, **options: Any) -> ScanResult:
        # Validate first, collect with explicit limits, retain evidence.
        return ScanResult(source=self.source_type, target=str(target), assets=[])
```

Then register it in `scanners/registry.py`. Scanner rules must:

- treat targets and source files as untrusted;
- avoid `shell=True` and command-string interpolation;
- bound time, file size, file count, output size, and network reach;
- preserve a useful evidence string and location;
- provide a calibrated confidence value;
- return stable relationships using asset fingerprints.

## Quality checks

```bash
ruff check backend scanners cbom_engine knowledge_graph risk_engine tests
pytest
cd frontend
npm run typecheck
npm run test -- --run
npm run build
npm audit
```

Tests use an in-memory SQLite database, the PostgreSQL graph fallback, and deterministic scanner fixtures. Docker and live TLS collection should be exercised in an isolated integration environment.

## Database changes

Phase 1 creates tables from SQLAlchemy metadata. Before shared production evolution, introduce Alembic migrations and version every schema change. PostgreSQL remains authoritative; Neo4j can be rebuilt from asset and relationship tables.

## Logging and diagnostics

The API emits structured-enough single-line logs with timestamps, severity, logger name, and scan IDs. Responses return `X-Request-ID`, honoring a caller-provided value when present. Avoid logging uploaded source, full certificates, secrets, or raw environment variables.

