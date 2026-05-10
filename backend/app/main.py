from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.routers import auth, companies, scraper, exports
import structlog

log = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.APP_ENV)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="StartupIntel India API",
        version="1.0.0",
        description="Startup intelligence platform — Zauba Corp × data.gov.in",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        max_age=600,
    )

    app.include_router(auth.router)
    app.include_router(companies.router)
    app.include_router(scraper.router)
    app.include_router(exports.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
