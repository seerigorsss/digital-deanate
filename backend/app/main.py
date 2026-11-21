"""Точка входа: API под /api, собранный SPA — на том же домене (без CORS)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import applications, auth, meta, notifications, staff, student
from .config import get_settings
from .errors import install_error_handlers

log = logging.getLogger("deanate")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from .bootstrap import init_database

    init_database()
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Цифровой деканат — API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if s.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.app_env != "production" else None,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        # Ограничение размера тела запроса API (защита от злоупотреблений)
        cl = request.headers.get("content-length")
        if request.url.path.startswith("/api") and cl and cl.isdigit() and int(cl) > 64 * 1024:
            return JSONResponse(status_code=413, content={"detail": "Слишком большой запрос", "code": "payload_too_large"})
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if s.cookie_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.url.path.startswith("/api"):
            h.setdefault("Cache-Control", "no-store")
        return response

    for r in (auth.router, student.router, applications.router, notifications.router, staff.router, meta.router):
        app.include_router(r)

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def api_not_found(rest: str):  # noqa: ARG001
        return JSONResponse(status_code=404, content={"detail": "Не найдено", "code": "not_found"})

    dist = Path(s.frontend_dist)
    if dist.is_dir() and (dist / "index.html").exists():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        index = dist / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str):
            candidate = (dist / full_path).resolve()
            if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
    else:
        log.warning("Frontend build not found at %s — serving API only", dist)

    return app


app = create_app()
