# Project skills (this repository)

Product- or stack-specific checklists that belong to this codebase rather than to a shared plugin.

## How these get found

Installed **plugin** skills are discovered by the tool from their own descriptions — junction-deployed by `deploy-kiro.ps1`/`deploy-cursor.ps1`/`deploy-claude.ps1` in the plugin repo. **Project skills get the same native discovery**, via a one-time per-machine setup step: run `scripts/Setup-ProjectSkillDiscovery.ps1` (Windows) or `scripts/setup-project-skill-discovery.sh` (macOS/Linux) once. This creates a junction/symlink from each tool's project-level skill path (`.cursor/skills/`, `.claude/skills/`, `.kiro/skills/`) back to this `skills/` directory — the exact same junction mechanism plugin skills use, one level down.

**Without that step, project skills are invisible to native discovery on every tool** — `skills/` at the repo root isn't a documented discovery path for any of the three (Cursor looks for `.cursor/skills/`/`.agents/skills/`; Claude Code walks `.claude/skills/` up to the repo root; Kiro mirrors its global `~/.kiro/skills/` shape at a project-local `.kiro/skills/`). The junctions aren't tracked by git (`.gitignore` already has the three paths — see this template's own note), so every developer's clone needs the setup script run once. `context-bootstrap` runs it during install; re-run it yourself if you clone the repo fresh or the junction gets removed.

The routing index below and the always-on routing steering (`.kiro/steering/kiro-context-agents-routing.md`, `.claude/agent-routing.md`, `.cursor/rules/context-agents-routing.mdc`) remain a **secondary reference** — useful for a human scanning what exists, or a session confirming the junction is present (`Setup-ProjectSkillDiscovery.ps1 -List`) — not the load-bearing discovery mechanism.

## Plugin skills — do not duplicate here

Generic workflows are installed as skills in the tool. Don't copy them into this folder; if a plugin skill is *nearly* right, either override it deliberately (see Precedence) or propose the improvement upstream with `/plugin-contribution`.

## Precedence

Project skills take precedence over plugin skills on the same subject. Declare intentional overrides in `PROJECT_STEERING.md` in this folder, so an override reads as a decision rather than an accident.

## When to create a project skill

A recurring pattern in this project's own work is a project-skill candidate when **all** of these hold:

1. **It recurs** — the same symptom, question, or checklist has come up more than once. A one-off doesn't need a skill; note it in `AGENT_LEARNINGS.md` instead and revisit if it recurs.
2. **It's product-specific** — it depends on this codebase's own contracts, architecture, or terminology (a specific DTO shape, a specific pipeline, a specific settings key) in a way a generic plugin skill can't already cover. If a plugin skill is *nearly* right, override it deliberately in `PROJECT_STEERING.md` instead of duplicating it here (see Precedence below) — or propose the improvement upstream with `/plugin-contribution` if the gap is genuinely generic, not product-specific.
3. **It's worth the maintenance cost** — a skill is a file someone has to keep accurate as the product changes. A pattern that's stable and rarely touched may be better served by a short note in `ARCHITECTURE.md` than a whole skill.

If a pattern fits, create the skill (checklist below). If it's borderline, err toward `AGENT_LEARNINGS.md` first — a skill created from a single occurrence risks encoding a guess as a procedure; a second real occurrence is much stronger evidence.

**Improving an existing project skill works differently from a plugin skill.** A plugin skill is shared across every project using that plugin, so a fix routes through `/plugin-contribution` (scope-guard, sanitize, changelog) before it can land. A project skill has exactly one owner — this project — so there's no equivalent gate: edit `skills/<name>/SKILL.md` directly, the same way you'd edit any other file in this repo, and record the change in `RECENT_CHANGES.md` if it's a substantive behavior change (see `project-release-notes-curator`-style guidance in `AGENT_WORKFLOWS.md` if this project has one, or `context-update`'s general "reusable pattern" criterion otherwise). There is no `SUGGESTIONS.md` for project skills and none is needed — the reason a plugin needs a deferred-suggestion backlog (change requires sanitization, scope-checking, and affects other projects) doesn't apply to a skill only this project uses.

## Add a project skill (checklist)

1. Create `skills/<name>/SKILL.md` — triggers, checklist, guardrails.
2. **Cross-OS:** follow `cross-os-compatibility.md` from the steering location. Runnable commands need Windows **and** Unix forms, or a documented exception in `DECISIONS.md`.
3. Add a row to the routing index below.
4. Add the same row to each tool's routing file listed above.

**There is no registry to sync.** The pack era required running a registry-sync specialist to register a new specialist in `.context/`, plus three routing files. Both registries were retired — skills are discovered rather than registered. Steps 3–4 are a secondary index now, not the discovery mechanism (see "How these get found" above) — keep them updated anyway, since they're what a human or a session with a stale/missing junction actually reads.

**Migrating an old `specialists/` folder rather than adding a new skill?** Don't hand-convert it — run `/context-specialists-migrate` instead. It handles merge-opportunity detection for specialists that were sequential stages of one workflow, which a manual file-by-file conversion is likely to miss.

## Routing index (edit when you add files)

| Keywords / symptoms | Skill |
|---|---|
| *(none yet — add rows when you create skills)* | |

**Boundary:** `PLAYBOOKS_BOUNDARY.md`
