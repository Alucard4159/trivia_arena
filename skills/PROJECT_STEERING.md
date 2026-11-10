# PROJECT_STEERING.md

> **Purpose:** Documents intentional divergences from pack defaults. When project specialists or
> steering files conflict with a plugin, this file is the authoritative declaration of which rule wins
> and why.
>
> **Precedence:** Project specialists and steering override pack defaults. This file documents
> the overrides; without a declaration here, pack defaults apply.

## Precedence declaration

Project-level specialists in `specialists/` and routing entries in this project's IDE wiring files
take precedence over pack defaults. Pack defaults apply in all other cases.

## Declared overrides

| Override | Pack default | Project rule | Justification |
|----------|-------------|--------------|---------------|
| *(none yet)* | | | |

<!--
Add rows as overrides are established. Example:

| Large dataset handling | Use Python pandas (universal-standards) | Use streaming batch loader | Scan modules process 100k+ rows; pandas OOM in container limits |
| Credential storage | Use Secrets Manager | Use encrypted DB column | Single-tenant PoC; secrets manager cost/overhead not justified |
-->

## Notes

- This file is project-owned. Bootstrap and re-sync never overwrite it.
- Update when a plugin update would change a declared behavior — decide whether to adopt or keep the override.
- Link related specialist files in the table if the override lives in a specific `.md`.
