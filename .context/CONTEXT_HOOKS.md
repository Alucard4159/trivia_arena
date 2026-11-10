# Context automation hooks (Cursor + Kiro + Claude Code)

> **Context Safety:** Never store secrets in hook prompts or logs. Redact per `.context/README.md`.

Bootstrap installs **closure hooks** so agents do not stop after product work without a `.context/` pass.

## Cursor

| Artifact | Purpose |
|----------|---------|
| `.cursor/hooks.json` | Registers `stop` → Python closure script, `afterFileEdit` → queue hook, and `sessionStart` → the plugin-routing sync script |
| `.cursor/hooks/context-closure-stop.py` | **Preferred** — `python`/`python3 -u` stop hook (Windows-safe stdout) |
| `.cursor/hooks/context-file-edit-check.py` | `afterFileEdit` queue hook — records edit notices for the stop hook to surface |
| `scripts/sync_manual_skill_routing.py` | Runs once per session (`sessionStart`) — mechanically syncs the project's manual-only-skill routing tables against every plugin's actual manual-only skills. Same script on all three tools; see its own module docstring. |

**OS:** Bootstrap sets `hooks.json` `stop` to `python -u` (Windows) or `python3 -u` (macOS/Linux). Installs the `.py` hook scripts only. See **`cross-os-compatibility.md`** in the steering location.

**Windows note:** Do not point Cursor `stop` at `powershell -File …context-closure-stop.ps1` when `followup_message` must reach chat — Cursor frequently records empty stdout for that path. Prefer the Python runner.


**Parity gap — plugin-CHANGELOG reminder:** Cursor does have an `afterFileEdit` queue hook, but it cannot inject follow-up context directly. The Kiro/Claude "you edited plugin content → log the CHANGELOG" reminder therefore still has no direct Cursor hook form; the notice is surfaced by the stop hook and backed up by the canonical-write-guard rule in universal-standards. Documented per the Three-Tool Rule rather than faked.

**Behavior:** Fires after **every response** (unconditional, matches Kiro). At `loop_count=0`, emits `followup_message` with the **same prompt as Kiro's agentStop** — run `context-closure` and return its Output Contract verbatim; if nothing material changed, say so briefly and stop; this turn is context-closure only (no hook/tooling fixes). At `loop_count>=1` or within the per-conversation cooldown, exits silently. Pending `afterFileEdit` notices (if any) are prepended to that same prompt.


## Kiro

| Artifact | Purpose |
|----------|---------|
| `.kiro/hooks/context-closure-agentStop.json` | `Stop` trigger → runs the `context-closure` skill, `.context/` consistency check, and `CONTEXT_INDEX.md` refresh (if present) folded into that skill's own workflow |
| `.kiro/hooks/context-frontmatter-fileCreated.json` / `context-frontmatter-fileDeleted.json` (opt-in, installed only if `PROJECT_FRONTMATTER.md` is present) | `PostFileCreate` / `PostFileDelete` triggers → maintains `PROJECT_FRONTMATTER.md` |
| `.kiro/hooks/plugin-changelog-reminder-fileSave.json` | `PostFileSave` trigger, matched to canonical plugin content (`*/skills/*/SKILL.md`, `*/skills/*/reference-*.md`, `*/README.md`) → reminds to add a `CHANGELOG.md` entry before committing. Installed everywhere: plugins deploy by junction, so canonical plugin content is editable from *any* project, not just a plugin-maintenance repo. Self-skips on the CHANGELOG/SUGGESTIONS files themselves and on trivial edits. `PostFileSave` (a user-save event) is safe here — unlike the retired agent-`fileEdited` hook, it does not form an agent re-trigger cycle. |
| `.kiro/hooks/plugin-routing-sync-sessionStart.json` | `SessionStart` trigger → runs `scripts/sync_manual_skill_routing.py`, which mechanically syncs the project's manual-only-skill routing tables against every plugin's actual manual-only skills, auto-adding any missing row. Fires once per session, on all three tools (same script). Existence check, not content-freshness — a different concern from `plugin_version_drift.py`'s registered-vs-actual version comparison. |

Installed automatically by `context-bootstrap` (restored 2026-09-01 — see `CHANGELOG.md`; an intermediate migration pass had this step removed with no replacement, leaving bootstrapped projects without a closure hook). **Format note (fixed 2026-09-01):** the file extension is `.json`, not the retired `.kiro.hook` — confirmed against `createHook`'s own tool contract and an empirical test of the file it actually writes. A project that predates this fix and still has a `*.kiro.hook` file should have it recreated, not just renamed, since the schema inside may also predate the 2026-08-21 schema fix referenced below.

The internal JSON schema itself (`{"version": "v1", "hooks": [{"name", "trigger", "matcher"?, "action": {"type": "agent", "prompt"}}]}`) was fixed 2026-08-21 — a prior version of this plugin shipped an older, incompatible schema (`{"when": {"type": ...}, "then": {"type": "askAgent", ...}}`). See `MIGRATIONS.md` (`2026-08-21-002`) for projects that installed that stale schema.

> **Note:** a prior version of this plugin also shipped a `fileEdited` hook on `.context/*.md`. It has been **deleted** — paired with the closure hook, it formed a confirmed, uncapped re-trigger cycle requiring a Kiro restart to clear. Its consistency-check and `CONTEXT_INDEX.md`-refresh instructions are now folded into `context-closure-agentStop.json` above, via the `context-closure` skill's own workflow. See `CHANGELOG.md` and `MIGRATIONS.md` (`2026-07-16-005`, `2026-08-20-002`).

## Claude Code

| Artifact | Purpose |
|----------|---------|
| `.claude/settings.json` | Registers `SessionStart`, `Stop`, `UserPromptSubmit`, and `PostToolUse` hooks |
| `scripts/sync_manual_skill_routing.py` (invoked from `settings.json`'s `SessionStart` entry) | Once per session: mechanically syncs the project's manual-only-skill routing tables against every plugin's actual manual-only skills. Same script on all three tools. |
| `.claude/hooks/context-closure-stop.py` | On stop: injects context closure reminder |
| `.claude/hooks/session-start-check.py` | On first prompt only: checks context file drift |
| `.claude/hooks/routing-reminder.py` | On every prompt: injects compact routing/standards file pointer (anti-fade) |
| `.claude/hooks/file-edit-check.py` | On AI Write/Edit: checks if `.context/*.md` or `skills/*/SKILL.md` needs sibling updates, **and** if canonical plugin content (`*/skills/*/SKILL.md`, `reference-*.md`, `*/README.md`) was edited, reminds to add a plugin `CHANGELOG.md` entry |

**Behavior:** `Stop` hook fires after **every response** (unconditional, matches Kiro). Returns `{ "decision": "block", "reason": "..." }` to inject the context-check prompt. Exits silently when `stop_hook_active=true` (the AI is responding to the previous block) to prevent infinite loops. `session-start-check.py` runs once per session (marker file guard). `routing-reminder.py` fires on **every prompt** with no guard — emits a one-line `hookSpecificOutput` pointer to keep routing file references visible under context compression. `PostToolUse` fires on every Write or Edit tool call and checks path patterns.

**Windows prerequisite:** Run `git config core.autocrlf false` in the repo so git CRLF warnings don't corrupt hook output parsing.

## Skills invoked by hooks

| Skill | Role |
|------------|------|
| `context-closure` | Session closure — verifies context, runs drift/gap checks, emits the gate block |

## Disable / debug

| Variable | Tool |
|----------|------|
| `CONTEXT_SKIP_HOOK=1` | Cursor + Claude Code hooks off for session |
| `CONTEXT_HOOK_DEBUG=1` | Logs to temp dir (`context-closure-hook.log`, `claude-session-start-hook.log`) |

## Materiality gate (both tools)

Update `.context/` when the session changed **behavior, contracts, architecture, security/deploy/runtime, or notable decisions** — not for typos-only or comment-only edits unless they change operator meaning.

## Fallback (no hooks)

Invoke `/context-closure` directly — especially **Close out** after each session.
