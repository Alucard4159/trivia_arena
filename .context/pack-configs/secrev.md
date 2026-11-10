# secrev — project config

## Scope

- Security review / remediation for **trivia_arena** (FastAPI multiplayer trivia API + static UI).
- Primary surfaces: auth (Bearer + cookie/CSRF), SQLite token hashing, rate limits, scoring races, OTDB ingest.

## Constraints

- Treat `data/*.db` as sensitive even with hashed tokens.
- Do not weaken CSRF/Bearer dual-auth without an explicit decision record.
- Prefer TDD-style regression tests under `tests/test_security.py` and `tests/test_cookie_auth.py` for auth/hardening fixes.
