from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, Request

from trivia_arena.domain.exceptions import ForbiddenError
from trivia_arena.repositories.room_repo import PlayerRow, RoomRepository
from trivia_arena.services.game_service import GameService


def get_db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


def get_connection(db_path: Annotated[Path, Depends(get_db_path)]) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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


def get_optional_player(
    repo: Annotated[RoomRepository, Depends(get_room_repo)],
    authorization: Annotated[str | None, Header()] = None,
) -> PlayerRow | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return repo.get_player_by_token(token)


def require_player(
    player: Annotated[PlayerRow | None, Depends(get_optional_player)],
) -> PlayerRow:
    if player is None:
        raise ForbiddenError("Bearer token required")
    return player
