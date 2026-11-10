# Pack Configurations

Project-specific parameters for each registered pack. One file per plugin.

Pack specialists check this folder before starting work. If a config exists for their pack, they use it for project-specific scope, search terms, data sources, and constraints — instead of asking the user for basic information every session.

## Adding a new config

When a new pack is registered, optionally create a config file here:
1. Name it `<pack-name-lowercase>.md` (e.g., `research.md`, `vuln-analysis.md`)
2. Include project-specific parameters the plugin's specialists would otherwise ask for
3. the plugin's specialists will read it automatically at the start of their workflow

## What belongs here vs. elsewhere

| Content | Where it goes |
|---------|---------------|
| Search terms, spaces, project keys, scope | Here (pack config) |
| Credentials, tokens, API keys | Environment variables (never in files) |
| Architecture, decisions, status | `.context/` handoff files |
| Deliverables, reports, analysis output | Project root or dedicated folders |
