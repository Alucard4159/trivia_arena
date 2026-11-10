# Demo vs live wiring

> **Context Safety:** Never store secrets here. Use `[REDACTED]` and follow `.context/README.md`.

Use when validating that environments behave like real deployments, not demo/mock surfaces.

## Integration matrix (fill in for your project)

| Area | Live source | Demo / mock (avoid in real envs) |
|------|-------------|----------------------------------|
| Auth | *(e.g. real IdP / session)* | *(e.g. hardcoded user, bypass flag)* |
| Primary API | *(production or staging backend)* | *(in-memory stub, MSW, static JSON)* |
| AI / LLM features | *(real provider + billing)* | *(canned responses, keyword simulation)* |
| Admin / billing | *(real service)* | *(fixture data only in demo builds)* |
| File / object storage | *(S3, blob, etc.)* | *(local disk mock)* |

## Environment flags (examples)

| Variable / flag | Purpose |
|-----------------|--------|
| `*_DEMO=true` | Force demo UI or canned API responses |
| `*_MOCK_API=true` | Frontend talks to mock layer instead of backend |
| `NODE_ENV=development` | May enable extra debug surfaces — document what ships to prod |

List **your** project's flags in `PROJECT_STATE.md` when known.

## Ops notes

- Document how operators discover the **real** base URL / endpoint after deploy.
- List IAM, API keys, or feature flags required for live paths (names only — no values).

## Gaps to watch

- UI shows “success” while backend is still mock.
- Profile/settings fields that read from cache while authority is external (IdP, billing).
- Docs or Help still describing removed features — use `documentation-drift-auditor.md`.
