# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.middleware.security import SecurityHeadersMiddleware
from app.api.admin import router as admin_router
from app.services.digest_service import DigestError
from app.api.articles import router as articles_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.digest import router as digest_router
from app.api.feeds import router as feeds_router
from app.api.search import router as search_router
from app.api.virtual_feeds import router as virtual_feeds_router
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.limiter import limiter
from app.services.auth_service import create_initial_admin
from app.services.llm.tagging import tagging_worker
from app.services.scheduler import setup_scheduler

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Prima Pagina backend (env=%s)", settings.app_env)
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        logger.info("Database connection OK")
        await create_initial_admin(session)

    _scheduler = setup_scheduler()
    _tagging_task = asyncio.create_task(tagging_worker())
    yield
    _tagging_task.cancel()
    await asyncio.gather(_tagging_task, return_exceptions=True)
    _scheduler.shutdown(wait=False)
    logger.info("Shutting down Prima Pagina backend")


app = FastAPI(
    title="Prima Pagina",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(feeds_router, prefix="/api/v1")
app.include_router(articles_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(virtual_feeds_router, prefix="/api/v1")
app.include_router(digest_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.exception_handler(DigestError)
async def digest_error_handler(request: Request, exc: DigestError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception for %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


@app.get("/api/v1/health", tags=["system"])
async def health():
    return {"status": "ok", "env": settings.app_env}
