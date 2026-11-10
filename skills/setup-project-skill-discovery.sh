#!/usr/bin/env bash
# macOS/Linux equivalent of Setup-ProjectSkillDiscovery.ps1 -- symlinks this
# project's skills/ into each AI tool's project-level skill discovery path.
# See the .ps1.txt version's header comment for the full rationale; this file
# only differs in the linking mechanism (symlink, not a Windows junction).
#
# Usage:
#   ./scripts/setup-project-skill-discovery.sh          # create all three links
#   ./scripts/setup-project-skill-discovery.sh --list    # show current state
#   ./scripts/setup-project-skill-discovery.sh --remove  # tear down

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SOURCE="$REPO_ROOT/skills"

TOOLS=("Cursor:.cursor/skills" "Claude Code:.claude/skills" "Kiro:.kiro/skills")

if [ ! -d "$SKILLS_SOURCE" ]; then
    echo "No skills/ directory found at $SKILLS_SOURCE -- nothing to link."
    exit 0
fi

MODE="link"
if [ "${1:-}" = "--list" ]; then MODE="list"; fi
if [ "${1:-}" = "--remove" ]; then MODE="remove"; fi

for entry in "${TOOLS[@]}"; do
    tool="${entry%%:*}"
    rel="${entry##*:}"
    target="$REPO_ROOT/$rel"

    if [ "$MODE" = "list" ]; then
        if [ ! -e "$target" ]; then
            printf '%-14s not linked\n' "$tool"
        elif [ -L "$target" ]; then
            printf '%-14s symlink OK\n' "$tool"
        else
            printf '%-14s PLAIN DIRECTORY - not a symlink, will not track skills/\n' "$tool"
        fi
        continue
    fi

    if [ "$MODE" = "remove" ]; then
        if [ -L "$target" ]; then
            rm "$target"
            printf '%-14s removed\n' "$tool"
        else
            printf '%-14s not linked (nothing to remove)\n' "$tool"
        fi
        continue
    fi

    # MODE = link
    if [ -e "$target" ]; then
        if [ -L "$target" ]; then
            printf '%-14s already linked\n' "$tool"
            continue
        fi
        echo "  SKIPPED $tool: $target exists and is not a symlink -- remove it manually first if you want this to link skills/"
        continue
    fi

    mkdir -p "$(dirname "$target")"
    ln -s "$SKILLS_SOURCE" "$target"
    if [ -L "$target" ] && [ -e "$target/README.md" ]; then
        printf '%-14s symlink OK\n' "$tool"
    else
        printf '%-14s FAILED\n' "$tool"
    fi
done

if [ "$MODE" = "link" ]; then
    echo ""
    echo "This project's skills are now discoverable natively on Cursor, Claude Code, and Kiro."
    echo "Reload/restart the tool if a skill doesn't show up right away."
fi
