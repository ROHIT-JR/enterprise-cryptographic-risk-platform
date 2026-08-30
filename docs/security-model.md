# Security model

Users authenticate with short-lived HS256 JWT access tokens. Rotating refresh tokens are stored
as SHA-256 digests and can be revoked. Passwords use salted scrypt. Tokens carry user,
organization, role, issuer, audience, type, issue time, expiry, and unique token ID claims.

| Role | Primary permissions |
|---|---|
| Administrator | users, organization, scans, analysis, migration, reports |
| Security analyst | scans, risk analysis, migration plans, reports |
| Auditor | reports, exports, read-only evidence |
| Viewer | read-only dashboard and scan visibility |

Organization IDs are persisted on projects, scans, assets, relationships, risk analyses, and
migration plans. Authenticated queries add the token organization as a mandatory filter.

Defense in depth includes exact-origin CORS, API/proxy rate limits, hardened response headers,
bounded inputs, production-secret validation, audit events, and CI dependency/secret/container
scanning. At multi-instance scale, replace the process-local inner limiter with a shared
Redis-backed limiter while retaining the reverse-proxy limit.
