from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateRoomIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=32)
    pack_id: str = Field(default="engineering", min_length=1, max_length=64)


class PackOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    source: str
    question_count: int


class JoinRoomIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=32)


class AnswerIn(BaseModel):
    choice_index: int = Field(ge=0, le=3)


class PlayerPublic(BaseModel):
    id: int
    display_name: str
    is_host: bool
    score: int


class QuestionPublic(BaseModel):
    prompt: str
    choices: list[str]
    round_number: int


class AnswerReveal(BaseModel):
    player_id: int
    display_name: str
    choice_index: int | None
    correct: bool


class RoundResult(BaseModel):
    round_number: int
    prompt: str
    choices: list[str]
    correct_index: int
    answers: list[AnswerReveal]


class RoomStateOut(BaseModel):
    code: str
    status: Literal["lobby", "active", "finished"]
    current_round: int
    pack_id: str
    players: list[PlayerPublic]
    question: QuestionPublic | None = None
    your_answered: bool | None = None
    phase_ends_at: str | None = None
    last_result: RoundResult | None = None


class RoomCreatedOut(BaseModel):
    code: str
    player_id: int
    token: str
    is_host: bool
    pack_id: str


class JoinedOut(BaseModel):
    code: str
    player_id: int
    token: str
    is_host: bool

