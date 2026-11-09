from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from trivia_arena.deps import get_game_service, get_optional_player, require_player
from trivia_arena.repositories.room_repo import PlayerRow
from trivia_arena.schemas.room import (
    AnswerIn,
    CreateRoomIn,
    JoinedOut,
    JoinRoomIn,
    RoomCreatedOut,
    RoomStateOut,
)
from trivia_arena.services.game_service import GameService

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("", response_model=RoomCreatedOut, status_code=status.HTTP_201_CREATED)
def create_room(
    body: CreateRoomIn,
    game: Annotated[GameService, Depends(get_game_service)],
) -> RoomCreatedOut:
    return game.create_room(body.display_name)


@router.post("/{code}/join", response_model=JoinedOut, status_code=status.HTTP_201_CREATED)
def join_room(
    code: str,
    body: JoinRoomIn,
    game: Annotated[GameService, Depends(get_game_service)],
) -> JoinedOut:
    return game.join_room(code, body.display_name)


@router.get("/{code}", response_model=RoomStateOut)
def get_room(
    code: str,
    game: Annotated[GameService, Depends(get_game_service)],
    viewer: Annotated[PlayerRow | None, Depends(get_optional_player)],
) -> RoomStateOut:
    return game.get_state(code, viewer)


@router.post("/{code}/start", response_model=RoomStateOut)
def start_room(
    code: str,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    return game.start(code, actor)


@router.post("/{code}/answer", response_model=RoomStateOut)
def answer(
    code: str,
    body: AnswerIn,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    return game.answer(code, actor, body.choice_index)


@router.post("/{code}/next", response_model=RoomStateOut)
def next_round(
    code: str,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    return game.next_round(code, actor)
