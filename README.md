# Trivia Arena

Turn-based multiplayer trivia API. Training project for [Python Engineering Standards](../../../AI_Packs/Python_Engineering_Standards) — FastAPI, Pydantic v2, parameterized SQLite, layered routes → services → repositories.

## Setup

```powershell
cd "C:\Users\aluca\OneDrive\Documents\Training\Python Projects\trivia_arena"
uv sync --extra dev --system-certs
```

(`--system-certs` needed on this machine — corporate/AV TLS interception.)

## Run

```powershell
uv run trivia-arena
# or: uv run uvicorn trivia_arena.main:app --reload
```

Open http://127.0.0.1:8000/docs

## Flow

1. `POST /api/rooms` `{ "display_name": "Host" }` → `code` + Bearer `token`
2. `POST /api/rooms/{code}/join` `{ "display_name": "Guest" }`
3. Host `POST /api/rooms/{code}/start` with `Authorization: Bearer …`
4. Players `POST /api/rooms/{code}/answer` `{ "choice_index": 0 }`
5. Host `POST /api/rooms/{code}/next` (scores open round, opens next; finishes after 5)

`GET /api/rooms/{code}` returns lobby/active state. Pass Bearer to see `your_answered`.

## Test

```powershell
uv run pytest
```

## Expand later

- Cookie auth + CSRF for a browser client
- Question packs / categories
- WebSocket lobby presence
- Idempotency keys on answer
- Hypothesis property tests for scoring
- Sysinfo collectors as a *separate* project once this stack is comfortable
