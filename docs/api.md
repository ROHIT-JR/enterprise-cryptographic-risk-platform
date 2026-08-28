# API reference

Base path: `/api/v1`. Interactive OpenAPI documentation is served at `/docs`.

## Health

```http
GET /api/v1/health/live
GET /api/v1/health/ready
```

Readiness reports PostgreSQL and Neo4j separately. A missing Neo4j projection returns a degraded status while PostgreSQL-backed features remain available.

## Start scans

Repository ZIP:

```bash
curl -X POST http://localhost:8000/api/v1/scans/repository \
  -F 'file=@repository.zip;type=application/zip' \
  -F 'project_name=Payment Platform' \
  -F 'criticality=critical'
```

Docker image:

```bash
curl -X POST http://localhost:8000/api/v1/scans/docker \
  -H 'Content-Type: application/json' \
  -d '{"image":"nginx:1.27-alpine","project_name":"Edge Gateway","criticality":"high"}'
```

TLS endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/scans/tls \
  -H 'Content-Type: application/json' \
  -d '{"endpoint":"example.com:443","project_name":"Public Web","criticality":"high"}'
```

All scan intake endpoints return HTTP `202`:

```json
{
  "id": "4d9547c8-5414-4207-b97f-bcf24c9a14dc",
  "project_id": "c7a43467-5773-4ea2-97af-556fa65c86ee",
  "source_type": "repository",
  "target": "repository.zip",
  "status": "queued",
  "progress": 0,
  "error_message": null,
  "summary": {}
}
```

Poll `GET /api/v1/scans/{scan_id}` until `status` is `completed` or `failed`. Progress ranges from 0 to 100.

## CBOM

```http
GET /api/v1/scans/{scan_id}/cbom
```

Returns `409` while the scan is incomplete. A completed response wraps the generated document:

```json
{
  "scan_id": "4d9547c8-5414-4207-b97f-bcf24c9a14dc",
  "document": {
    "bomFormat": "ECDAT-CBOM",
    "specVersion": "1.0",
    "components": [],
    "dependencies": []
  }
}
```

## Asset inventory

```http
GET /api/v1/assets?search=RSA&asset_type=algorithm&severity=critical&page=1&page_size=25
GET /api/v1/assets/{asset_id}
```

Filters are optional: `project_id`, `asset_type`, `severity`, and `search`. Each asset includes evidence, location, confidence, dependency count, and a risk summary.

## Risk analysis

```http
GET /api/v1/risks?severity=critical&page=1&page_size=25
GET /api/v1/risks/distribution
```

Each finding includes the total score, severity, reasons, and factor objects:

```json
{
  "category": "algorithm_security",
  "points": 55,
  "explanation": "RSA is vulnerable to cryptographically relevant quantum computers",
  "rule_id": "ALG-RSA-Q"
}
```

## Knowledge graph

```http
GET /api/v1/graph?project_id={project_id}&limit=500
```

The response is frontend-neutral:

```json
{
  "nodes": [{"id":"asset-id","label":"RSA-2048","type":"algorithm","properties":{}}],
  "edges": [{"id":"edge-id","source":"library-id","target":"asset-id","type":"CONTAINS","properties":{}}],
  "source": "neo4j"
}
```

`source` becomes `postgresql` when Neo4j is unavailable.

## Errors

FastAPI validation errors use HTTP `422`. Unsafe archive or scanner failures transition the scan to `failed`; poll the scan resource and inspect `error_message`. Internal exceptions are logged with the scan ID but returned as a non-sensitive generic message.

