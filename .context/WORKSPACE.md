# Workspace tier (multi-repo initiatives only)

Replaces the former `CONTEXT_PACK.md`. That file held three things: a `PACK_ROOT` pointer, a registered-sibling-packs table, and the `WORKSPACE_ROOT` declaration. The first two are retired — skills are discovered natively, and there is no registry — but **`WORKSPACE_ROOT` is not**, so it lives here under an accurate name.

| Field | Value |
|-------|-------|
| **WORKSPACE_ROOT** | `C:\Users\aluca\OneDrive\Documents\Training\Python Projects` |
| **Declared (UTC)** | `2026-11-10T19:58:50Z` |

## What WORKSPACE_ROOT is

A dedicated sibling folder holding the coordination-layer `.context/` for a whole initiative — sibling-repo index, why-split rationale, cross-repo decisions and changes.

## Routing rule

- A decision or change affecting **only this repo's internals** stays in this project's `.context/`.
- A decision or change affecting the **split or topology across sibling repos**, or spanning **more than one member repo**, goes to `WORKSPACE_ROOT/.context/`.
- If edited files live **outside this project's directory**, update the `.context/` nearest those files — not this project's by default.
- Cross-repo history goes to `WORKSPACE_ROOT/.context/DECISIONS.md` and `RECENT_CHANGES.md`, **not** to `WORKSPACE_STATE.md`'s narrative sections.

Consumed by `context-update` and `context-closure`.
