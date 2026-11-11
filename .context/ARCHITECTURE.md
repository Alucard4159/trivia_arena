# Architecture

> **Context Safety:** No secrets in this file.

Last updated: 2026-11-10

## Shape

- **API:** FastAPI app in `src/trivia_arena/` — layered `api/` → `services/` → `repositories/` → SQLite
- **UI:** Static files under `src/trivia_arena/static/` served at `/` and `/static`
- **Auth:** Dual — HttpOnly `ta_session` + CSRF double-submit for browser; `Authorization: Bearer` for API/tests (CSRF skipped). Logout burns `token_hash`.
- **Room visibility:** Lobby/meta public (rate-limited); roster public only in lobby; live question + reveal + post-start roster are room-member-only
- **Game phases:** Lobby → open round → scored reveal → next/finish; lazy `_tick`; atomic `claim_round_scored` + `claim_status` + idempotent `create_round`
- **Content:** JSON packs in `src/trivia_arena/packs/`; `open_trivia` commits DB then fetches/caches via httpx (length-capped)
- **Limits:** create / join / lookup / action (start|answer|next) in-process sliding windows; `SameSite=none` requires Secure

## Key entrypoints

| Path | Role |
|------|------|
| `src/trivia_arena/app.py` | App factory, CORS, rate limiters, SameSite gate, lifespan DB init |
| `src/trivia_arena/api/rooms.py` | Room create/join/play + rate limits |
| `src/trivia_arena/api/auth.py` | CSRF issue, session peek, logout (+ token invalidate) |
| `src/trivia_arena/services/game_service.py` | Game rules / tick / packs / member-gated state |
| `src/trivia_arena/db.py` | Schema, migrate, seed packs, token scrub |

## Data

- SQLite file (default `data/trivia.db`); WAL; `token_hash` only at rest
