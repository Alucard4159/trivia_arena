# Junctions this project's skills/ into each AI tool's project-level skill
# discovery path, so project skills are natively discovered the same way
# plugin skills already are via junction deployment (see cross-tool-parity.md).
#
# Why this is needed: skills/ lives at the repo root, which is not one of the
# documented per-tool project-skill discovery paths:
#   - Cursor:      .cursor/skills/ or .agents/skills/ (project-level)
#   - Claude Code: .claude/skills/ (walked up from cwd to repo root)
#   - Kiro:        .kiro/skills/ (project-level, mirrors ~/.kiro/skills/ globally)
# Without this junction, project skills rely entirely on the hand-maintained
# keyword tables in the routing steering files, with native description-match
# discovery never actually engaged. All three tools consume the same SKILL.md
# frontmatter shape, so one junction per tool is all that's needed -- no
# per-skill step, and a skill added later is automatically covered.
#
# This is a ONE-TIME, PER-MACHINE setup step, like the plugin system's own
# deploy-kiro.ps1/deploy-cursor.ps1/deploy-claude.ps1 (the plugins repo) --
# junctions aren't tracked by git (add .cursor/skills/, .claude/skills/,
# .kiro/skills/ to .gitignore -- see this template's own note in
# PLAYBOOKS_BOUNDARY.md), so every developer's clone needs this run once.
# Idempotent: safe to re-run.
#
# Usage:
#   .\scripts\Setup-ProjectSkillDiscovery.ps1          # create all three junctions
#   .\scripts\Setup-ProjectSkillDiscovery.ps1 -List    # show current state, change nothing
#   .\scripts\Setup-ProjectSkillDiscovery.ps1 -Remove  # tear down

[CmdletBinding()]
param(
    [switch]$List,
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SkillsSource = Join-Path $RepoRoot 'skills'

$targets = @(
    @{ Tool = 'Cursor';      Path = Join-Path $RepoRoot '.cursor\skills' }
    @{ Tool = 'Claude Code'; Path = Join-Path $RepoRoot '.claude\skills' }
    @{ Tool = 'Kiro';        Path = Join-Path $RepoRoot '.kiro\skills' }
)

if (-not (Test-Path $SkillsSource)) {
    Write-Host "No skills/ directory found at $SkillsSource -- nothing to link."
    return
}

if ($List) {
    foreach ($t in $targets) {
        $state = if (-not (Test-Path $t.Path)) { 'not linked' }
                 elseif ((Get-Item $t.Path).LinkType -eq 'Junction') { 'junction OK' }
                 else { 'PLAIN DIRECTORY - not a junction, will not track skills/' }
        '{0,-14} {1}' -f $t.Tool, $state
    }
    return
}

foreach ($t in $targets) {
    if (Test-Path $t.Path) {
        if ($Remove) {
            Remove-Item $t.Path -Recurse -Force
            '{0,-14} removed' -f $t.Tool
            continue
        }
        if ((Get-Item $t.Path).LinkType -eq 'Junction') {
            '{0,-14} already linked' -f $t.Tool
            continue
        }
        Write-Host "  SKIPPED $($t.Tool): $($t.Path) exists and is not a junction -- remove it manually first if you want this to link skills/" -ForegroundColor Yellow
        continue
    }

    if ($Remove) { '{0,-14} not linked (nothing to remove)' -f $t.Tool; continue }

    $parent = Split-Path -Parent $t.Path
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

    cmd /c mklink /J "$($t.Path)" "$SkillsSource" | Out-Null
    $ok = (Test-Path (Join-Path $t.Path 'README.md')) -and ((Get-Item $t.Path).LinkType -eq 'Junction')
    '{0,-14} {1}' -f $t.Tool, $(if ($ok) { 'junction OK' } else { 'FAILED' })
}

if (-not $Remove -and -not $List) {
    Write-Host "`nThis project's skills are now discoverable natively on Cursor, Claude Code, and Kiro."
    Write-Host "Reload/restart the tool if a skill doesn't show up right away."
}
