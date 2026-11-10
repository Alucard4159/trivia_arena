# python — project config

## Scope

- Apply Python Engineering Standards to `trivia_arena` (FastAPI + Pydantic v2 + parameterized SQLite, no ORM).
- Runtime: Python 3.12, package manager `uv`.
- App package: `src/trivia_arena/`.

## Search / paths

- Source: `src/trivia_arena/`
- Tests: `tests/`
- Static UI: `src/trivia_arena/static/`
- Question packs: `src/trivia_arena/packs/`

## Constraints

- No ORM; SQL stays in repositories.
- Prefer layered routes → services → repositories.
- Do not commit `.venv/`, `data/*.db`, or secrets.
