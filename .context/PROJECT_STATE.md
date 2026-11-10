# Project State

> **Context Safety:** Redact sensitive values. No secrets in this file.

Last updated: 2026-11-10

## What this project does

Turn-based multiplayer trivia API (FastAPI + SQLite) with a vanilla static UI, question packs (local JSON + optional Open Trivia DB), timed rounds/reveal, and cookie/CSRF + Bearer auth.

## Current status

- Phase: build / stabilization
- Overall: green — core game loop, packs, security hardening, and tests are in place on GitHub `main`

## Active priorities

- P1: Host a playable URL (Render/Fly/Railway or similar) if sharing beyond local
- P2: Keep `.context/` current via closure after work sessions
- P3: Optional WebSocket broadcasts for `round_opened` / `round_scored` only

## Environment notes (safe only)

- Runtime(s): Python 3.12, `uv`
- Deployment target(s): local (`uv run trivia-arena`); GitHub repo public; no production host yet
- Key external dependencies (names only): Open Trivia DB (optional pack), FastAPI, uvicorn, httpx

## Risks / blockers

- Single-process SQLite + in-memory rate limits — fine for demos, not multi-worker prod
- Cross-site Pages hosting needs CORS + `SameSite=None; Secure` carefully configured
