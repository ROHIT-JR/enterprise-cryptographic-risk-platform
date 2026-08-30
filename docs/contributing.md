# Contributor guide

Start with `CONTRIBUTING.md`. Maintainer review additionally verifies:

- Tenant filters cover every new read and write.
- Mutating endpoints have a named RBAC permission and audit action.
- Scanner findings use normalized assets and never persist raw credentials.
- API changes update this documentation and OpenAPI tests.
- Data-model changes include an Alembic migration and rollback analysis.
- Unit, API integration, organization-isolation, frontend, and build checks pass.
- No environment file, token, report, scan archive, or customer artifact is committed.

Record user-visible changes in `CHANGELOG.md` and keep unrelated refactors separate.
