from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from trivia_arena.api import auth, health, packs, rooms
from trivia_arena.db import connect, init_db
from trivia_arena.domain.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationDomainError,
)
from trivia_arena.rate_limit import RateLimiter

STATIC_DIR = Path(__file__).parent / "static"

# Defaults: blunt room-code guessing without punishing normal play/polling.
DEFAULT_CREATE_RATE = (10, 60.0)  # 10 creates / minute / IP
DEFAULT_JOIN_RATE = (20, 60.0)  # 20 joins / minute / IP
DEFAULT_LOOKUP_RATE = (120, 60.0)  # 120 lookups / minute / IP


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


def create_app(
    *,
    db_path: Path | str = "data/trivia.db",
    create_rate: tuple[int, float] = DEFAULT_CREATE_RATE,
    join_rate: tuple[int, float] = DEFAULT_JOIN_RATE,
    lookup_rate: tuple[int, float] = DEFAULT_LOOKUP_RATE,
    cors_origins: Sequence[str] | None = None,
    cookie_secure: bool | None = None,
    cookie_samesite: str | None = None,
    trust_proxy: bool | None = None,
) -> FastAPI:
    path = Path(db_path)
    origins = list(cors_origins) if cors_origins is not None else _parse_cors_origins(
        os.environ.get("TRIVIA_CORS_ORIGINS")
    )
    secure = (
        cookie_secure
        if cookie_secure is not None
        else _env_flag("TRIVIA_COOKIE_SECURE")
    )
    samesite = (cookie_samesite or os.environ.get("TRIVIA_COOKIE_SAMESITE") or "lax").lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    proxy = trust_proxy if trust_proxy is not None else _env_flag("TRIVIA_TRUST_PROXY")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        conn = connect(path)
        try:
            init_db(conn)
        finally:
            conn.close()
        app.state.db_path = path
        app.state.create_limiter = RateLimiter(
            max_calls=create_rate[0],
            window_seconds=create_rate[1],
        )
        app.state.join_limiter = RateLimiter(
            max_calls=join_rate[0],
            window_seconds=join_rate[1],
        )
        app.state.lookup_limiter = RateLimiter(
            max_calls=lookup_rate[0],
            window_seconds=lookup_rate[1],
        )
        app.state.cookie_secure = secure
        app.state.cookie_samesite = samesite
        app.state.cors_origins = origins
        app.state.trust_proxy = proxy
        yield

    app = FastAPI(title="Trivia Arena", version="0.1.0", lifespan=lifespan)

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        )

    @app.exception_handler(NotFoundError)
    async def not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ValidationDomainError)
    async def validation(_request: Request, exc: ValidationDomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RateLimitError)
    async def rate_limited(_request: Request, exc: RateLimitError) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(DomainError)
    async def domain(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(packs.router)
    app.include_router(rooms.router)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
