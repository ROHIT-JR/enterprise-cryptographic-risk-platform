# Security Policy

ECDAT-X processes sensitive source code, certificates, and infrastructure metadata. Supported
releases receive security fixes on the latest minor version.

Report suspected vulnerabilities privately using GitHub Security Advisories for this repository.
Do not open a public issue or include live credentials, customer source code, certificates, or
proprietary scan output. Include affected version, reproduction steps, impact, and a safe proof of
concept. Maintainers will acknowledge a report within five business days and coordinate disclosure.

Operational safeguards:

- Uploaded archives are bounded and extracted with traversal and symlink checks.
- TLS scanning blocks non-global addresses unless `ECDAT_TLS_ALLOW_PRIVATE_TARGETS=true` is explicitly set.
- Docker probes run without networking, Linux capabilities, or writable container filesystems. Access to the Docker socket remains privileged; isolate the backend host accordingly.
- PostgreSQL is authoritative. Neo4j is a rebuildable projection and the API degrades to relational graph data.
- Phase 3 APIs require JWT authentication and enforce role and organization boundaries.
- Refresh tokens are rotated and revocable; production deployments must replace every template secret.
- Production should terminate TLS ahead of the supplied reverse proxy and centralize audit logs.
