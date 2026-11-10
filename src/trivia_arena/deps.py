from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, Request

from trivia_arena.domain.exceptions import ForbiddenError
from trivia_arena.repositories.room_repo import PlayerRow, RoomRepository
from trivia_arena.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, csrf_tokens_match
from trivia_arena.services.game_service import GameService

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


def get_connection(db_path: Annotated[Path, Depends(get_db_path)]) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_room_repo(
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> RoomRepository:
    return RoomRepository(conn)


def get_game_service(
    repo: Annotated[RoomRepository, Depends(get_room_repo)],
) -> GameService:
    return GameService(repo)


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_optional_player(
    request: Request,
    repo: Annotated[RoomRepository, Depends(get_room_repo)],
    authorization: Annotated[str | None, Header()] = None,
) -> PlayerRow | None:
    raw = _bearer_token(authorization)
    if raw is None:
        raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    return repo.get_player_by_token(raw)


def require_player(
    player: Annotated[PlayerRow | None, Depends(get_optional_player)],
) -> PlayerRow:
    if player is None:
        raise ForbiddenError("authentication required (Bearer or session cookie)")
    return player


def enforce_csrf(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """CSRF required for cookie/browser mutating calls. Bearer API clients skip."""
    if _bearer_token(authorization) is not None:
        return
    if request.method not in _UNSAFE_METHODS:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)
    if not csrf_tokens_match(cookie_token, header_token):
        raise ForbiddenError("CSRF validation failed")
