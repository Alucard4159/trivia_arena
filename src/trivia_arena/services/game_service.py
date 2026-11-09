from __future__ import annotations

import secrets
import sqlite3
import string

from trivia_arena.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from trivia_arena.repositories.room_repo import PlayerRow, RoomRepository
from trivia_arena.schemas.room import (
    JoinedOut,
    PlayerPublic,
    QuestionPublic,
    RoomCreatedOut,
    RoomStateOut,
)

MAX_ROUNDS = 5


def _room_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


class GameService:
    def __init__(self, repo: RoomRepository) -> None:
        self._repo = repo

    def create_room(self, display_name: str) -> RoomCreatedOut:
        name = display_name.strip()
        if not name:
            raise ValidationDomainError("display_name required")

        for _ in range(8):
            code = _room_code()
            if self._repo.get_by_code(code) is None:
                break
        else:
            raise ConflictError("could not allocate room code")

        room = self._repo.create_room(code)
        host = self._repo.add_player(room.id, name, is_host=True)
        self._repo.set_host(room.id, host.id)
        return RoomCreatedOut(
            code=room.code,
            player_id=host.id,
            token=host.token,
            is_host=True,
        )

    def join_room(self, code: str, display_name: str) -> JoinedOut:
        name = display_name.strip()
        if not name:
            raise ValidationDomainError("display_name required")

        room = self._repo.get_by_code(code)
        if room is None:
            raise NotFoundError("room not found")
        if room.status != "lobby":
            raise ConflictError("room already started")

        try:
            player = self._repo.add_player(room.id, name, is_host=False)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("display_name already taken in room") from exc

        return JoinedOut(
            code=room.code,
            player_id=player.id,
            token=player.token,
            is_host=False,
        )

    def get_state(self, code: str, viewer: PlayerRow | None) -> RoomStateOut:
        room = self._repo.get_by_code(code)
        if room is None:
            raise NotFoundError("room not found")

        players = [
            PlayerPublic(
                id=p.id,
                display_name=p.display_name,
                is_host=p.is_host,
                score=p.score,
            )
            for p in self._repo.list_players(room.id)
        ]

        question: QuestionPublic | None = None
        your_answered: bool | None = None

        if room.status == "active" and room.current_round > 0:
            rnd = self._repo.get_round(room.id, room.current_round)
            if rnd is not None and rnd.status == "open":
                q = self._repo.get_question(rnd.question_id)
                question = QuestionPublic(
                    prompt=q.prompt,
                    choices=q.choices,
                    round_number=rnd.round_number,
                )
                if viewer is not None and viewer.room_id == room.id:
                    your_answered = self._repo.has_answer(rnd.id, viewer.id)

        return RoomStateOut(
            code=room.code,
            status=room.status,  # type: ignore[arg-type]
            current_round=room.current_round,
            players=players,
            question=question,
            your_answered=your_answered,
        )

    def start(self, code: str, actor: PlayerRow) -> RoomStateOut:
        room = self._require_room(code)
        self._require_host(actor, room.id)
        if room.status != "lobby":
            raise ConflictError("room already started")
        if len(self._repo.list_players(room.id)) < 1:
            raise ConflictError("need at least one player")

        self._open_next_round(room.id, next_number=1)
        self._repo.set_status(room.id, "active")
        return self.get_state(code, actor)

    def answer(self, code: str, actor: PlayerRow, choice_index: int) -> RoomStateOut:
        room = self._require_room(code)
        if actor.room_id != room.id:
            raise ForbiddenError("player not in this room")
        if room.status != "active":
            raise ConflictError("room not accepting answers")

        rnd = self._repo.get_round(room.id, room.current_round)
        if rnd is None or rnd.status != "open":
            raise ConflictError("no open round")

        q = self._repo.get_question(rnd.question_id)
        if choice_index < 0 or choice_index >= len(q.choices):
            raise ValidationDomainError("choice_index out of range")

        # First answer wins; repeats are idempotent no-ops (no overwrite).
        self._repo.upsert_answer(rnd.id, actor.id, choice_index)
        return self.get_state(code, actor)

    def next_round(self, code: str, actor: PlayerRow) -> RoomStateOut:
        room = self._require_room(code)
        self._require_host(actor, room.id)
        if room.status != "active":
            raise ConflictError("room not active")

        rnd = self._repo.get_round(room.id, room.current_round)
        if rnd is None:
            raise ConflictError("no current round")
        if rnd.status == "open":
            self._score_round(rnd.id)

        if room.current_round >= MAX_ROUNDS:
            self._repo.set_status(room.id, "finished")
            return self.get_state(code, actor)

        self._open_next_round(room.id, next_number=room.current_round + 1)
        return self.get_state(code, actor)

    def _score_round(self, round_id: int) -> None:
        rnd = self._repo.get_round_by_id(round_id)
        if rnd is None:
            return
        question = self._repo.get_question(rnd.question_id)
        for player_id, choice_index in self._repo.list_answers(round_id):
            if choice_index == question.correct_index:
                self._repo.add_score(player_id, 1)
        self._repo.mark_round_scored(round_id)

    def _open_next_round(self, room_id: int, *, next_number: int) -> None:
        used = self._repo.used_question_ids(room_id)
        question = self._repo.pick_question(used)
        if question is None:
            self._repo.set_status(room_id, "finished")
            return
        self._repo.create_round(room_id, next_number, question.id)
        self._repo.set_current_round(room_id, next_number)

    def _require_room(self, code: str):
        room = self._repo.get_by_code(code)
        if room is None:
            raise NotFoundError("room not found")
        return room

    def _require_host(self, actor: PlayerRow, room_id: int) -> None:
        if actor.room_id != room_id or not actor.is_host:
            raise ForbiddenError("host only")
