# Skill layout (this project)

Which workflows come from installed plugins and which belong to this repository.

## Two layers

| Layer | Location | Owns |
|---|---|---|
| **Plugin skills** | Installed in the tool (`~/.kiro/skills/`, `.claude/skills/`) | Generic workflows — context, delivery, QA, security, research |
| **This project** | `.context/`, `skills/` | Handoff facts, product-specific checklists |

Plugin skills are **installed in the tool, not copied into this repo.** They are discovered from their own descriptions; there is no path to configure and no index to maintain.

**Precedence:** project skills override plugin skills on the same subject. Declare intentional overrides in `PROJECT_STEERING.md`.

## Plugin skills you are most likely to meet here

Context workflows, from the `context` plugin:

| Skill | Role | Invocation |
|---|---|---|
| `context-update` | Keep `.context/` current during work; archive when files grow large | automatic |
| `/context-closure` | Closure before "done" — emits the gate block | **manual only** |
| `/context-bootstrap` | Stand up `.context/`, install steering | **manual only** |
| `context-mvp-scope-guard` | Include-versus-defer decisions | automatic |
| `context-sanitize` | Redact secrets and org identifiers before sharing | automatic |
| `context-docs-drift-audit` | Find stale user-facing documentation | automatic |

Other plugins cover delivery (`devops-*`), quality (`qa-*`), vulnerabilities (`vuln-*`), source security review (`secrev-*`), research (`research-*`) and plugin maintenance (`plugin-*`). Each ships its own README.

**Manual-only skills** declare `disable-model-invocation: true` and never fire on their own. If work calls for one, the assistant should **say so and ask** rather than doing the equivalent inline.

## Project skills

Add files under **`skills/<name>/SKILL.md`** when this codebase needs named checklists — see `README.md`'s "When to create a project skill" section for the criteria (recurring, product-specific, worth the maintenance cost). Index them in `skills/README.md`.

**Discovery is native, the same as plugin skills — one setup step, not per-skill.** `scripts/Setup-ProjectSkillDiscovery.ps1` (Windows) / `setup-project-skill-discovery.sh` (macOS/Linux) junctions/symlinks `skills/` into each tool's project-level skill path once per machine. `context-bootstrap` runs this during install; re-run it if you clone fresh. Without it, project skills fall back to the routing tables (secondary reference, not the primary mechanism) — confirm with the setup script's `-List` flag before assuming a skill "isn't firing" is a description-quality problem rather than a missing junction.

There is **no registration step.** The pack era required syncing a new specialist into a registry and three routing files; that is gone. A project skill placed in `skills/` and listed in `skills/README.md` is discoverable — natively, once the junction exists.

**Still have a `specialists/` folder from before this shape existed?** Run `/context-specialists-migrate` — it converts each specialist into a `skills/<name>/SKILL.md`, merges genuine sequential-stage groups, updates the routing files, and removes the old folder once nothing is left unaccounted for. Manual-only; never fires on its own.

**Cross-OS:** skills often contain run commands. Follow `cross-os-compatibility.md` from the steering location — runnable commands need Windows **and** Unix forms, or a documented exception in `DECISIONS.md`.

## Who edits what

| Role | Writes | Does not edit |
|---|---|---|
| `context-update` | `.context/` handoff files, `*_ARCHIVE.md`, pointers | Plugin content |
| `/context-closure` | Closure updates across `.context/` | Plugin content |
| `context-mvp-scope-guard` | Defer/include notes in `DECISIONS.md` | — |
| `context-sanitize` | Sanitized copies you choose to export | — |
| **You** | `skills/*`, `.context/*` | Installed plugin content — that goes through `/plugin-contribution` |

Editing canonical plugin content is deliberately gated: plugins deploy by junction, so a change is live in every session on the machine immediately. Use `/plugin-contribution`, which scope-guards, sanitizes and logs a changelog entry in one operation.

## Routing

Installed skills (plugin **and** project, once the discovery junction exists) are matched by the tool against their own descriptions. The always-on routing steering covers what native discovery cannot do — manual-only skills, and a secondary index of project skills for a session that hasn't confirmed the junction:

1. `.kiro/steering/kiro-context-agents-routing.md` (Kiro, `inclusion: always`)
2. `.claude/agent-routing.md` (Claude Code, session start)
3. `.cursor/rules/context-agents-routing.mdc` (Cursor, `alwaysApply: true`)

## Automation (hooks)

| Tool | Mechanism |
|---|---|
| **Kiro** | `agentStop` → closure, folding in `.context/` consistency and `CONTEXT_INDEX.md` refresh |
| **Cursor** | `stop` hook → `.cursor/hooks/context-closure-stop.py` (`python`/`python3 -u`) |
| **Claude Code** | `Stop` → closure; `UserPromptSubmit` → routing pointer |

A Kiro `fileEdited` hook on skill files used to exist and was **deleted** — paired with the `agentStop` hook it formed a confirmed uncapped re-trigger cycle. Do not re-add one.

See `.context/CONTEXT_HOOKS.md`. Hooks **remind**; they do not edit files for you.

## Flow

```
Work -> context-update (as needed) -> domain fix in codebase
     -> context-mvp-scope-guard (if new feature)
     -> /context-closure          <- hooks nudge here
     -> context-sanitize (before sharing externally)
```
