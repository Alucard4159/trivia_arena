from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from trivia_arena.cookies import clear_session_cookies
from trivia_arena.deps import enforce_csrf, get_optional_player, get_room_repo
from trivia_arena.repositories.room_repo import PlayerRow, RoomRepository
from trivia_arena.security import CSRF_COOKIE, new_csrf_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CsrfOut(BaseModel):
    csrf_token: str


class SessionOut(BaseModel):
    authenticated: bool
    player_id: int | None = None
    is_host: bool | None = None
    room_id: int | None = None


def _cookie_kwargs(request: Request) -> dict[str, object]:
    return {
        "secure": bool(request.app.state.cookie_secure),
        "samesite": str(request.app.state.cookie_samesite),
    }


@router.get("/csrf", response_model=CsrfOut)
def issue_csrf(request: Request, response: Response) -> CsrfOut:
    token = new_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=False,
        secure=bool(request.app.state.cookie_secure),
        samesite=str(request.app.state.cookie_samesite),  # type: ignore[arg-type]
        path="/",
        max_age=60 * 60 * 12,
    )
    return CsrfOut(csrf_token=token)


@router.get("/session", response_model=SessionOut)
def current_session(
    player: Annotated[PlayerRow | None, Depends(get_optional_player)],
) -> SessionOut:
    if player is None:
        return SessionOut(authenticated=False)
    return SessionOut(
        authenticated=True,
        player_id=player.id,
        is_host=player.is_host,
        room_id=player.room_id,
    )


@router.post("/logout", status_code=204, dependencies=[Depends(enforce_csrf)])
def logout(
    request: Request,
    response: Response,
    player: Annotated[PlayerRow | None, Depends(get_optional_player)],
    repo: Annotated[RoomRepository, Depends(get_room_repo)],
) -> Response:
    if player is not None:
        repo.invalidate_player_token(player.id)
    clear_session_cookies(response, **_cookie_kwargs(request))  # type: ignore[arg-type]
    response.status_code = 204
    return response
