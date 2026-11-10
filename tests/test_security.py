from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from trivia_arena.app import create_app
from trivia_arena.db import connect, init_db
from trivia_arena.repositories.room_repo import RoomRepository
from trivia_arena.security import hash_token


def test_legacy_plaintext_token_column_scrubbed(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            host_player_id INTEGER,
            current_round INTEGER NOT NULL DEFAULT 0,
            pack_id TEXT NOT NULL DEFAULT 'engineering'
        );
        CREATE TABLE players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            is_host INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id TEXT NOT NULL DEFAULT 'engineering',
            category TEXT NOT NULL DEFAULT 'engineering',
            prompt TEXT NOT NULL,
            choices_json TEXT NOT NULL,
            correct_index INTEGER NOT NULL
        );
        CREATE TABLE rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            phase_ends_at TEXT
        );
        CREATE TABLE answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            choice_index INTEGER NOT NULL
        );
        """
    )
    raw = "plaintext-bearer-token-value"
    conn.execute("INSERT INTO rooms (code, status) VALUES ('LEGACY', 'lobby')")
    conn.execute(
        """
        INSERT INTO players (room_id, display_name, token, is_host)
        VALUES (1, 'Host', ?, 1)
        """,
        (raw,),
    )
    conn.commit()
    conn.close()

    migrated = connect(db_path)
    init_db(migrated)
    cols = {row[1] for row in migrated.execute("PRAGMA table_info(players)").fetchall()}
    assert "token_hash" in cols
    row = migrated.execute(
        "SELECT token_hash FROM players WHERE display_name = 'Host'"
    ).fetchone()
    assert row is not None
    assert row["token_hash"] == hash_token(raw)
    if "token" in cols:
        leftover = migrated.execute("SELECT token FROM players").fetchone()[0]
        assert leftover != raw
        assert str(leftover).startswith("scrubbed:")
    else:
        assert "token" not in cols
    migrated.close()



def test_tokens_hashed_at_rest(client: TestClient, tmp_path: Path) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    raw = created["token"]
    assert raw
    assert raw != hash_token(raw)

    # Locate the same db the app is using via a second create_app is hard;
    # inspect through auth round-trip + direct hash lookup on a fresh mirrored insert.
    # Re-auth proves plaintext works; DB must not equal plaintext.
    me = client.get(
        f"/api/rooms/{created['code']}",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert me.status_code == 200

    # Open the client's db file from the TestClient app state.
    db_path = client.app.state.db_path  # type: ignore[attr-defined]
    row = sqlite3.connect(db_path).execute(
        "SELECT token_hash FROM players WHERE id = ?",
        (created["player_id"],),
    ).fetchone()
    assert row is not None
    assert row[0] == hash_token(raw)
    assert row[0] != raw


def test_duplicate_answer_is_idempotent(client: TestClient) -> None:
    created = client.post("/api/rooms", json={"display_name": "Host"}).json()
    code = created["code"]
    token = created["token"]
    # Second player keeps the round open after host answers (no early close).
    client.post(f"/api/rooms/{code}/join", json={"display_name": "Guest"})
    auth = {"Authorization": f"Bearer {token}"}
    client.post(f"/api/rooms/{code}/start", headers=auth)

    first = client.post(
        f"/api/rooms/{code}/answer",
        headers=auth,
        json={"choice_index": 0},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/rooms/{code}/answer",
        headers=auth,
        json={"choice_index": 1},
    )
    assert second.status_code == 200
    # First answer sticks; no 500 from UNIQUE race path.
    assert second.json()["your_answered"] is True
    assert second.json()["question"] is not None


def test_concurrent_score_awards_once(tmp_path: Path) -> None:
    db_path = tmp_path / "race.db"
    conn = connect(db_path)
    init_db(conn)
    repo = RoomRepository(conn)
    room = repo.create_room("RACE01", "engineering")
    host, _token = repo.add_player(room.id, "Host", is_host=True)
    repo.set_host(room.id, host.id)
    q = repo.pick_question("engineering", [])
    assert q is not None
    rnd = repo.create_round(room.id, 1, q.id, "2099-01-01T00:00:00Z")
    repo.set_current_round(room.id, 1)
    repo.set_status(room.id, "active")
    # Correct answer so a double-score would be visible.
    repo.upsert_answer(rnd.id, host.id, q.correct_index)
    conn.commit()
    conn.close()

    barrier = threading.Barrier(2)
    winners: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        c = connect(db_path)
        r = RoomRepository(c)
        barrier.wait()
        won = r.claim_round_scored(rnd.id, "2099-01-01T00:00:05Z")
        if won:
            question = r.get_question(q.id)
            for player_id, choice_index in r.list_answers(rnd.id):
                if choice_index == question.correct_index:
                    r.add_score(player_id, 1)
        c.commit()
        with lock:
            winners.append(won)
        c.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert winners.count(True) == 1
    assert winners.count(False) == 1

    check = connect(db_path)
    score = check.execute(
        "SELECT score FROM players WHERE id = ?",
        (host.id,),
    ).fetchone()[0]
    status = check.execute(
        "SELECT status FROM rounds WHERE id = ?",
        (rnd.id,),
    ).fetchone()[0]
    check.close()
    assert status == "scored"
    assert score == 1


def _with_csrf(client: TestClient) -> TestClient:
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return client


def test_create_rate_limit(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "create_limit.db",
        create_rate=(2, 60.0),
        join_rate=(10_000, 60.0),
        lookup_rate=(10_000, 60.0),
    )
    with TestClient(app) as raw:
        client = _with_csrf(raw)
        assert client.post("/api/rooms", json={"display_name": "A"}).status_code == 201
        assert client.post("/api/rooms", json={"display_name": "B"}).status_code == 201
        limited = client.post("/api/rooms", json={"display_name": "C"})
        assert limited.status_code == 429


def test_xff_ignored_unless_trust_proxy(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "xff.db",
        create_rate=(10_000, 60.0),
        join_rate=(1, 60.0),
        lookup_rate=(10_000, 60.0),
        trust_proxy=False,
    )
    with TestClient(app) as raw:
        client = _with_csrf(raw)
        host = client.post("/api/rooms", json={"display_name": "Host"}).json()
        code = host["code"]
        assert (
            client.post(
                f"/api/rooms/{code}/join",
                json={"display_name": "A"},
                headers={"X-Forwarded-For": "1.1.1.1"},
            ).status_code
            == 201
        )
        # Spoofed XFF must not mint a fresh bucket when trust_proxy is off.
        limited = client.post(
            f"/api/rooms/{code}/join",
            json={"display_name": "B"},
            headers={"X-Forwarded-For": "2.2.2.2"},
        )
        assert limited.status_code == 429


def test_join_rate_limit(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "limit.db",
        create_rate=(10_000, 60.0),
        join_rate=(2, 60.0),
        lookup_rate=(10_000, 60.0),
    )
    with TestClient(app) as raw:
        client = _with_csrf(raw)
        host = client.post("/api/rooms", json={"display_name": "Host"}).json()
        code = host["code"]
        assert (
            client.post(
                f"/api/rooms/{code}/join",
                json={"display_name": "A"},
            ).status_code
            == 201
        )
        assert (
            client.post(
                f"/api/rooms/{code}/join",
                json={"display_name": "B"},
            ).status_code
            == 201
        )
        limited = client.post(
            f"/api/rooms/{code}/join",
            json={"display_name": "C"},
        )
        assert limited.status_code == 429


def test_lookup_rate_limit(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "lookup.db",
        create_rate=(10_000, 60.0),
        join_rate=(10_000, 60.0),
        lookup_rate=(3, 60.0),
    )
    with TestClient(app) as raw:
        client = _with_csrf(raw)
        host = client.post("/api/rooms", json={"display_name": "Host"}).json()
        code = host["code"]
        assert client.get(f"/api/rooms/{code}").status_code == 200
        assert client.get(f"/api/rooms/{code}").status_code == 200
        assert client.get(f"/api/rooms/{code}").status_code == 200
        assert client.get(f"/api/rooms/{code}").status_code == 429
