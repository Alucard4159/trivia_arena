# Security notes — Trivia Arena

Training project threat model and hardening log. Scope is a small FastAPI + SQLite multiplayer trivia API with a static browser client.

## Assets

| Asset | Why it matters |
| --- | --- |
| Room codes (6-char) | Capability to join a lobby |
| Bearer player tokens | Prove identity / host powers for a room |
| SQLite DB file | Scores, answers, cached questions, token hashes |
| Game phase transitions | Fair scoring; no double credit |

## Actors

- **Host** — creates room, starts game, can force-next.
- **Player** — joins by code + display name; answers while authenticated.
- **Anonymous client** — can list packs / probe codes within rate limits; mutating calls need CSRF bootstrap.
- **DB reader** — anyone with filesystem access to `data/trivia.db`.

## Trust boundaries

1. Browser → HTTP API via **HttpOnly `ta_session`** + **double-submit CSRF** (`ta_csrf` cookie mirrored in `X-CSRF-Token`). Non-secret room meta may sit in `sessionStorage`.
2. API clients → same API with **`Authorization: Bearer`** (CSRF skipped).
3. API → SQLite (parameterized SQL only; no ORM).
4. API → Open Trivia DB (optional pack fetch; untrusted input, HTML-unescaped then stored).
5. Optional split origin (Pages ↔ API) via allowlisted CORS + `SameSite=None; Secure` cookies.

Out of scope: multi-worker rate-limit sharing, TLS termination, admin auth, WebSockets.

## Threats and controls

### 1. Double-scoring race (integrity)

**Issue:** Lazy phase advances run on `GET`/`answer`/`next`. Two concurrent requests could both observe `rounds.status = 'open'`, both award points, then both mark scored.

**Fix:** Claim with a conditional update before mutating scores:

```sql
UPDATE rounds
SET status = 'scored', phase_ends_at = ?
WHERE id = ? AND status = 'open'
```

Only the connection with `rowcount == 1` adds points. Covered by `tests/test_security.py::test_concurrent_score_awards_once`.

### 2. Duplicate answer insert (availability / clean errors)

**Issue:** Check-then-insert on answers raced a double-click into the `UNIQUE (round_id, player_id)` constraint → 500.

**Fix:** `INSERT OR IGNORE` and treat `rowcount == 0` as idempotent no-op. First answer wins; no overwrite.

### 3. Stolen DB → impersonation (confidentiality)

**Issue:** Bearer tokens were stored plaintext in `players.token`. DB exfil = full account takeover for every player.

**Fix:** Store `token_hash = SHA-256(raw_token)` only. Raw token returned once at create/join; lookups hash the presented Bearer. Migration hashes legacy plaintext rows when upgrading older DBs.

Residual risk: SHA-256 without per-token salt is fine for high-entropy `token_urlsafe(24)` secrets; do not reuse this pattern for passwords.

### 4. Room-code brute force (unauthorized join / recon)

**Issue:** 6-char codes over `[A-Z0-9]` are guessable under unbounded `join` / `GET` traffic.

**Fix:** In-process sliding-window rate limits per client IP (or first `X-Forwarded-For` hop):

- Join: 20 / minute (default)
- Room lookup: 120 / minute (default; allows ~1 Hz UI polling with headroom)

Return `429` + `Retry-After: 60`. Limits are configurable in `create_app(...)` for tests / deploy.

Residual risk: limiter is per-process memory (not shared across workers); spoofable `X-Forwarded-For` unless the reverse proxy overwrites it. Bind to proxy-trusted IP in production.

### 5. Browser XSS / CSRF

**Issue:** Putting bearer tokens in `localStorage` made XSS equal to full account takeover; cookie sessions without CSRF enable cross-site state changes.

**Fix:**

- Session secret in HttpOnly `ta_session` (not JS-readable).
- CSRF double-submit: readable `ta_csrf` + required `X-CSRF-Token` on unsafe methods when not using Bearer.
- UI keeps only `{code, is_host, player_id}` in `sessionStorage`.
- `GET /api/auth/csrf`, `POST /api/auth/logout`.

### 6. Split-origin hosting

**Issue:** GitHub Pages + separate API needs credentialed CORS without reflecting arbitrary `Origin`.

**Fix:** CORS middleware only when `TRIVIA_CORS_ORIGINS` / `create_app(cors_origins=…)` is set; credentials allowed; methods/headers allowlisted. Cross-site cookies need `TRIVIA_COOKIE_SAMESITE=none` + `TRIVIA_COOKIE_SECURE=true`.

## What we tested

| Test | Intent |
| --- | --- |
| `test_concurrent_score_awards_once` | Two threads score one open round → score == 1 |
| `test_duplicate_answer_is_idempotent` | Re-answer returns 200, no 500 |
| `test_tokens_hashed_at_rest` | DB holds SHA-256, not raw bearer |
| `test_join_rate_limit` / `test_lookup_rate_limit` | Over-limit → 429 |
| `test_bearer_skips_csrf` | API Bearer path works without CSRF header |
| `test_cookie_auth_requires_csrf` / `test_cookie_auth_with_csrf` | Cookie mutations gated by CSRF |
| `test_cors_origins_configured` | Allowlisted origin only |
| Existing game-flow / packs / phase suites | Regressions |

## Explicit non-goals (still open)

- Shared rate limit store (Redis) for multi-worker hosts
- Room TTL / GC against abandoned lobbies
- Formal CAPTCHA or proof-of-work on create/join
- Signing or binding tokens to room id / IP
- WebSocket presence channel

## Operator notes

- Prefer a single app worker with SQLite WAL (enabled on connect).
- Put TLS and a real client-IP strategy at the reverse proxy.
- Treat `data/*.db` as sensitive even with hashed tokens (scores / answers still PII-adjacent).
