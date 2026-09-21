from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import api_router, auth, health, phase2, phase15
from backend.app.auth.dependencies import get_current_user
from backend.app.config import get_settings
from backend.app.database import SessionLocal, init_db
from backend.app.logging_config import configure_logging
from backend.app.security import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment.lower() == "production":
        insecure_secret = len(settings.secret_key) < 32 or settings.secret_key.startswith(
            ("development-", "replace-with", "change-me")
        )
        if insecure_secret:
            raise RuntimeError("ECDAT_SECRET_KEY must be a random production secret")
        if "*" in settings.cors_origins:
            raise RuntimeError("Wildcard CORS origins are not permitted in production")
    init_db()
    settings.scan_storage_path.mkdir(parents=True, exist_ok=True)
    if settings.seed_demo:
        from backend.app.seed import (
            seed_india_payments_contingency_scan,
            seed_india_payments_demo_org,
            seed_securebank_demo,
        )

        with SessionLocal() as db:
            seed_securebank_demo(db)
            seed_india_payments_demo_org(db)
            await seed_india_payments_contingency_scan(db)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        description="Multi-organization enterprise cryptographic intelligence API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
    )
    application.add_middleware(
        RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1_000,
            request_id,
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "errors": jsonable_encoder(exc.errors()),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logger.exception(
            "request_failed method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    application.include_router(health.public_router)
    application.include_router(auth.router)
    protected = [Depends(get_current_user)]
    application.include_router(phase15.router, dependencies=protected)
    application.include_router(phase2.router, dependencies=protected)
    application.include_router(api_router, prefix=settings.api_prefix, dependencies=protected)
    return application


app = create_app()
