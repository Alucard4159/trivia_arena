from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from trivia_arena.packs_catalog import load_all_packs
from trivia_arena.security import hash_token, looks_like_token_hash

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('lobby', 'active', 'finished')),
    host_player_id INTEGER,
    current_round INTEGER NOT NULL DEFAULT 0,
    pack_id TEXT NOT NULL DEFAULT 'engineering',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    is_host INTEGER NOT NULL DEFAULT 0 CHECK (is_host IN (0, 1)),
    score INTEGER NOT NULL DEFAULT 0,
    UNIQUE (room_id, display_name)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id TEXT NOT NULL,
    category TEXT NOT NULL,
    prompt TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    correct_index INTEGER NOT NULL,
    UNIQUE (pack_id, prompt)
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


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate(conn: sqlite3.Connection) -> None:
    round_cols = _table_cols(conn, "rounds")
    if "phase_ends_at" not in round_cols:
        conn.execute("ALTER TABLE rounds ADD COLUMN phase_ends_at TEXT")

    room_cols = _table_cols(conn, "rooms")
    if "pack_id" not in room_cols:
        conn.execute(
            "ALTER TABLE rooms ADD COLUMN pack_id TEXT NOT NULL DEFAULT 'engineering'"
        )

    question_cols = _table_cols(conn, "questions")
    if "pack_id" not in question_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN pack_id TEXT NOT NULL DEFAULT 'engineering'"
        )
    if "category" not in question_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN category TEXT NOT NULL DEFAULT 'engineering'"
        )

    # Unique (pack_id, prompt) may be missing on older DBs; best-effort index.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS questions_pack_prompt
        ON questions (pack_id, prompt)
        """
    )

    _migrate_player_tokens(conn)


def _migrate_player_tokens(conn: sqlite3.Connection) -> None:
    player_cols = _table_cols(conn, "players")
    if "token_hash" not in player_cols:
        conn.execute("ALTER TABLE players ADD COLUMN token_hash TEXT")
        player_cols = _table_cols(conn, "players")
        if "token" in player_cols:
            for row in conn.execute("SELECT id, token FROM players").fetchall():
                raw = str(row["token"] or "")
                if not raw:
                    continue
                digest = raw if looks_like_token_hash(raw) else hash_token(raw)
                conn.execute(
                    "UPDATE players SET token_hash = ? WHERE id = ?",
                    (digest, row["id"]),
                )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS players_token_hash
            ON players (token_hash)
            """
        )

    # Drop leftover plaintext column so DB exfil cannot recover bearer tokens.
    if "token" in _table_cols(conn, "players"):
        try:
            conn.execute("ALTER TABLE players DROP COLUMN token")
        except sqlite3.OperationalError:
            # Older SQLite without DROP COLUMN: overwrite with unique non-secrets.
            for row in conn.execute("SELECT id FROM players").fetchall():
                conn.execute(
                    "UPDATE players SET token = ? WHERE id = ?",
                    (f"scrubbed:{row['id']}", row["id"]),
                )


def _seed_local_packs(conn: sqlite3.Connection) -> None:
    for pack in load_all_packs():
        if pack.source != "local":
            continue
        for q in pack.questions:
            conn.execute(
                """
                INSERT OR IGNORE INTO questions
                    (pack_id, category, prompt, choices_json, correct_index)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pack.id,
                    pack.category,
                    q.prompt,
                    json.dumps(q.choices),
                    q.correct_index,
                ),
            )


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    _seed_local_packs(conn)
    conn.commit()


@contextmanager
def db_session(db_path: Path | str) -> Generator[sqlite3.Connection, None, None]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
