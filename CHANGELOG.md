# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) conventions.

## [Unreleased]

### Added

- Branded PDF reports (reportlab): a one-page executive summary (risk gauge, key metrics, top 5 critical assets, Mosca status, recommendation) and a multi-page technical report (inventory, risk breakdown, dependency graph, migration roadmap, PQC matrix, CBOM summary).
- `cbom-pdf` report format: a human-readable companion to the machine-readable CBOM JSON.
- Dashboard "Generate Report" dialog with report and format selection.

### Changed

- CBOM output is now CycloneDX 1.6 (`bomFormat: CycloneDX`) and validates against the official schema; algorithm primitives use spec enums, risk scores are carried in component and metadata properties. Previously `bomFormat` was `ECDAT-CBOM`.
- The enterprise CBOM is generated from the live inventory as a single BOM instead of wrapping stored per-scan documents.
- Existing inventory / quantum-risk / migration PDFs render as full paginated tables instead of the previous 56-line text dump.

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
