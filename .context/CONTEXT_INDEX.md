# Context Index — section pointers across `.context/`

> **Context Safety:** Redact sensitive values. No secrets in this file.

## Purpose

Lookup layer across the `.context/` corpus.

## Index

| File | Section / heading | One-line summary | Last confirmed |
|------|--------------------|-------------------|-----------------|
| PROJECT_STATE.md | What this project does | FastAPI trivia API + static UI | 2026-11-10 |
| PROJECT_STATE.md | Current status | Build/stabilization, green on GitHub main | 2026-11-10 |
| PROJECT_STATE.md | Active priorities | Host demo URL; keep context current; optional WS | 2026-11-10 |
| ARCHITECTURE.md | Shape | Layered FastAPI, static UI, dual auth, packs | 2026-11-10 |
| ARCHITECTURE.md | Key entrypoints | app/rooms/auth/game_service/db map | 2026-11-10 |
| DECISIONS.md | Dual auth | Cookie+CSRF browser; Bearer API | 2026-11-10 |
| DECISIONS.md | trust_proxy | XFF ignored unless opted in | 2026-11-10 |
| DECISIONS.md | Context ownership | Project `.context/` here; Cursor rules at workspace | 2026-11-10 |
| TODO.md | Now / Next / Done | Hosting, WS polish, bootstrap done | 2026-11-10 |
| RECENT_CHANGES.md | 2026-11-10 bootstrap | Context install | 2026-11-10 |
| RECENT_CHANGES.md | 2026-11-09 security+packs | Main feature/hardening push | 2026-11-10 |
| WORKSPACE.md | WORKSPACE_ROOT | Points at Python Projects umbrella | 2026-11-10 |
| AGENT_LEARNINGS.md | TA-001 | Nested vs root Cursor wiring | 2026-11-10 |

## Related

- `WORKSPACE.md` — workspace pointer
- Workspace `.context/` at `Python Projects` — initiative coordination
