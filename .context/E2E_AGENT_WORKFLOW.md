# E2E / smoke workflow (agent-driven, tool-agnostic)

> **Context Safety:** Never put credentials in this file. Pass secrets via environment variables in the shell that launches tests.

Use when an AI agent runs automated UI or API smoke checks. Adapt commands to your stack (Playwright, Cypress, Selenium, HTTP checks, etc.).

## 1) Plan first

Before running tests, produce a short run plan:

| Section | Content |
|---------|---------|
| **Target** | Environment name + base URL + build/commit if known |
| **Planned checks** | What will be executed this run |
| **Not automatable** | Checks that need human confirmation |
| **Blocked prerequisites** | Auth, data seed, network, feature flags |
| **Pass/fail gates** | When to stop the run |

Optional project file: maintain a checklist (e.g. `UI_SMOKE_TEST_PLAN.md`) and reference it here.

## 2) Record untestable items explicitly

Do not silently skip checks. Label each with:

- `missing_data` — no seeded rows / fixtures
- `missing_permission` — role cannot access route
- `missing_credential` — no login or integration secret in env
- `not_exposed_in_ui` — no stable selector or public API
- `environment_blocker` — VPN, allowlist, service down

Include a **next action** (manual step or setup command).

## 3) Credentials handshake

The test runner reads **environment variables** from the shell that launches it. The agent must set:

| Variable (examples) | Purpose |
|---------------------|---------|
| `BASE_URL` / `SMOKE_BASE_URL` | Application root |
| `TEST_USER` / `TEST_EMAIL` | Login identity |
| `TEST_PASSWORD` | Login secret (process env only — never commit) |
| `API_TOKEN` | Bearer token for API smoke, if used |

Obtain values from the user or your project's documented provisioning script. Delete temp credential files after export.

## 4) Execute

Run from the directory your project documents (e.g. `e2e/`, `frontend/`).

Record: command, exit code, and failing assertion text (quote errors).

## 5) Close out

- Material failures → `RECENT_CHANGES.md` + `AGENT_LEARNINGS.md` if reusable
- Run `/context-closure`

## Defaults (recommendations)

- Prefer **low-cost** smoke (shell + navigation) unless the user asked for full integration paths.
- Prefer a **retained** test user over creating users every run when the IdP allows it.
- Fail fast on auth/role checks before deep UI assertions.
