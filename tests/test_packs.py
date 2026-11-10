from __future__ import annotations

from fastapi.testclient import TestClient

import trivia_arena.services.game_service as game_service
from trivia_arena.packs_catalog import PackQuestion

SCIENCE_PROMPTS = {
    "What is the chemical symbol for gold?",
    "What force keeps planets in orbit around the Sun?",
    "DNA is primarily found in which part of a eukaryotic cell?",
    "What is the speed of light in vacuum (approx)?",
    "Which particle has a negative charge?",
    "What is the pH of pure water at 25°C?",
    "Sound travels fastest through which medium?",
    "Which planet has the most moons (known count classically high)?",
    "What vitamin is produced in skin exposed to sunlight?",
    "What is the powerhouse of the cell?",
}


def test_list_packs(client: TestClient) -> None:
    response = client.get("/api/packs")
    assert response.status_code == 200
    packs = response.json()
    ids = {p["id"] for p in packs}
    assert {"engineering", "general", "science", "open_trivia"} <= ids
    science = next(p for p in packs if p["id"] == "science")
    assert science["source"] == "local"
    assert science["question_count"] >= 5


def test_create_room_unknown_pack(client: TestClient) -> None:
    response = client.post(
        "/api/rooms",
        json={"display_name": "Host", "pack_id": "nope"},
    )
    assert response.status_code == 404


def test_pack_filters_questions(client: TestClient) -> None:
    created = client.post(
        "/api/rooms",
        json={"display_name": "Host", "pack_id": "science"},
    ).json()
    assert created["pack_id"] == "science"
    code = created["code"]
    token = created["token"]

    started = client.post(
        f"/api/rooms/{code}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert started.status_code == 200
    body = started.json()
    assert body["pack_id"] == "science"
    assert body["question"] is not None
    assert body["question"]["prompt"] in SCIENCE_PROMPTS


def test_open_trivia_fetches_and_caches(client: TestClient, monkeypatch) -> None:
    fake = [
        PackQuestion(
            prompt=f"OTDB Q{i}?",
            choices=["A", "B", "C", "D"],
            correct_index=0,
        )
        for i in range(8)
    ]
    calls = {"n": 0}

    def fake_fetch() -> list[PackQuestion]:
        calls["n"] += 1
        return fake

    monkeypatch.setattr(game_service, "fetch_opentdb_questions", lambda amount=12: fake_fetch())

    created = client.post(
        "/api/rooms",
        json={"display_name": "Host", "pack_id": "open_trivia"},
    )
    assert created.status_code == 201
    assert created.json()["pack_id"] == "open_trivia"
    assert calls["n"] == 1

    started = client.post(
        f"/api/rooms/{created.json()['code']}/start",
        headers={"Authorization": f"Bearer {created.json()['token']}"},
    )
    assert started.status_code == 200
    prompt = started.json()["question"]["prompt"]
    assert prompt.startswith("OTDB Q")

    # Cache warm — second room should not refetch.
    again = client.post(
        "/api/rooms",
        json={"display_name": "Host2", "pack_id": "open_trivia"},
    )
    assert again.status_code == 201
    assert calls["n"] == 1
