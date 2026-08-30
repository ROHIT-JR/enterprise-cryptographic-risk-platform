# Production deployment

`deployment/docker-compose.prod.yml` runs immutable backend/frontend images, PostgreSQL and Neo4j
on an internal data network, and an Nginx gateway with request limiting. Local development remains
on the root `docker-compose.yml`.

```bash
cp deployment/.env.production.example deployment/.env.production
# Replace every placeholder with a secret from your secret manager.
docker compose --env-file deployment/.env.production \
  -f deployment/docker-compose.prod.yml up -d --build
```

The gateway listens on port `8080` by default. Terminate TLS at the load balancer or ingress and
set `ECDAT_CORS_ORIGINS` to the exact HTTPS origin. The backend runs `alembic upgrade head` before
starting two API workers.

- Liveness: `GET /health`
- Component readiness: `GET /health/full`
- Backup PostgreSQL and Neo4j volumes independently; PostgreSQL is authoritative.
- Keep `ECDAT_DOCKER_ENABLED=false` unless an isolated worker receives Docker socket access.
- Roll back images only after confirming the database migration is forward-compatible.

Cloud orchestration is intentionally not forced; the images and health contracts can later be
placed behind Kubernetes, ECS, or another managed container platform.
