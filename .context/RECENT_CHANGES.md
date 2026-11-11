# Recent Changes

> **Context Safety:** No secrets in this file.

## 2026-11-10 — security review remediation (local, uncommitted)

- Logout burns `token_hash` so prior Bearer secrets die with cookies (`SEC-026`)
- Live `question` / reveal payloads are room-member-only; lobby/meta stays public
- `SameSite=none` without `Secure` rejected at `create_app` (`SEC-029`)
- Commit SQLite txn before OTDB HTTP; length-cap OTDB prompts/choices (`SEC-010`)
- Action rate limiter on start/answer/next; explicit SELECT columns; domain errors; pyright Generator types
- Follow-up (same day): `claim_status` lobby→active / active→finished; `INSERT OR IGNORE` create_round; post-start roster members-only; deps `Generator` typing
- Tests: logout kill, non-member Q/reveal/roster strip, action limit, SameSite gate, OTDB oversize, concurrent start claim, duplicate round, second start 409 (33 green)

## 2026-11-10 — context-bootstrap

- Installed full `.context/` handoff set, pack-configs (`context`, `python`, `secrev`), `PLUGIN_VERSIONS.md`
- Linked to workspace root via `WORKSPACE.md`
- Project skills scaffold + discovery junctions

## 2026-11-09 — security + packs + cookie auth (git `main`)

- Question packs + OTDB cache
- Scoring race claim, hashed tokens, rate limits, SECURITY.md
- HttpOnly session cookie + CSRF; CORS allowlist support
- Follow-up: scrub legacy `token` column, trust-proxy gate for XFF, create-room rate limit
