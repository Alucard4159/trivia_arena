from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

PACKS_DIR = Path(__file__).parent / "packs"

PackSource = Literal["local", "opentdb"]


@dataclass(frozen=True)
class PackQuestion:
    prompt: str
    choices: list[str]
    correct_index: int


@dataclass(frozen=True)
class PackMeta:
    id: str
    title: str
    description: str
    category: str
    source: PackSource
    questions: list[PackQuestion]


def _as_pack(data: dict[str, Any]) -> PackMeta:
    source = data.get("source", "local")
    if source not in ("local", "opentdb"):
        raise ValueError(f"unknown pack source: {source}")
    questions: list[PackQuestion] = []
    for raw in data.get("questions", []):
        choices = list(raw["choices"])
        if len(choices) != 4:
            raise ValueError(f"pack {data['id']}: expected 4 choices")
        correct_index = int(raw["correct_index"])
        if correct_index < 0 or correct_index >= 4:
            raise ValueError(f"pack {data['id']}: correct_index out of range")
        questions.append(
            PackQuestion(
                prompt=str(raw["prompt"]),
                choices=choices,
                correct_index=correct_index,
            )
        )
    return PackMeta(
        id=str(data["id"]),
        title=str(data["title"]),
        description=str(data["description"]),
        category=str(data["category"]),
        source=source,  # type: ignore[arg-type]
        questions=questions,
    )


def load_all_packs() -> list[PackMeta]:
    packs: list[PackMeta] = []
    for path in sorted(PACKS_DIR.glob("*.json")):
        packs.append(_as_pack(json.loads(path.read_text(encoding="utf-8"))))
    return packs


def get_pack(pack_id: str) -> PackMeta | None:
    for pack in load_all_packs():
        if pack.id == pack_id:
            return pack
    return None
