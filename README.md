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

Open http://127.0.0.1:8000/ for the game UI (create/join, answer, countdown).

Swagger stays at http://127.0.0.1:8000/docs

Rounds auto-advance: 20s to answer, 5s reveal, or early when everyone has answered. Host **Force next** still skips the clock.

UI uses **1s short-poll** (no WebSockets yet). Auth for the browser is **HttpOnly `ta_session` + double-submit CSRF** (`ta_csrf` cookie + `X-CSRF-Token`). API/tests keep `Authorization: Bearer …` (CSRF skipped when Bearer is present).

### Split frontend (GitHub Pages) CORS

```powershell
$env:TRIVIA_CORS_ORIGINS = "https://alucard4159.github.io"
$env:TRIVIA_COOKIE_SECURE = "true"
$env:TRIVIA_COOKIE_SAMESITE = "none"   # cross-site cookies
# Only if a reverse proxy overwrites X-Forwarded-For:
# $env:TRIVIA_TRUST_PROXY = "true"
uv run trivia-arena
```

Same-origin (default) needs no CORS env vars. Create/join/lookup/actions are rate-limited per peer IP. `SameSite=none` requires `TRIVIA_COOKIE_SECURE=true` (enforced at startup).

## Question packs

Local JSON packs live under `src/trivia_arena/packs/` (`engineering`, `general`, `science`).

`open_trivia` fetches from [Open Trivia DB](https://opentdb.com/) on room create when the cache is thin, then stores rows in SQLite for reuse.

- `GET /api/packs` — pack catalog
- `POST /api/rooms` `{ "display_name": "Host", "pack_id": "science" }` — optional `pack_id` (default `engineering`)

## Flow

Browser: `GET /api/auth/csrf` → then POSTs with `X-CSRF-Token` (session cookie set on create/join).

API client:

1. `POST /api/rooms` `{ "display_name": "Host", "pack_id": "general" }` → `code` + `token` (+ cookies for browsers)
2. `POST /api/rooms/{code}/join` `{ "display_name": "Guest" }`
3. Host `POST /api/rooms/{code}/start` with `Authorization: Bearer …`
4. Players `POST /api/rooms/{code}/answer` `{ "choice_index": 0 }`
5. Host `POST /api/rooms/{code}/next` (or wait for timers)

`GET /api/rooms/{code}` returns lobby/meta publicly (roster only while lobby); live `question` / reveal / post-start roster require room membership. Logout burns the server-side token hash.

## Test

```powershell
uv run pytest
```

Security threat model + hardening notes: [SECURITY.md](SECURITY.md).

## Expand later

- WebSocket broadcasts for `round_opened` / `round_scored` only (REST stays source of truth)
- Idempotency keys on answer
- Hypothesis property tests for scoring
- Sysinfo collectors as a *separate* project once this stack is comfortable
