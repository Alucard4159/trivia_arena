from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from trivia_arena.cookies import apply_session_cookies
from trivia_arena.deps import enforce_csrf, get_game_service, get_optional_player, require_player
from trivia_arena.domain.exceptions import RateLimitError
from trivia_arena.rate_limit import RateLimiter
from trivia_arena.repositories.room_repo import PlayerRow
from trivia_arena.schemas.room import (
    AnswerIn,
    CreateRoomIn,
    JoinedOut,
    JoinRoomIn,
    RoomCreatedOut,
    RoomStateOut,
)
from trivia_arena.security import CSRF_COOKIE
from trivia_arena.services.game_service import GameService

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def _client_key(request: Request) -> str:
    """Client identity for rate limits.

    Uses the direct peer address by default. Only honor X-Forwarded-For when the
    operator opts in via TRIVIA_TRUST_PROXY / create_app(trust_proxy=True) and a
    reverse proxy overwrites that header.
    """
    if bool(getattr(request.app.state, "trust_proxy", False)):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _enforce(limiter: RateLimiter, key: str, *, action: str) -> None:
    if not limiter.allow(key):
        raise RateLimitError(f"rate limit exceeded for {action}")


def _set_auth_cookies(request: Request, response: Response, raw_token: str) -> None:
    # Reuse existing CSRF so the browser header stays valid across create/join.
    apply_session_cookies(
        response,
        raw_token=raw_token,
        csrf_token=request.cookies.get(CSRF_COOKIE),
        secure=bool(request.app.state.cookie_secure),
        samesite=str(request.app.state.cookie_samesite),
    )


@router.post(
    "",
    response_model=RoomCreatedOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_csrf)],
)
def create_room(
    body: CreateRoomIn,
    request: Request,
    response: Response,
    game: Annotated[GameService, Depends(get_game_service)],
) -> RoomCreatedOut:
    _enforce(request.app.state.create_limiter, _client_key(request), action="create room")
    out = game.create_room(body.display_name, pack_id=body.pack_id)
    _set_auth_cookies(request, response, out.token)
    return out


@router.post(
    "/{code}/join",
    response_model=JoinedOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_csrf)],
)
def join_room(
    code: str,
    body: JoinRoomIn,
    request: Request,
    response: Response,
    game: Annotated[GameService, Depends(get_game_service)],
) -> JoinedOut:
    _enforce(request.app.state.join_limiter, _client_key(request), action="join")
    out = game.join_room(code, body.display_name)
    _set_auth_cookies(request, response, out.token)
    return out


@router.get("/{code}", response_model=RoomStateOut)
def get_room(
    code: str,
    request: Request,
    game: Annotated[GameService, Depends(get_game_service)],
    viewer: Annotated[PlayerRow | None, Depends(get_optional_player)],
) -> RoomStateOut:
    _enforce(request.app.state.lookup_limiter, _client_key(request), action="room lookup")
    return game.get_state(code, viewer)


@router.post(
    "/{code}/start",
    response_model=RoomStateOut,
    dependencies=[Depends(enforce_csrf)],
)
def start_room(
    code: str,
    request: Request,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    _enforce(request.app.state.action_limiter, _client_key(request), action="room action")
    return game.start(code, actor)


@router.post(
    "/{code}/answer",
    response_model=RoomStateOut,
    dependencies=[Depends(enforce_csrf)],
)
def answer(
    code: str,
    body: AnswerIn,
    request: Request,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    _enforce(request.app.state.action_limiter, _client_key(request), action="room action")
    return game.answer(code, actor, body.choice_index)


@router.post(
    "/{code}/next",
    response_model=RoomStateOut,
    dependencies=[Depends(enforce_csrf)],
)
def next_round(
    code: str,
    request: Request,
    game: Annotated[GameService, Depends(get_game_service)],
    actor: Annotated[PlayerRow, Depends(require_player)],
) -> RoomStateOut:
    _enforce(request.app.state.action_limiter, _client_key(request), action="room action")
    return game.next_round(code, actor)
