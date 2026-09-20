from fastapi import APIRouter

from backend.app.api import intelligence, migration, mosca

router = APIRouter(prefix="/api")
router.include_router(intelligence.router)
router.include_router(migration.router)
router.include_router(mosca.router)
