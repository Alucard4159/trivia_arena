# Key Decisions Log

Newest first. Capture what was decided and why.

## 2026-11-10: Claim room status + idempotent create_round

**Decision**: `start` uses `claim_status(lobby→active)` before opening round 1; `create_round` is `INSERT OR IGNORE` returning `None` for the race loser; finish paths use `claim_status(active→finished)`.

**Rationale**: Check-then-act on start/next/`_tick` raced into unique `(room_id, round_number)` and 500'd (`ARCH-039`). Score already claimed; room/round opens now match.

**Tradeoff**: Winner that claims active then dies before creating round 1 leaves an active room with no round until a later recovery — rare; acceptable for demo SQLite.

## 2026-11-10: Member-only live prompts; public lobby meta

**Decision**: Unauthenticated `GET /api/rooms/{code}` returns code/status/pack; player roster is public only while `lobby`. After start, roster/scores plus `question`, `phase_ends_at`, `your_answered`, and `last_result` require room membership.

**Rationale**: A leaked room code must not be a live cheat feed or scoreboard peek. Join UX still needs lobby roster/meta.

**Tradeoff**: True spectators without joining cannot follow the round unless we later add an explicit spectator role. Create/join still mint raw `token` in JSON for Bearer API compat.

## 2026-11-10: Logout burns server-side token hash

**Decision**: `POST /api/auth/logout` invalidates `players.token_hash` (replace with a fresh unused hash) before clearing cookies.

**Rationale**: Cookie clear alone left create/join Bearer JSON tokens alive (`SEC-026`).

**Tradeoff**: No re-login for the same player row — they must re-join/create; acceptable for ephemeral trivia rooms.

## 2026-11-10: Reject SameSite=none without Secure at startup

**Decision**: `create_app` raises `ValueError` if `cookie_samesite=none` and `cookie_secure` is false (env or kwargs).

**Rationale**: Docs said "set both"; browsers require Secure with `SameSite=None` (`SEC-029`). Fail loud rather than ship broken cross-site cookies.

## 2026-11-10: Commit before OTDB HTTP in ensure-pack

**Decision**: When the Open Trivia cache is thin, `RoomRepository.commit()` runs before `fetch_opentdb_questions`, then inserts.

**Rationale**: Request-scoped SQLite must not hold an open transaction across third-party HTTP (PY-230 anti-pattern).

**Tradeoff**: Mid-request commit can leave cached OTDB rows even if later room create fails — acceptable (cache still useful).

## 2026-11-10: Context lives under trivia_arena; Cursor rules stay at workspace root

**Decision**: Full project `.context/` (including pack-configs for `context` / `python` / `secrev`) is owned by this repo. Always-on Cursor rules/hooks remain in the parent `Python Projects` workspace.

**Rationale**: This repo is its own git unit and needs durable project memory. The open Cursor workspace is the parent folder, so nested `.cursor/rules` would not load.

**Tradeoff**: Opening `trivia_arena` alone as a workspace skips root rules unless that folder gets its own Cursor top-up later.

## 2026-11-09: Dual auth — cookie+CSRF for browsers, Bearer for API/tests

**Decision**: HttpOnly `ta_session` + double-submit CSRF for the static UI; `Authorization: Bearer` still accepted and skips CSRF.

**Rationale**: Real page needs cookie security; Swagger/tests/API clients stay simple with Bearer.

**Tradeoff**: Two auth paths to keep correct; token still returned in JSON for API compat.

## 2026-11-09: Rate-limit identity ignores X-Forwarded-For unless trust_proxy

**Decision**: Default rate-limit key is the direct peer address; honor `X-Forwarded-For` only when `TRIVIA_TRUST_PROXY` / `trust_proxy=True`.

**Rationale**: Spoofable XFF otherwise bypasses join/lookup/create limits on a bare expose.

**Tradeoff**: Behind a real proxy you must opt in and ensure the proxy overwrites XFF.
