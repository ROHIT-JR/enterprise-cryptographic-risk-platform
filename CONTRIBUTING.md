# Contributing to ECDAT-X

Thank you for helping improve enterprise cryptographic visibility and migration readiness.

## Development setup

1. Fork and clone the repository.
2. Copy `.env.example` to `.env`; never commit the resulting file.
3. Run `docker compose up --build` for the complete local stack.
4. For host development, install `backend/requirements-dev.txt` and run `npm ci` in `frontend/`.

## Change workflow

- Create a focused branch from `main`.
- Add tests for behavior and security-boundary changes.
- Keep organization filters on every new persistence query.
- Implement scanners through `scanners.plugins.Scanner`; do not bypass normalization.
- Run `pytest`, Ruff, frontend tests/typecheck/build, and relevant Docker builds.
- Update the changelog and documentation when contracts change.

## Pull requests

Describe the problem, approach, security impact, testing evidence, and migration/rollback needs.
Keep unrelated refactors out of the same pull request. All CI and security checks must pass, and
at least one maintainer review is required before merge.

See [the detailed contribution guide](docs/contributing.md) and [security policy](SECURITY.md).
