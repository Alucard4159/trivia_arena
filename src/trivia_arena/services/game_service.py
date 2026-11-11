from __future__ import annotations

import secrets
import sqlite3
import string
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from trivia_arena.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from trivia_arena.opentdb import fetch_opentdb_questions
from trivia_arena.packs_catalog import PackQuestion, get_pack, load_all_packs
from trivia_arena.repositories.room_repo import PlayerRow, RoomRepository, RoomRow, RoundRow
from trivia_arena.schemas.room import (
    AnswerReveal,
    JoinedOut,
    PackOut,
    PlayerPublic,
    QuestionPublic,
    RoomCreatedOut,
    RoomStateOut,
    RoundResult,
)

MAX_ROUNDS = 5
ROUND_SECONDS = 20
REVEAL_SECONDS = 5
OTDB_FETCH_AMOUNT = 12
DEFAULT_PACK_ID = "engineering"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    raw = value.removesuffix("Z")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _deadline(seconds: int, *, now: datetime | None = None) -> str:
    base = now if now is not None else _utc_now()
    return _iso(base + timedelta(seconds=seconds))


class GameService:
    def __init__(
        self,
        repo: RoomRepository,
        *,
        now_fn: Callable[[], datetime] | None = None,
        round_seconds: int = ROUND_SECONDS,
        reveal_seconds: int = REVEAL_SECONDS,
        otdb_fetch: Callable[[], list[PackQuestion]] | None = None,
    ) -> None:
        self._repo = repo
        self._now_fn = now_fn
        self._round_seconds = round_seconds
        self._reveal_seconds = reveal_seconds
        self._otdb_fetch = otdb_fetch

    def _now(self) -> datetime:
        return self._now_fn() if self._now_fn is not None else _utc_now()

    def list_packs(self) -> list[PackOut]:
        out: list[PackOut] = []
        for pack in load_all_packs():
            count = self._repo.count_questions(pack.id)
            if pack.source == "opentdb" and count == 0:
                # Not cached yet; still playable after create fetches.
                count = OTDB_FETCH_AMOUNT
            out.append(
                PackOut(
                    id=pack.id,
                    title=pack.title,
                    description=pack.description,
                    category=pack.category,
                    source=pack.source,
                    question_count=count,
                )
            )
        return out

    def create_room(
        self,
        display_name: str,
        *,
        pack_id: str = DEFAULT_PACK_ID,
    ) -> RoomCreatedOut:
        name = display_name.strip()
        if not name:
            raise ValidationDomainError("display_name required")

        pack = get_pack(pack_id)
        if pack is None:
            raise NotFoundError(f"pack not found: {pack_id}")

        self._ensure_pack_questions(pack.id)

        if self._repo.count_questions(pack.id) < MAX_ROUNDS:
            raise ConflictError(f"pack '{pack.id}' needs at least {MAX_ROUNDS} questions")

        for _ in range(8):
            code = _room_code()
            if self._repo.get_by_code(code) is None:
                break
        else:
            raise ConflictError("could not allocate room code")

        room = self._repo.create_room(code, pack.id)
        host, raw_token = self._repo.add_player(room.id, name, is_host=True)
        self._repo.set_host(room.id, host.id)
        return RoomCreatedOut(
            code=room.code,
            player_id=host.id,
            token=raw_token,
            is_host=True,
            pack_id=room.pack_id,
        )

    def _ensure_pack_questions(self, pack_id: str) -> None:
        pack = get_pack(pack_id)
        if pack is None:
            raise NotFoundError(f"pack not found: {pack_id}")
        if pack.source != "opentdb":
            return
        # Refresh cache when thin so rooms don't starve mid-game.
        if self._repo.count_questions(pack.id) >= MAX_ROUNDS:
            return
        fetch = self._otdb_fetch or (lambda: fetch_opentdb_questions(amount=OTDB_FETCH_AMOUNT))
        # End any open DB transaction before third-party HTTP (PY-230).
        self._repo.commit()
        try:
            fetched = fetch()
        except Exception as exc:
            raise ConflictError(f"failed to fetch Open Trivia DB questions: {exc}") from exc
        if not fetched:
            raise ConflictError("Open Trivia DB returned no questions")
        self._repo.insert_questions(
            pack_id=pack.id,
            category=pack.category,
            questions=[(q.prompt, q.choices, q.correct_index) for q in fetched],
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
            player, raw_token = self._repo.add_player(room.id, name, is_host=False)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("display_name already taken in room") from exc

        return JoinedOut(
            code=room.code,
            player_id=player.id,
            token=raw_token,
            is_host=False,
        )

    def get_state(self, code: str, viewer: PlayerRow | None) -> RoomStateOut:
        room = self._require_room(code)
        if room.status == "active":
            room = self._tick(room)
        return self._build_state(room, viewer)

    def start(self, code: str, actor: PlayerRow) -> RoomStateOut:
        room = self._require_room(code)
        self._require_host(actor, room.id)
        if len(self._repo.list_players(room.id)) < 1:
            raise ConflictError("need at least one player")
        # Claim lobby→active before opening round 1 so concurrent starts cannot 500.
        if not self._repo.claim_status(room.id, from_status="lobby", to_status="active"):
            raise ConflictError("room already started")
        self._open_next_round(room.id, next_number=1)
        room = self._require_room(code)
        return self._build_state(room, actor)

    def answer(self, code: str, actor: PlayerRow, choice_index: int) -> RoomStateOut:
        room = self._require_room(code)
        if room.status == "active":
            room = self._tick(room)

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
        room = self._tick(self._require_room(code))
        return self._build_state(room, actor)

    def next_round(self, code: str, actor: PlayerRow) -> RoomStateOut:
        room = self._require_room(code)
        self._require_host(actor, room.id)
        if room.status == "active":
            room = self._tick(room)

        if room.status != "active":
            raise ConflictError("room not active")

        rnd = self._repo.get_round(room.id, room.current_round)
        if rnd is None:
            raise ConflictError("no current round")

        # Host force: skip remaining answer/reveal time and advance.
        if rnd.status == "open":
            self._score_round(rnd.id, reveal_seconds=0)
            rnd = self._repo.get_round_by_id(rnd.id)
            if rnd is None:
                raise ConflictError("round disappeared during score")

        if room.current_round >= MAX_ROUNDS:
            self._repo.claim_status(room.id, from_status="active", to_status="finished")
            room = self._require_room(code)
            return self._build_state(room, actor)

        self._open_next_round(room.id, next_number=room.current_round + 1)
        room = self._require_room(code)
        return self._build_state(room, actor)

    def _tick(self, room: RoomRow) -> RoomRow:
        if room.status != "active":
            return room

        # Loop: open→scored and scored→next can both fire if clocks are past both.
        for _ in range(MAX_ROUNDS + 2):
            room = self._require_room_by_id(room.id)
            if room.status != "active":
                return room

            rnd = self._repo.get_round(room.id, room.current_round)
            if rnd is None:
                return room

            now = self._now()
            if rnd.status == "open":
                deadline_passed = (
                    rnd.phase_ends_at is not None and now >= _parse_iso(rnd.phase_ends_at)
                )
                if deadline_passed or self._all_answered(room.id, rnd):
                    self._score_round(rnd.id, reveal_seconds=self._reveal_seconds)
                    continue
                return room

            if rnd.status == "scored":
                reveal_done = (
                    rnd.phase_ends_at is not None and now >= _parse_iso(rnd.phase_ends_at)
                )
                if not reveal_done:
                    return room
                if room.current_round >= MAX_ROUNDS:
                    self._repo.claim_status(
                        room.id, from_status="active", to_status="finished"
                    )
                    return self._require_room_by_id(room.id)
                self._open_next_round(room.id, next_number=room.current_round + 1)
                continue

            return room

        return self._require_room_by_id(room.id)

    def _all_answered(self, room_id: int, rnd: RoundRow) -> bool:
        players = self._repo.list_players(room_id)
        if not players:
            return False
        return all(self._repo.has_answer(rnd.id, p.id) for p in players)

    def _score_round(self, round_id: int, *, reveal_seconds: int) -> None:
        rnd = self._repo.get_round_by_id(round_id)
        if rnd is None or rnd.status != "open":
            return
        ends = _deadline(reveal_seconds, now=self._now())
        # Claim first so concurrent ticks cannot double-award points.
        if not self._repo.claim_round_scored(round_id, ends):
            return
        question = self._repo.get_question(rnd.question_id)
        for player_id, choice_index in self._repo.list_answers(round_id):
            if choice_index == question.correct_index:
                self._repo.add_score(player_id, 1)

    def _open_next_round(self, room_id: int, *, next_number: int) -> None:
        room = self._require_room_by_id(room_id)
        used = self._repo.used_question_ids(room_id)
        question = self._repo.pick_question(room.pack_id, used)
        if question is None:
            self._repo.claim_status(room_id, from_status="active", to_status="finished")
            return
        ends = _deadline(self._round_seconds, now=self._now())
        created = self._repo.create_round(room_id, next_number, question.id, ends)
        if created is None:
            # Lost race with another tick/next — winner already owns this round_number.
            return
        self._repo.set_current_round(room_id, next_number)

    def _build_state(self, room: RoomRow, viewer: PlayerRow | None) -> RoomStateOut:
        member = viewer is not None and viewer.room_id == room.id
        # Lobby player list stays public for join UX. After start, roster/scores are
        # members-only (closes scoreboard peek via leaked code).
        if member or room.status == "lobby":
            players = [
                PlayerPublic(
                    id=p.id,
                    display_name=p.display_name,
                    is_host=p.is_host,
                    score=p.score,
                )
                for p in self._repo.list_players(room.id)
            ]
        else:
            players = []

        question: QuestionPublic | None = None
        your_answered: bool | None = None
        phase_ends_at: str | None = None
        last_result: RoundResult | None = None

        # Live prompts and reveal payloads are members-only.
        if viewer is not None and viewer.room_id == room.id and room.current_round > 0:
            rnd = self._repo.get_round(room.id, room.current_round)
            if rnd is not None:
                phase_ends_at = rnd.phase_ends_at
                if rnd.status == "open" and room.status == "active":
                    q = self._repo.get_question(rnd.question_id)
                    question = QuestionPublic(
                        prompt=q.prompt,
                        choices=q.choices,
                        round_number=rnd.round_number,
                    )
                    your_answered = self._repo.has_answer(rnd.id, viewer.id)
                elif rnd.status == "scored":
                    last_result = self._build_result(room.id, rnd)

        return RoomStateOut(
            code=room.code,
            status=room.status,  # type: ignore[arg-type]
            current_round=room.current_round,
            pack_id=room.pack_id,
            players=players,
            question=question,
            your_answered=your_answered,
            phase_ends_at=phase_ends_at,
            last_result=last_result,
        )

    def _build_result(self, room_id: int, rnd: RoundRow) -> RoundResult:
        q = self._repo.get_question(rnd.question_id)
        answers_by_player = dict(self._repo.list_answers(rnd.id))
        reveals: list[AnswerReveal] = []
        for player in self._repo.list_players(room_id):
            choice = answers_by_player.get(player.id)
            reveals.append(
                AnswerReveal(
                    player_id=player.id,
                    display_name=player.display_name,
                    choice_index=choice,
                    correct=choice is not None and choice == q.correct_index,
                )
            )
        return RoundResult(
            round_number=rnd.round_number,
            prompt=q.prompt,
            choices=q.choices,
            correct_index=q.correct_index,
            answers=reveals,
        )

    def _require_room(self, code: str) -> RoomRow:
        room = self._repo.get_by_code(code)
        if room is None:
            raise NotFoundError("room not found")
        return room

    def _require_room_by_id(self, room_id: int) -> RoomRow:
        # Rooms are looked up by code in public API; re-fetch via players' room is awkward.
        # Use code from a lightweight query through repo by scanning — add get_by_id.
        room = self._repo.get_by_id(room_id)
        if room is None:
            raise NotFoundError("room not found")
        return room

    def _require_host(self, actor: PlayerRow, room_id: int) -> None:
        if actor.room_id != room_id or not actor.is_host:
            raise ForbiddenError("host only")


def _room_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))
