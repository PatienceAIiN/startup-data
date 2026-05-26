from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.routers import auth, companies, scraper, exports
from app.services.scheduler_service import start_scheduler, stop_scheduler
import structlog
from urllib.parse import urlparse

log = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.APP_ENV)
    try:
        start_scheduler()
    except Exception as e:
        log.error("scheduler_start_failed", error=str(e))
    yield
    try:
        stop_scheduler()
    except Exception:
        pass
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nexus Intel API",
        version="1.0.0",
        description="B2B intelligence platform — Zauba Corp × data.gov.in",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(auth.router)
    app.include_router(companies.router)
    app.include_router(scraper.router)
    app.include_router(exports.router)


    @app.get("/", include_in_schema=False)
    async def root(request: Request):
        frontend_url = settings.FRONTEND_URL or ""
        if frontend_url and not frontend_url.startswith(("http://", "https://")):
            frontend_url = f"https://{frontend_url}"

        frontend_host = urlparse(frontend_url).netloc.lower()
        request_host = (request.url.hostname or "").lower()

        if not frontend_host or request_host == frontend_host:
            return {
                "message": "Backend is running",
                "docs": "/docs",
                "health": "/health",
            }

        return RedirectResponse(url=frontend_url, status_code=307)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
