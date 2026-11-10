from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class RoomRow:
    id: int
    code: str
    status: str
    host_player_id: int | None
    current_round: int


@dataclass(frozen=True)
class PlayerRow:
    id: int
    room_id: int
    display_name: str
    token: str
    is_host: bool
    score: int


@dataclass(frozen=True)
class QuestionRow:
    id: int
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
    )


def _player(row: sqlite3.Row) -> PlayerRow:
    return PlayerRow(
        id=row["id"],
        room_id=row["room_id"],
        display_name=row["display_name"],
        token=row["token"],
        is_host=bool(row["is_host"]),
        score=row["score"],
    )


def _question(row: sqlite3.Row) -> QuestionRow:
    return QuestionRow(
        id=row["id"],
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

    def create_room(self, code: str) -> RoomRow:
        cur = self._conn.execute(
            "INSERT INTO rooms (code, status) VALUES (?, 'lobby')",
            (code,),
        )
        row = self._conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _room(row)

    def get_by_code(self, code: str) -> RoomRow | None:
        row = self._conn.execute(
            "SELECT * FROM rooms WHERE code = ?",
            (code.upper(),),
        ).fetchone()
        return _room(row) if row else None

    def get_by_id(self, room_id: int) -> RoomRow | None:
        row = self._conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
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

    def set_current_round(self, room_id: int, round_number: int) -> None:
        self._conn.execute(
            "UPDATE rooms SET current_round = ? WHERE id = ?",
            (round_number, room_id),
        )

    def add_player(self, room_id: int, display_name: str, *, is_host: bool) -> PlayerRow:
        token = secrets.token_urlsafe(24)
        cur = self._conn.execute(
            """
            INSERT INTO players (room_id, display_name, token, is_host)
            VALUES (?, ?, ?, ?)
            """,
            (room_id, display_name, token, 1 if is_host else 0),
        )
        row = self._conn.execute(
            "SELECT * FROM players WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _player(row)

    def list_players(self, room_id: int) -> list[PlayerRow]:
        rows = self._conn.execute(
            "SELECT * FROM players WHERE room_id = ? ORDER BY id",
            (room_id,),
        ).fetchall()
        return [_player(r) for r in rows]

    def get_player_by_token(self, token: str) -> PlayerRow | None:
        row = self._conn.execute(
            "SELECT * FROM players WHERE token = ?",
            (token,),
        ).fetchone()
        return _player(row) if row else None

    def get_player(self, player_id: int) -> PlayerRow | None:
        row = self._conn.execute(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()
        return _player(row) if row else None

    def pick_question(self, exclude_ids: list[int]) -> QuestionRow | None:
        if exclude_ids:
            placeholders = ",".join("?" for _ in exclude_ids)
            row = self._conn.execute(
                f"""
                SELECT * FROM questions
                WHERE id NOT IN ({placeholders})
                ORDER BY RANDOM()
                LIMIT 1
                """,
                exclude_ids,
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM questions ORDER BY RANDOM() LIMIT 1",
            ).fetchone()
        return _question(row) if row else None

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
    ) -> RoundRow:
        cur = self._conn.execute(
            """
            INSERT INTO rounds (room_id, round_number, question_id, status, phase_ends_at)
            VALUES (?, ?, ?, 'open', ?)
            """,
            (room_id, round_number, question_id, phase_ends_at),
        )
        row = self._conn.execute(
            "SELECT * FROM rounds WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _round(row)

    def get_round(self, room_id: int, round_number: int) -> RoundRow | None:
        row = self._conn.execute(
            """
            SELECT * FROM rounds
            WHERE room_id = ? AND round_number = ?
            """,
            (room_id, round_number),
        ).fetchone()
        return _round(row) if row else None

    def get_round_by_id(self, round_id: int) -> RoundRow | None:
        row = self._conn.execute(
            "SELECT * FROM rounds WHERE id = ?",
            (round_id,),
        ).fetchone()
        return _round(row) if row else None

    def get_question(self, question_id: int) -> QuestionRow:
        row = self._conn.execute(
            "SELECT * FROM questions WHERE id = ?",
            (question_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"missing question id={question_id}")
        return _question(row)

    def upsert_answer(self, round_id: int, player_id: int, choice_index: int) -> bool:
        """Insert answer. Returns False if already answered (idempotent no-op)."""
        existing = self._conn.execute(
            "SELECT id FROM answers WHERE round_id = ? AND player_id = ?",
            (round_id, player_id),
        ).fetchone()
        if existing:
            return False
        self._conn.execute(
            """
            INSERT INTO answers (round_id, player_id, choice_index)
            VALUES (?, ?, ?)
            """,
            (round_id, player_id, choice_index),
        )
        return True

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

    def mark_round_scored(self, round_id: int, phase_ends_at: str) -> None:
        self._conn.execute(
            """
            UPDATE rounds
            SET status = 'scored', phase_ends_at = ?
            WHERE id = ?
            """,
            (phase_ends_at, round_id),
        )

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
