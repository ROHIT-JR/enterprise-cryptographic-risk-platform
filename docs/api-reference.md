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
| Audit | `GET /api/v1/audit-logs` |
| Monitoring | `GET /health`, `/health/full` |

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"organization":"SecureBank","username":"security-analyst","password":"<demo password>"}'
```

Successful refresh revokes the submitted refresh token and returns a new pair.
