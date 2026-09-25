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

## Free-tier deployment (Render + Cloudflare Pages + Neon + Neo4j AuraDB Free)

For a public demo without recurring cost, the same images and health contracts run on managed
free tiers instead of self-hosted containers:

| Component  | Service                                                          | Notes |
|------------|-------------------------------------------------------------------|-------|
| PostgreSQL | [Neon](https://neon.tech)                                        | Autosuspends after 5 min idle, wakes on connection |
| Neo4j      | [Neo4j AuraDB Free](https://neo4j.com/docs/aura/auradb/free/)    | Auto-pauses after 3 days idle, needs a manual resume from the console |
| Backend    | [Render](https://render.com) free web service, builds from [`render.yaml`](../render.yaml) | Sleeps after 15 min idle, cold-starts on next request |
| Frontend   | [Cloudflare Pages](https://pages.cloudflare.com), builds `frontend/` | Free, unlimited static hosting, global CDN |

Setup:

1. Create the Neon project and AuraDB Free instance; copy `DATABASE_URL` and the `NEO4J_*` values.
2. Connect the repo to Render; it reads [`render.yaml`](../render.yaml) automatically. Set the
   `sync: false` env vars (`ECDAT_SECRET_KEY`, `DATABASE_URL`, `NEO4J_URI`, `NEO4J_USERNAME`,
   `NEO4J_PASSWORD`, `ECDAT_CORS_ORIGINS`) in the Render dashboard — they are intentionally not
   committed to the blueprint.
3. Connect the repo to Cloudflare Pages with project root `frontend/`, build command `npm run
   build`, output directory `dist`. Set `VITE_API_URL` to the Render service URL. The committed
   [`frontend/public/_redirects`](../frontend/public/_redirects) file makes client-side routes
   (React Router) resolve correctly instead of 404ing on a hard refresh.
4. Push to `main` — both platforms auto-deploy on their own via the native GitHub integration; the
   existing CI checks in `.github/workflows/ci.yml` remain the merge quality gate.

Known free-tier limitations to expect during a demo, not bugs:

- First request after 15 min of backend inactivity is slow (Render cold start).
- AuraDB pauses after 3 days of inactivity and needs a manual resume from the Aura console before
  graph-backed pages (Knowledge Graph, Blast Radius) will return data again.
