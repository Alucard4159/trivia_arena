from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('lobby', 'active', 'finished')),
    host_player_id INTEGER,
    current_round INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    is_host INTEGER NOT NULL DEFAULT 0 CHECK (is_host IN (0, 1)),
    score INTEGER NOT NULL DEFAULT 0,
    UNIQUE (room_id, display_name)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    correct_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    status TEXT NOT NULL CHECK (status IN ('open', 'scored')),
    phase_ends_at TEXT,
    UNIQUE (room_id, round_number)
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    choice_index INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (round_id, player_id)
);
"""

SEED_QUESTIONS: list[tuple[str, str, int]] = [
    (
        "What does HTTP status 404 mean?",
        '["OK","Created","Not Found","Unauthorized"]',
        2,
    ),
    (
        "Which Python version does this stack lock?",
        '["3.9","3.10","3.11","3.12"]',
        3,
    ),
    (
        "Where should SQL live in the layered architecture?",
        '["Routes","Services","Repositories","Schemas"]',
        2,
    ),
    (
        "What validation library sits at trust boundaries?",
        '["attrs","Pydantic v2","marshmallow","dataclasses"]',
        1,
    ),
    (
        "Which is the pack stance on ORMs?",
        '["Required","SQLAlchemy ORM only","No ORM","Django ORM preferred"]',
        2,
    ),
]


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(rounds)").fetchall()}
    if "phase_ends_at" not in cols:
        conn.execute("ALTER TABLE rounds ADD COLUMN phase_ends_at TEXT")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
    if count == 0:
        conn.executemany(
            "INSERT INTO questions (prompt, choices_json, correct_index) VALUES (?, ?, ?)",
            SEED_QUESTIONS,
        )
    conn.commit()


@contextmanager
def db_session(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
