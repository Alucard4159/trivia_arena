# .context/ — Project context for AI handoff

Structured project memory for AI and human handoff.

<!-- ContextTemplateVersion: 3.0-plugin -->
<!-- BootstrappedAt: {{BOOTSTRAP_TIMESTAMP}} -->

## Scope

| Layer | Location | Owns |
|---|---|---|
| **This `.context/`** | This folder | Project facts, status, architecture, history |
| **Plugin skills** | Installed in the tool (`~/.kiro/skills/`, or `.claude/skills/`) | Generic reusable workflows — never copied into this repo |
| **Project skills** | `skills/` | Your product-specific checklists (optional) |
| **Wiring references** | `.kiro/steering/` (or equivalent) | `cross-os-compatibility.md`, `cross-tool-parity.md` — installed at bootstrap, `inclusion: manual` |

Boundary doc: **`skills/PLAYBOOKS_BOUNDARY.md`**.

**Skills are discovered by the tool, not indexed here.** There is no registry file and no routing table to maintain: the assistant matches a request against each skill's own description. Do not create a `PLAYBOOK_REGISTRY.md` or `STEERING_REGISTRY.md` — both were retired, and re-adding one means maintaining by hand what the tool already does.

## Files

| File | Purpose | When to read |
|---|---|---|
| `PROJECT_STATE.md` | Current status, environment, key facts | Always first |
| `ARCHITECTURE.md` | Layout, modules, execution paths | Structural changes |
| `DECISIONS.md` | Decision log and rationale | "Why was this done?" |
| `AGENT_LEARNINGS.md` | Reusable guardrails | After incidents |
| `TODO.md` | Backlog | Planning |
| `RECENT_CHANGES.md` | Change log | After work / compression |
| `CONTEXT_HOOKS.md` | Closure automation across Kiro, Cursor, Claude Code | After bootstrap; disable/debug |
| `DEMO_VS_LIVE.md` | Mock vs real integrations matrix | Before claiming prod behaviour |
| `E2E_AGENT_WORKFLOW.md` | Agent-driven smoke/E2E plan | Before UI/API smoke runs |
| `WORKSPACE.md` | **Opt-in.** Declares `WORKSPACE_ROOT` for a multi-repo initiative | Only if this repo is part of one |
| `patterns/README.md` | Index for repo-specific runbooks | When adding a recurring failure class |
| `pack-configs/` | Per-plugin project configuration — scope, data sources, constraints | A skill reads its own config at pre-flight |

## First-read sequence (bounded session start)

Install the IDE **session-start** rule from `templates/ide-wiring/` — agents load a small context budget, not full history.

1. `PROJECT_STATE.md` — overview only, through the deployment/env section
2. `TODO.md` — open and blocker sections
3. `RECENT_CHANGES.md` — **top dated section only**
4. `WORKSPACE.md` — **only if present**; declares `WORKSPACE_ROOT`
5. `AGENT_LEARNINGS.md` — when troubleshooting
6. `ARCHITECTURE.md` + `DECISIONS.md` — when implementing
7. `*_ARCHIVE.md` — **never auto-read** at session start

## Maintenance

- **`RECENT_CHANGES.md`** — paper trail for material edits
- **`AGENT_LEARNINGS.md`** — repeatable patterns, not a diary
- **Closure:** `/context-closure` — manual-only, so invoke it by name
- **Updating context during work:** the `context-update` skill fires on its own; it handles archival when files grow large
- **New features:** the `context-mvp-scope-guard` skill, for include-versus-defer decisions
- **Hooks:** Kiro `agentStop`, Cursor `stop`, Claude Code `Stop` all nudge closure — see `CONTEXT_HOOKS.md`

## For AI assistants

1. **Bounded session start.** Overview of `PROJECT_STATE`, open `TODO`, top section of `RECENT_CHANGES` only. See the IDE session-start wiring.
2. **Let skills fire.** Non-trivial work — troubleshoot, implement, review, deploy, multi-step — should match an installed skill. Read its body before deep edits. There is no table to consult first.
3. **Manual-only skills must be offered, not performed.** A skill declaring `disable-model-invocation: true` never fires by itself. If work clearly calls for one, say so and ask rather than doing the equivalent inline.
4. **Cross-OS and cross-tool.** Before changing scripts, hooks, CI, Docker, or IDE wiring, read `cross-os-compatibility.md` and `cross-tool-parity.md` from the steering location.
5. **Project skills** live in `skills/`, indexed in `skills/README.md`. They override plugin skills on the same subject; declared overrides go in `skills/PROJECT_STEERING.md`.
6. **Policies** are always-on steering: `.kiro/steering/`, `.cursor/rules/`, or `.claude/agent-routing.md` — evidence-first, deploy consent, install consent, universal standards.
7. Read `AGENT_LEARNINGS.md` when troubleshooting.

## Where the generic workflows live

Installed as skills in the tool, invoked by name or matched by description:

| Topic | Skill |
|---|---|
| Boundary doc | `skills/PLAYBOOKS_BOUNDARY.md` (this repo) |
| Session closure | `/context-closure` |
| Keeping context current | `context-update` |
| Scope decisions | `context-mvp-scope-guard` |
| Docs drift | `context-docs-drift-audit` |
| Sanitizing before sharing | `context-sanitize` |
| Hooks | `CONTEXT_HOOKS.md` (this repo) |
