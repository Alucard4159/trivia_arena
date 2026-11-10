# Project Frontmatter — file/folder map

> **Context Safety:** Redact sensitive values (hostnames, IPs, identifiers). No secrets in this file.

<!-- ContextTemplateVersion: 1.0 -->
<!-- BootstrappedAt: {{BOOTSTRAP_TIMESTAMP}} -->

## Purpose

A compact map of this project's folders/files with a one-line description of what each is for. Exists to reduce token usage when a session needs to locate a relevant file — consult this instead of exploratory directory listing or search calls across the real tree, especially for non-obviously-named files (e.g. generated exports, hashed filenames, abbreviated scripts).

This is **not** a replacement for `PROJECT_STATE.md`'s "Environment notes" section, which describes key artifacts in prose with project-status context. This file is a structural index for path lookup — no status, no narrative, just "what is this and where."

## Maintenance

Maintained by a `fileCreated`/`fileDeleted` hook (see `.context/CONTEXT_HOOKS.md`) — new files/folders get a placeholder entry, deleted ones are removed. The placeholder description is a best-effort inference from filename/location; a human or a later session should correct it if wrong. This file can go stale if the hook doesn't fire (e.g., files created outside the IDE) — if a listed path no longer exists or a real path is missing, treat it as a signal to re-scan, not as ground truth.

## Map

```text
<project-root>/
  <populate at bootstrap or first hook run — one line per top-level folder/file,
   nested one level further for folders with non-obvious contents>
```

| Path | What it is |
|------|------------|
| *(seed at bootstrap by scanning the project tree)* | |

## Related

- `PROJECT_STATE.md` — "Environment notes" section describes key artifacts in prose with project-status framing; this file is the structural, status-free complement
- `CONTEXT_HOOKS.md` — the fileCreated/fileDeleted hook that keeps this file current
