# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) conventions.

## [Unreleased]

### Added

- Branded PDF reports (reportlab): a one-page executive summary (risk gauge, key metrics, top 5 critical assets, Mosca status, recommendation) and a multi-page technical report (inventory, risk breakdown, dependency graph, migration roadmap, PQC matrix, CBOM summary).
- `cbom-pdf` report format: a human-readable companion to the machine-readable CBOM JSON.
- Dashboard "Generate Report" dialog with report and format selection.
- PQC performance benchmarking dashboard (`/benchmarks`): key generation and operation time,
  key/ciphertext/signature size table, multi-dimensional radar comparison, and a TLS migration
  impact calculator. Reference data in `config/pqc_benchmarks.json` (sizes from FIPS 203/204);
  optional live measurement of this host via `POST /api/v1/benchmarks/run`.
- Migration verification on the Research & Validation page: a five-item checklist per migration
  task (compatibility, performance, key size, backward compatibility, rollback), a hybrid
  migration path (add PQC alongside the classical algorithm, test 30 days, then cut over), and test
  results with pass/fail indicators. Backed by `GET /api/v1/analytics/validation/migrations` and
  `migration_engine/verification.py`; limits live in `config/migration_verification.json`.
- Reference benchmark data for ML-KEM-512 and SLH-DSA-SHA2-128f, the algorithms the recommender
  actually selects.
- Complete API documentation. Every endpoint has a description and belongs to one of eight
  feature-area groups (Discovery, Intelligence, Migration, Enterprise, and so on). Request bodies
  carry working examples, error responses are documented, and each operation's required permission
  is declared in the OpenAPI spec. New `docs/api-guide.md` walks through the API with commands that
  have been run against a live server.
- Architecture documentation: a complete system diagram, the upload-to-report data flow, the
  risk-scoring methodology, a TOPSIS worked example, and the database schema. The schema and the
  TOPSIS example are generated from the code (`scripts/generate_docs.py`), and tests fail if any
  generated block, link, diagram or endpoint reference goes stale.
- Developer setup guide covering running without Docker, every configuration variable, migrations
  and troubleshooting, and a scanner development guide with a worked example that is run in tests.

### Changed

- CBOM output is now CycloneDX 1.6 (`bomFormat: CycloneDX`) and validates against the official schema; algorithm primitives use spec enums, risk scores are carried in component and metadata properties. Previously `bomFormat` was `ECDAT-CBOM`.
- The enterprise CBOM is generated from the live inventory as a single BOM instead of wrapping stored per-scan documents.
- Existing inventory / quantum-risk / migration PDFs render as full paginated tables instead of the previous 56-line text dump.

### Fixed

- The Research & Validation page failed for every signed-in user (it read a token from
  `localStorage` that the app never sets). It now uses the shared API client.
- The production image now ships `config/` and `benchmarks/`. `config/` was missing, so edits to
  `config/quantum_timeline.json` were silently ignored in containers (the Mosca model fell back to
  identical built-in defaults); the benchmark endpoints need both directories.
- `/docs` and `/redoc` rendered a blank page: the API-wide Content-Security-Policy blocked Swagger
  UI's scripts and styles. Those two pages now get a narrower policy they can run under (inline
  script allowed by hash only); every other route keeps the strict default.
- Database migrations could not run at all. Two `down_revision` pointers named a file instead of
  a revision ID, so `alembic upgrade head` (which the production Compose file runs before starting
  the API) crashed. The chain is repaired, and the Phase 4 revisions now skip columns and tables
  that the first revision already creates on a fresh database.
- The scanner plugin docs and README described entry-point plugin discovery as a shipped feature.
  `ScannerRegistry.discover()` exists but is never called by the application, so they now say so.

## [0.3.0] - 2026-08-29

### Added

- JWT access and rotating refresh authentication with scrypt password hashing.
- Administrator, security analyst, auditor, and viewer RBAC.
- Organization ownership across projects, scans, assets, risks, and migration plans.
- Audit logging, JSON/PDF/CBOM reports, and full component health monitoring.
- Public scanner plugin contract and Python entry-point discovery.
- Enterprise dashboards, production Compose, reverse proxy, Alembic migration, and security CI.
- Apache-2.0 licensing and public contribution/governance documentation.

### Security

- Authenticated API routers, tenant query filters, request rate limiting, hardened headers,
  production-secret validation, dependency auditing, secret scanning, and Trivy image checks.

## [0.2.0] - 2026-08-29

- Phase 2 quantum-risk intelligence and PQC migration planning.

## [0.1.0] - 2026-08-28

- Phase 1 and 1.5 discovery, inventory, CBOM, graph, and risk foundation.
