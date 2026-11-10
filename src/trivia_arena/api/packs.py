from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from trivia_arena.deps import get_game_service
from trivia_arena.schemas.room import PackOut
from trivia_arena.services.game_service import GameService

router = APIRouter(prefix="/api/packs", tags=["packs"])


@router.get("", response_model=list[PackOut])
def list_packs(
    game: Annotated[GameService, Depends(get_game_service)],
) -> list[PackOut]:
    return game.list_packs()
