from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.routers import auth, companies, scraper, exports, startups
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
    is_prod = settings.APP_ENV == "production"
    app = FastAPI(
        title="Nexus Intel API",
        version="1.0.0",
        description="B2B intelligence platform — Zauba Corp × data.gov.in",
        # Hide API docs in production to reduce attack surface
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    # Restrict accepted Host headers in production — prevents host-header injection.
    if is_prod:
        from fastapi.middleware.trustedhost import TrustedHostMiddleware
        allowed_hosts: list[str] = []
        for origin in settings.cors_origins_list:
            try:
                allowed_hosts.append(urlparse(origin).hostname or "")
            except Exception:
                pass
        allowed_hosts = [h for h in allowed_hosts if h]
        if allowed_hosts:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["Content-Disposition"],
        max_age=600,
    )

    # Financial-Grade Security Middleware (DOS, XSS, Clickjacking, MIME and HSTS)
    @app.middleware("http")
    async def security_attack_prevention_middleware(request: Request, call_next):
        # 1. DOS Protection: Prevent memory exhaustion attacks by capping standard request entity bodies at 5MB
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 5 * 1024 * 1024:  # 5 Megabytes
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Financial platform entity limit exceeded: request body payload too large."}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Malformed request: invalid Content-Length format."}
                )

        response = await call_next(request)

        # 2. Defense-in-depth response headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
            "magnetometer=(), accelerometer=(), gyroscope=()"
        )
        # Content Security Policy — restrictive but compatible with our Angular bundle
        # served from the same origin. Inline scripts allowed because Angular hashes
        # are awkward to compute at runtime; tighten further with nonces if needed.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none';"
        )

        # Strict HSTS in production
        if is_prod:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # Hide server header where possible
        response.headers.pop("Server", None)
        return response

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(auth.router)
    app.include_router(companies.router)
    app.include_router(scraper.router)
    app.include_router(exports.router)
    app.include_router(startups.router)


    if not os.path.exists("static"):
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
        # In production, return the minimum so we don't leak env metadata.
        if is_prod:
            return {"status": "ok"}
        return {"status": "ok", "env": settings.APP_ENV}

    # Mount frontend static files if the directory exists to support unified hosting
    if os.path.exists("static"):
        app.mount("/", StaticFiles(directory="static", html=True), name="static")

        # Custom exception handler for 404 Errors to support SPA routing (Angular routing)
        @app.exception_handler(404)
        async def spa_404_handler(request: Request, exc: Exception):
            path = request.url.path
            
            # Keep API endpoints returning standard 404
            if path.startswith(("/auth", "/companies", "/scraper", "/exports", "/startups", "/docs", "/health")):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            
            # If it's a file request that doesn't exist (e.g. missing image/assets), return 404
            if "." in path.split("/")[-1]:
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            
            # Serve index.html for SPA routing
            index_path = os.path.join("static", "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


app = create_app()
