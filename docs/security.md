# Phase 1 security notes

## Trust boundaries

Repository archives, Docker images, TLS endpoints, certificate data, and all scanner output are untrusted. Analyst browsers and the deployment control plane are trusted only after an external access-control layer is applied.

## Implemented controls

- Bounded streaming uploads and normalized filenames
- ZIP traversal, absolute-path, symlink, encryption, file-count, and expanded-size checks
- Source-file size caps and ignored dependency/build directories
- Docker image reference validation and argument-array subprocess execution
- Docker probe isolation: no network, read-only filesystem, dropped capabilities, no-new-privileges, PID/memory/CPU limits, and fixed probe script
- DNS resolution before TLS connection and blocking of non-global addresses by default
- TLS connect timeout and certificate-verification error capture
- Controlled Neo4j labels and relationship types; no user-supplied Cypher fragments
- SQLAlchemy parameterization and Pydantic request validation
- CORS allowlist, response request IDs, clickjacking and MIME-sniffing headers
- Nginx CSP and static asset controls

## Residual Phase 1 risks

- Docker socket access is equivalent to privileged host control even when mounted read-only. Use a dedicated scanner host or socket proxy for broader deployments.
- Scans run in the API process and are not durable across a process crash. Move them to isolated queue workers before horizontal scale.
- Regex discovery can produce false positives and false negatives. Evidence and confidence are retained for analyst review.
- No authentication or tenant isolation exists by design. An authenticated reverse proxy is mandatory outside a single-user trusted lab.
- TLS private targets are blocked by default, but an administrator may explicitly enable them for internal discovery.
- Table creation is metadata-driven in Phase 1. Adopt migrations and backup procedures before production data stewardship.

