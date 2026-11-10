# Project patterns (`.context/patterns/`)

Short, **repo-specific** runbooks for failure classes that repeat in **this** codebase.

## When to add a file here

- Same bug class happened twice, or
- Operators need a fixed checklist (logs to pull, files to check, safe rollback)

## When not to add

- One-off fixes → `RECENT_CHANGES.md` only
- Generic lessons that apply to any repo → `AGENT_LEARNINGS.md` (keep product-neutral)

## Suggested shape

```markdown
# <Pattern title>

## Symptom
<what users or agents observe>

## Detection
<commands, log markers, API checks>

## Fix
<minimal steps>

## Prevention
<guardrail, test, or doc update>
```

## Size

Keep each pattern **under ~5 KB**. Archive or split if it grows — see `context-compressor.md`.
