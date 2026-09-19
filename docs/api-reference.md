# Enterprise API reference

All `/api/v1` endpoints except registration, login, and token refresh require
`Authorization: Bearer <access JWT>`. Rate-limited requests return `429` with `Retry-After`.

| Area | Endpoints |
|---|---|
| Authentication | `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`; `GET /me` |
| Organization | `GET,PUT /api/v1/organizations/current` |
| Users | `GET,POST /api/v1/users` (administrator) |
| Discovery | `POST /api/v1/scans/repository`, `/docker`, `/tls`; `GET /scans` |
| Inventory | `GET /api/v1/assets`, `/graph`, `/dashboard` |
| Intelligence | `GET /api/v1/intelligence/risk`, `/hndl`, `/blast-radius` |
| Migration | `GET /api/v1/migration/recommendations`, `/roadmap` |
| Reports | `GET /api/v1/reports/{executive-summary|technical|inventory|quantum-risk|migration}?format=json|pdf|cbom|cbom-pdf` |
| PQC benchmarks | `GET /api/v1/benchmarks/pqc`, `/migration-impact`; `POST /api/v1/benchmarks/run` (administrator, analyst) |
| Audit | `GET /api/v1/audit-logs` |
| Monitoring | `GET /health`, `/health/full` |

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"organization":"SecureBank","username":"security-analyst","password":"<demo password>"}'
```

Successful refresh revokes the submitted refresh token and returns a new pair.

## PQC benchmarks

`GET /benchmarks/pqc` returns reference timings and sizes for ML-KEM-768/1024, ML-DSA-65/87,
RSA-2048/4096, ECDSA-P256 and ECDH-P256 (`config/pqc_benchmarks.json`), 0-100 radar scores, the
source of each figure, and the latest live run if there has been one. Sizes come from FIPS 203/204.
Timings marked `estimate` are order-of-magnitude figures rather than citations.

`POST /benchmarks/run` with `{"iterations": 20, "include_pqc": true}` measures this host: classical
algorithms via `cryptography`, and post-quantum algorithms only if `liboqs-python` is installed
(otherwise they are listed under `skipped`). One run at a time; a concurrent request gets `409`.
The result is kept in process memory per organisation (one tenant never sees another's host
details) and recorded as a `benchmark.run` audit event.

`GET /benchmarks/migration-impact?kex_from=&kex_to=&auth_from=&auth_to=&chain_certs=` models one
TLS 1.3 handshake before and after a migration: client/server CPU time, bytes on the wire,
certificate chain size, whether the server flight exceeds a 14.6 KB initial congestion window, and
whether each part is quantum-safe. Key-exchange arguments may be KEMs (`ECDH-P256`, `ML-KEM-768`)
or RSA used as legacy key transport (`RSA-2048`, TLS 1.2 style); authentication arguments must be
signature schemes. Invalid names return `422`.
