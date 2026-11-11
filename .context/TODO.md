# TODO

> **Context Safety:** Redact sensitive values. No secrets in this file.

## Now

- [ ] Host a playable demo URL (Render/Fly/Railway) if sharing beyond localhost
- [ ] Keep closing sessions with `/context-closure` so `.context/` stays honest

## Next

- [ ] Optional WebSocket broadcasts for `round_opened` / `round_scored` only (REST remains source of truth)
- [ ] When adding the next sibling Python app: bootstrap its `.context/` + `WORKSPACE.md`, add row to workspace `WORKSPACE_STATE.md`

## Blocked

- (none)

## Done recently (optional short list)

- [x] Question packs + OTDB cache
- [x] Cookie/CSRF browser auth; Bearer for API
- [x] Security hardening (score claim, token hash scrub, rate limits, trust-proxy)
- [x] context-bootstrap (project `.context/` + workspace pointer)
- [x] 2026-11-10 security review remediation (logout burn, member-gated state, SameSite gate, OTDB txn/length, action limits, claim start/round, post-start roster gate) — local uncommitted
