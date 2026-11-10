# Agent Learnings

Durable failure-pattern memory for improving agents over time.

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
