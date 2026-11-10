# Architecture

> **Context Safety:** No secrets in this file.

Last updated: 2026-11-10

## Shape

- **API:** FastAPI app in `src/trivia_arena/` — layered `api/` → `services/` → `repositories/` → SQLite
- **UI:** Static files under `src/trivia_arena/static/` served at `/` and `/static`
- **Auth:** Dual — HttpOnly `ta_session` + CSRF double-submit for browser; `Authorization: Bearer` for API/tests (CSRF skipped)
- **Game phases:** Lobby → open round → scored reveal → next/finish; lazy `_tick` on reads/mutations; atomic `claim_round_scored`
- **Content:** JSON packs in `src/trivia_arena/packs/`; `open_trivia` fetches/caches via httpx

## Key entrypoints

| Path | Role |
|------|------|
| `src/trivia_arena/app.py` | App factory, CORS, rate limiters, lifespan DB init |
| `src/trivia_arena/api/rooms.py` | Room create/join/play + rate limits |
| `src/trivia_arena/api/auth.py` | CSRF issue, session peek, logout |
| `src/trivia_arena/services/game_service.py` | Game rules / tick / packs |
| `src/trivia_arena/db.py` | Schema, migrate, seed packs, token scrub |

## Data

- SQLite file (default `data/trivia.db`); WAL; `token_hash` only at rest
