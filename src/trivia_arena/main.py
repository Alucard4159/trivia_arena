from __future__ import annotations

import uvicorn

from trivia_arena.app import create_app

app = create_app()


def main() -> None:
    uvicorn.run("trivia_arena.main:app", host="127.0.0.1", port=8000, reload=True)
