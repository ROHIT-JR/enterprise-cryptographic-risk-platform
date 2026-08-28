from fastapi import APIRouter

from backend.app.api import assets, dashboard, graph, health, projects, risk, upload

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(upload.router)
api_router.include_router(assets.router)
api_router.include_router(risk.router)
api_router.include_router(graph.router)
