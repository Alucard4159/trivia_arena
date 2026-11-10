from __future__ import annotations

import hashlib
import hmac
import re
import secrets

_TOKEN_HASH_RE = re.compile(r"^[a-f0-9]{64}$")

SESSION_COOKIE = "ta_session"
CSRF_COOKIE = "ta_csrf"
CSRF_HEADER = "x-csrf-token"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(24)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def looks_like_token_hash(value: str) -> bool:
    return bool(_TOKEN_HASH_RE.fullmatch(value))


def csrf_tokens_match(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)
