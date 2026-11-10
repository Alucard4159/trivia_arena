from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

import trivia_arena.services.game_service as game_service


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _start_two_player(client: TestClient) -> tuple[str, str, str]:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    code = created["code"]
    host_token = created["token"]
    guest = client.post(
        f"/api/rooms/{code}/join",
        json={"display_name": "Guest"},
    ).json()
    started = client.post(f"/api/rooms/{code}/start", headers=_auth(host_token))
    assert started.status_code == 200
    return code, host_token, guest["token"]


def test_early_close_when_all_answered(client: TestClient) -> None:
    code, host_token, guest_token = _start_two_player(client)

    host_state = client.get(f"/api/rooms/{code}", headers=_auth(host_token)).json()
    assert host_state["question"] is not None

    assert (
        client.post(
            f"/api/rooms/{code}/answer",
            headers=_auth(host_token),
            json={"choice_index": 0},
        ).status_code
        == 200
    )
    mid = client.get(f"/api/rooms/{code}", headers=_auth(host_token)).json()
    assert mid["question"] is not None
    assert mid["last_result"] is None

    answered = client.post(
        f"/api/rooms/{code}/answer",
        headers=_auth(guest_token),
        json={"choice_index": 1},
    )
    assert answered.status_code == 200
    body = answered.json()
    assert body["question"] is None
    assert body["last_result"] is not None
    assert "correct_index" in body["last_result"]
    assert len(body["last_result"]["answers"]) == 2
    assert all("correct" in a for a in body["last_result"]["answers"])


def test_deadline_ticks_open_then_reveal(client: TestClient, monkeypatch) -> None:
    clock = {"now": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)}

    def fake_now() -> datetime:
        return clock["now"]

    monkeypatch.setattr(game_service, "_utc_now", fake_now)

    code, host_token, _guest_token = _start_two_player(client)
    open_state = client.get(f"/api/rooms/{code}", headers=_auth(host_token)).json()
    assert open_state["question"] is not None
    assert open_state["phase_ends_at"] is not None
    assert open_state["last_result"] is None

    clock["now"] = clock["now"] + timedelta(seconds=game_service.ROUND_SECONDS + 1)
    scored = client.get(f"/api/rooms/{code}", headers=_auth(host_token)).json()
    assert scored["question"] is None
    assert scored["last_result"] is not None
    assert scored["current_round"] == 1

    clock["now"] = clock["now"] + timedelta(seconds=game_service.REVEAL_SECONDS + 1)
    advanced = client.get(f"/api/rooms/{code}", headers=_auth(host_token)).json()
    assert advanced["current_round"] == 2
    assert advanced["question"] is not None
    assert advanced["last_result"] is None


def test_host_next_includes_force_advance(client: TestClient) -> None:
    code, host_token, guest_token = _start_two_player(client)
    client.post(
        f"/api/rooms/{code}/answer",
        headers=_auth(guest_token),
        json={"choice_index": 0},
    )
    advanced = client.post(f"/api/rooms/{code}/next", headers=_auth(host_token))
    assert advanced.status_code == 200
    body = advanced.json()
    assert body["current_round"] == 2
    assert body["question"] is not None


def test_static_routes(client: TestClient) -> None:
    index = client.get("/")
    assert index.status_code == 200
    assert "text/html" in index.headers["content-type"]
    assert b"Trivia Arena" in index.content

    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert b"trivia_arena_meta" in js.content
    assert b"X-CSRF-Token" in js.content

    css = client.get("/static/style.css")
    assert css.status_code == 200
