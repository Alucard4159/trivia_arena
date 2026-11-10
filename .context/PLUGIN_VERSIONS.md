# Plugin versions (synced)

> **Context Safety:** Never store secrets/tokens/passwords/private keys in this file.

Records the version this project last reconciled against, per plugin it uses — read from that plugin's own `README.md` `Version:` and `Last updated:` fields. The Synced date column is a copy of `Last updated:` itself, not the calendar date of the bootstrap or sync session.

| Plugin | Synced version | Synced date |
|---|---|---|
| context | 2.4.7 | 2026-11-10 |
| python | 1.0.0 | 2026-11-09 |
| secrev | 0.1.2 | 2026-11-10 |

## Maintenance

- **Written by:** `context-bootstrap` / `context-update-project`.
- **Read by:** `context-closure` Plugin version drift gate.
- Prefer letting those skills own version/date columns.
