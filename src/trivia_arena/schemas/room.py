from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateRoomIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=32)


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


class RoomStateOut(BaseModel):
    code: str
    status: Literal["lobby", "active", "finished"]
    current_round: int
    players: list[PlayerPublic]
    question: QuestionPublic | None = None
    your_answered: bool | None = None


class RoomCreatedOut(BaseModel):
    code: str
    player_id: int
    token: str
    is_host: bool


class JoinedOut(BaseModel):
    code: str
    player_id: int
    token: str
    is_host: bool
