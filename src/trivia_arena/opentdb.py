from __future__ import annotations

import html
import random
from typing import Any

import httpx

from trivia_arena.packs_catalog import PackQuestion

OTDB_URL = "https://opentdb.com/api.php"


def fetch_opentdb_questions(
    *,
    amount: int = 10,
    client: httpx.Client | None = None,
) -> list[PackQuestion]:
    """Fetch multiple-choice questions from Open Trivia DB and normalize."""
    owns_client = client is None
    http = client or httpx.Client(timeout=10.0)
    try:
        response = http.get(
            OTDB_URL,
            params={"amount": amount, "type": "multiple"},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    finally:
        if owns_client:
            http.close()

    if int(payload.get("response_code", -1)) != 0:
        raise RuntimeError(f"Open Trivia DB error code={payload.get('response_code')}")

    out: list[PackQuestion] = []
    for item in payload.get("results", []):
        prompt = html.unescape(str(item["question"]))
        correct = html.unescape(str(item["correct_answer"]))
        incorrect = [html.unescape(str(x)) for x in item["incorrect_answers"]]
        choices = incorrect + [correct]
        random.shuffle(choices)
        # OTDB multiple always has 4 answers (1 correct + 3 incorrect).
        if len(choices) != 4:
            continue
        out.append(
            PackQuestion(
                prompt=prompt,
                choices=choices,
                correct_index=choices.index(correct),
            )
        )
    return out
