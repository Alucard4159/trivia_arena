# Key Decisions Log

Newest first. Capture what was decided and why.

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
