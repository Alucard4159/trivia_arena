# Agent Learnings

Durable failure-pattern memory for improving agents over time.

## [TA-002] Commit before third-party HTTP under request-scoped SQLite
- Date: 2026-11-10
- Confidence: high
- Scope: trivia_arena / FastAPI+sqlite3 Depends

### Symptom
OTDB fetch ran while the request `Depends(get_connection)` transaction was still open.

### Root Cause Class
Single request-scoped connection wrapping service work that includes network I/O.

### Detection
- Any service path that calls httpx/external I/O after repo reads and before later writes.

### Fix Pattern
`repo.commit()` (or equivalent) immediately before the HTTP call; then resume writes.

### Prevention Rule
- When adding remote fetches inside GameService, end the open SQLite transaction first.

### Applies to
- Pack ensure, any future webhook/remote hydrate on the request path

## [TA-001] Workspace-root Cursor rules vs nested project
- Date: 2026-11-10
- Confidence: high
- Scope: cross-project

### Symptom
Instinct to put `.cursor/rules` only under `trivia_arena/` while the open workspace is `Python Projects`.

### Root Cause Class
Tool loads project rules from the **open workspace root**, not from every nested git repo.

### Detection
- Confirm Cursor workspace path vs repo path before bootstrap target choice.

### Fix Pattern
Cursor wiring at workspace root; per-app `.context/` + `WORKSPACE.md` pointer.

### Prevention Rule
- Ask nested-subproject question on every `/context-bootstrap` in a multi-folder workspace.

### Applies to
- Any sibling app under `Training\Python Projects`
