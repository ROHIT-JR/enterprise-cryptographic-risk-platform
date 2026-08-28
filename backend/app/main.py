from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import api_router
from backend.app.config import get_settings
from backend.app.database import SessionLocal, init_db
from backend.app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    settings.scan_storage_path.mkdir(parents=True, exist_ok=True)
    if settings.seed_demo:
        from backend.app.seed import seed_securebank_demo

        with SessionLocal() as db:
            seed_securebank_demo(db)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Enterprise cryptographic discovery, CBOM, graph, and explainable risk API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
