from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_join_start_answer_next(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    code = created["code"]
    host_token = created["token"]

    joined = client.post(
        f"/api/rooms/{code}/join",
        json={"display_name": "Guest"},
    ).json()
    guest_token = joined["token"]

    started = client.post(
        f"/api/rooms/{code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "active"
    assert body["question"] is not None
    assert len(body["question"]["choices"]) == 4

    guest_auth = {"Authorization": f"Bearer {guest_token}"}
    answered = client.post(
        f"/api/rooms/{code}/answer",
        headers=guest_auth,
        json={"choice_index": 0},
    )
    assert answered.status_code == 200
    assert answered.json()["your_answered"] is True

    # Idempotent re-answer
    again = client.post(
        f"/api/rooms/{code}/answer",
        headers=guest_auth,
        json={"choice_index": 1},
    )
    assert again.status_code == 200

    guest_cannot_advance = client.post(
        f"/api/rooms/{code}/next",
        headers=guest_auth,
    )
    assert guest_cannot_advance.status_code == 403

    advanced = client.post(
        f"/api/rooms/{code}/next",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["current_round"] == 2


def test_guest_cannot_start(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    code = created["code"]
    guest = client.post(
        f"/api/rooms/{code}/join",
        json={"display_name": "Guest"},
    ).json()

    response = client.post(
        f"/api/rooms/{code}/start",
        headers={"Authorization": f"Bearer {guest['token']}"},
    )
    assert response.status_code == 403


def test_join_after_start_conflicts(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    code = created["code"]
    client.post(
        f"/api/rooms/{code}/start",
        headers={"Authorization": f"Bearer {created['token']}"},
    )
    response = client.post(
        f"/api/rooms/{code}/join",
        json={"display_name": "Late"},
    )
    assert response.status_code == 409
