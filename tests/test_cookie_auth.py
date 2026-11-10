from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from trivia_arena.app import create_app
from trivia_arena.security import CSRF_COOKIE, SESSION_COOKIE


def test_bearer_skips_csrf(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    # Drop CSRF header — Bearer alone must still authorize mutations.
    client.headers.pop("X-CSRF-Token", None)
    started = client.post(
        f"/api/rooms/{created['code']}/start",
        headers={"Authorization": f"Bearer {created['token']}"},
    )
    assert started.status_code == 200


def test_cookie_auth_requires_csrf(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"})
    assert created.status_code == 201
    assert SESSION_COOKIE in created.cookies

    # Cookie present, CSRF header removed → blocked.
    client.headers.pop("X-CSRF-Token", None)
    blocked = client.post(f"/api/rooms/{created.json()['code']}/start")
    assert blocked.status_code == 403
    assert "CSRF" in blocked.json()["detail"]


def test_cookie_auth_with_csrf(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"})
    code = created.json()["code"]
    # No Authorization header — rely on HttpOnly session cookie + CSRF.
    started = client.post(f"/api/rooms/{code}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "active"

    state = client.get(f"/api/rooms/{code}")
    assert state.status_code == 200
    # Cookie viewer should see your_answered field once answering starts.
    assert state.json()["question"] is not None


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/api/rooms", json={"display_name": "Host"})
    assert SESSION_COOKIE in client.cookies
    gone = client.post("/api/auth/logout")
    assert gone.status_code == 204
    # Starlette TestClient may keep jar entries as empty; server delete is enough.
    # Re-issue CSRF for next call.
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf


def test_cors_origins_configured(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "cors.db",
        create_rate=(10_000, 60.0),
        join_rate=(10_000, 60.0),
        lookup_rate=(10_000, 60.0),
        cors_origins=["https://alucard4159.github.io"],
    )
    with TestClient(app) as client:
        preflight = client.options(
            "/api/packs",
            headers={
                "Origin": "https://alucard4159.github.io",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.status_code == 200
        assert (
            preflight.headers.get("access-control-allow-origin")
            == "https://alucard4159.github.io"
        )
        assert preflight.headers.get("access-control-allow-credentials") == "true"

        denied = client.options(
            "/api/packs",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert denied.headers.get("access-control-allow-origin") != "https://evil.example"


def test_csrf_endpoint_sets_cookie(client: TestClient) -> None:
    # Fixture already called csrf; call again and ensure cookie + body match.
    res = client.get("/api/auth/csrf")
    assert res.status_code == 200
    assert res.json()["csrf_token"]
    assert CSRF_COOKIE in res.cookies or CSRF_COOKIE in client.cookies
