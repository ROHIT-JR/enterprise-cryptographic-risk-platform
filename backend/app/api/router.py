from fastapi import APIRouter

from backend.app.api import (
    assets,
    audit,
    benchmarks,
    dashboard,
    enterprise,
    graph,
    health,
    intelligence,
    migration,
    organizations,
    projects,
    reports,
    risk,
    upload,
    users,
    validation,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(upload.router)
api_router.include_router(assets.router)
api_router.include_router(risk.router)
api_router.include_router(graph.router)
api_router.include_router(intelligence.router)
api_router.include_router(migration.router)
api_router.include_router(organizations.router)
api_router.include_router(users.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
api_router.include_router(enterprise.router)
api_router.include_router(validation.router)
api_router.include_router(benchmarks.router)
