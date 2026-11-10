from __future__ import annotations

from fastapi import Response

from trivia_arena.security import CSRF_COOKIE, SESSION_COOKIE, new_csrf_token


def apply_session_cookies(
    response: Response,
    *,
    raw_token: str,
    csrf_token: str | None = None,
    secure: bool = False,
    samesite: str = "lax",
    max_age: int = 60 * 60 * 12,
) -> str:
    """Set HttpOnly session + readable CSRF cookie. Returns CSRF token used."""
    csrf = csrf_token or new_csrf_token()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        httponly=True,
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf,
        httponly=False,
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
        path="/",
        max_age=max_age,
    )
    return csrf


def clear_session_cookies(
    response: Response,
    *,
    secure: bool = False,
    samesite: str = "lax",
) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
    )
    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
    )
