from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from trivia_arena.domain.exceptions import NotFoundError
from trivia_arena.security import hash_token, new_token

_ROOM_COLS = "id, code, status, host_player_id, current_round, pack_id"
_PLAYER_COLS = "id, room_id, display_name, is_host, score"
_QUESTION_COLS = "id, pack_id, category, prompt, choices_json, correct_index"
_ROUND_COLS = "id, room_id, round_number, question_id, status, phase_ends_at"


@dataclass(frozen=True)
class RoomRow:
    id: int
    code: str
    status: str
    host_player_id: int | None
    current_round: int
    pack_id: str


@dataclass(frozen=True)
class PlayerRow:
    id: int
    room_id: int
    display_name: str
    is_host: bool
    score: int


@dataclass(frozen=True)
class QuestionRow:
    id: int
    pack_id: str
    category: str
    prompt: str
    choices: list[str]
    correct_index: int


@dataclass(frozen=True)
class RoundRow:
    id: int
    room_id: int
    round_number: int
    question_id: int
    status: str
    phase_ends_at: str | None


def _room(row: sqlite3.Row) -> RoomRow:
    return RoomRow(
        id=row["id"],
        code=row["code"],
        status=row["status"],
        host_player_id=row["host_player_id"],
        current_round=row["current_round"],
        pack_id=row["pack_id"],
    )


def _player(row: sqlite3.Row) -> PlayerRow:
    return PlayerRow(
        id=row["id"],
        room_id=row["room_id"],
        display_name=row["display_name"],
        is_host=bool(row["is_host"]),
        score=row["score"],
    )


def _question(row: sqlite3.Row) -> QuestionRow:
    return QuestionRow(
        id=row["id"],
        pack_id=row["pack_id"],
        category=row["category"],
        prompt=row["prompt"],
        choices=json.loads(row["choices_json"]),
        correct_index=row["correct_index"],
    )


def _round(row: sqlite3.Row) -> RoundRow:
    return RoundRow(
        id=row["id"],
        room_id=row["room_id"],
        round_number=row["round_number"],
        question_id=row["question_id"],
        status=row["status"],
        phase_ends_at=row["phase_ends_at"],
    )


class RoomRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def commit(self) -> None:
        """End the open transaction (e.g. before third-party HTTP)."""
        self._conn.commit()

    def create_room(self, code: str, pack_id: str) -> RoomRow:
        cur = self._conn.execute(
            "INSERT INTO rooms (code, status, pack_id) VALUES (?, 'lobby', ?)",
            (code, pack_id),
        )
        row = self._conn.execute(
            f"SELECT {_ROOM_COLS} FROM rooms WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _room(row)

    def get_by_code(self, code: str) -> RoomRow | None:
        row = self._conn.execute(
            f"SELECT {_ROOM_COLS} FROM rooms WHERE code = ?",
            (code.upper(),),
        ).fetchone()
        return _room(row) if row else None

    def get_by_id(self, room_id: int) -> RoomRow | None:
        row = self._conn.execute(
            f"SELECT {_ROOM_COLS} FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
        return _room(row) if row else None

    def set_host(self, room_id: int, player_id: int) -> None:
        self._conn.execute(
            "UPDATE rooms SET host_player_id = ? WHERE id = ?",
            (player_id, room_id),
        )

    def set_status(self, room_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE rooms SET status = ? WHERE id = ?",
            (status, room_id),
        )

    def claim_status(self, room_id: int, *, from_status: str, to_status: str) -> bool:
        """Conditional status transition. True only for the winning claim (ARCH-039)."""
        cur = self._conn.execute(
            "UPDATE rooms SET status = ? WHERE id = ? AND status = ?",
            (to_status, room_id, from_status),
        )
        return cur.rowcount == 1

    def set_current_round(self, room_id: int, round_number: int) -> None:
        self._conn.execute(
            "UPDATE rooms SET current_round = ? WHERE id = ?",
            (round_number, room_id),
        )

    def add_player(
        self,
        room_id: int,
        display_name: str,
        *,
        is_host: bool,
    ) -> tuple[PlayerRow, str]:
        """Insert player. Returns (row, plaintext bearer token) — never stored raw."""
        raw_token = new_token()
        token_hash = hash_token(raw_token)
        cur = self._conn.execute(
            """
            INSERT INTO players (room_id, display_name, token_hash, is_host)
            VALUES (?, ?, ?, ?)
            """,
            (room_id, display_name, token_hash, 1 if is_host else 0),
        )
        row = self._conn.execute(
            f"SELECT {_PLAYER_COLS} FROM players WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _player(row), raw_token

    def invalidate_player_token(self, player_id: int) -> None:
        """Burn the stored hash so prior Bearer/cookie secrets stop matching."""
        burned = hash_token(new_token())
        self._conn.execute(
            "UPDATE players SET token_hash = ? WHERE id = ?",
            (burned, player_id),
        )

    def list_players(self, room_id: int) -> list[PlayerRow]:
        rows = self._conn.execute(
            f"SELECT {_PLAYER_COLS} FROM players WHERE room_id = ? ORDER BY id",
            (room_id,),
        ).fetchall()
        return [_player(r) for r in rows]

    def get_player_by_token(self, raw_token: str) -> PlayerRow | None:
        row = self._conn.execute(
            f"SELECT {_PLAYER_COLS} FROM players WHERE token_hash = ?",
            (hash_token(raw_token),),
        ).fetchone()
        return _player(row) if row else None

    def get_player(self, player_id: int) -> PlayerRow | None:
        row = self._conn.execute(
            f"SELECT {_PLAYER_COLS} FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()
        return _player(row) if row else None

    def pick_question(self, pack_id: str, exclude_ids: list[int]) -> QuestionRow | None:
        if exclude_ids:
            placeholders = ",".join("?" for _ in exclude_ids)
            row = self._conn.execute(
                f"""
                SELECT {_QUESTION_COLS} FROM questions
                WHERE pack_id = ? AND id NOT IN ({placeholders})
                ORDER BY RANDOM()
                LIMIT 1
                """,
                [pack_id, *exclude_ids],
            ).fetchone()
        else:
            row = self._conn.execute(
                f"""
                SELECT {_QUESTION_COLS} FROM questions
                WHERE pack_id = ?
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (pack_id,),
            ).fetchone()
        return _question(row) if row else None

    def count_questions(self, pack_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM questions WHERE pack_id = ?",
            (pack_id,),
        ).fetchone()
        return int(row["c"])

    def insert_questions(
        self,
        *,
        pack_id: str,
        category: str,
        questions: list[tuple[str, list[str], int]],
    ) -> int:
        """Insert questions; skip duplicates by (pack_id, prompt). Returns inserted count."""
        inserted = 0
        for prompt, choices, correct_index in questions:
            cur = self._conn.execute(
                """
                INSERT OR IGNORE INTO questions
                    (pack_id, category, prompt, choices_json, correct_index)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pack_id, category, prompt, json.dumps(choices), correct_index),
            )
            inserted += cur.rowcount
        return inserted

    def used_question_ids(self, room_id: int) -> list[int]:
        rows = self._conn.execute(
            "SELECT question_id FROM rounds WHERE room_id = ?",
            (room_id,),
        ).fetchall()
        return [int(r["question_id"]) for r in rows]

    def create_round(
        self,
        room_id: int,
        round_number: int,
        question_id: int,
        phase_ends_at: str,
    ) -> RoundRow | None:
        """Insert open round. None if (room_id, round_number) already exists (race loser)."""
        cur = self._conn.execute(
            """
            INSERT OR IGNORE INTO rounds
                (room_id, round_number, question_id, status, phase_ends_at)
            VALUES (?, ?, ?, 'open', ?)
            """,
            (room_id, round_number, question_id, phase_ends_at),
        )
        if cur.rowcount != 1:
            return None
        row = self._conn.execute(
            f"SELECT {_ROUND_COLS} FROM rounds WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _round(row)

    def get_round(self, room_id: int, round_number: int) -> RoundRow | None:
        row = self._conn.execute(
            f"""
            SELECT {_ROUND_COLS} FROM rounds
            WHERE room_id = ? AND round_number = ?
            """,
            (room_id, round_number),
        ).fetchone()
        return _round(row) if row else None

    def get_round_by_id(self, round_id: int) -> RoundRow | None:
        row = self._conn.execute(
            f"SELECT {_ROUND_COLS} FROM rounds WHERE id = ?",
            (round_id,),
        ).fetchone()
        return _round(row) if row else None

    def get_question(self, question_id: int) -> QuestionRow:
        row = self._conn.execute(
            f"SELECT {_QUESTION_COLS} FROM questions WHERE id = ?",
            (question_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"missing question id={question_id}")
        return _question(row)

    def upsert_answer(self, round_id: int, player_id: int, choice_index: int) -> bool:
        """Insert answer. Returns False if already answered (idempotent no-op)."""
        cur = self._conn.execute(
            """
            INSERT OR IGNORE INTO answers (round_id, player_id, choice_index)
            VALUES (?, ?, ?)
            """,
            (round_id, player_id, choice_index),
        )
        return cur.rowcount == 1

    def has_answer(self, round_id: int, player_id: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM answers WHERE round_id = ? AND player_id = ?",
            (round_id, player_id),
        ).fetchone()
        return row is not None

    def list_answers(self, round_id: int) -> list[tuple[int, int]]:
        rows = self._conn.execute(
            "SELECT player_id, choice_index FROM answers WHERE round_id = ?",
            (round_id,),
        ).fetchall()
        return [(int(r["player_id"]), int(r["choice_index"])) for r in rows]

    def claim_round_scored(self, round_id: int, phase_ends_at: str) -> bool:
        """Atomically claim an open round for scoring. True only for the winning claim."""
        cur = self._conn.execute(
            """
            UPDATE rounds
            SET status = 'scored', phase_ends_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (phase_ends_at, round_id),
        )
        return cur.rowcount == 1

    def set_phase_ends_at(self, round_id: int, phase_ends_at: str) -> None:
        self._conn.execute(
            "UPDATE rounds SET phase_ends_at = ? WHERE id = ?",
            (phase_ends_at, round_id),
        )

    def add_score(self, player_id: int, points: int) -> None:
        self._conn.execute(
            "UPDATE players SET score = score + ? WHERE id = ?",
            (points, player_id),
        )
