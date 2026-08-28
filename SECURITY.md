# Security policy

ECDAT-X Phase 1 is a security-analysis platform and should be deployed on a trusted administrative network.

Report suspected vulnerabilities privately to the repository maintainers. Do not include live credentials, customer source code, certificates, or proprietary scan output in a public issue.

Operational safeguards:

- Uploaded archives are bounded and extracted with traversal and symlink checks.
- TLS scanning blocks non-global addresses unless `ECDAT_TLS_ALLOW_PRIVATE_TARGETS=true` is explicitly set.
- Docker probes run without networking, Linux capabilities, or writable container filesystems. Access to the Docker socket remains privileged; isolate the backend host accordingly.
- PostgreSQL is authoritative. Neo4j is a rebuildable projection and the API degrades to relational graph data.
- Phase 1 intentionally has no authentication. Do not expose it directly to the public internet.

