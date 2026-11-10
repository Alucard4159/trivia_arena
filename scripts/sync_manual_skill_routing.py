#!/usr/bin/env python3
"""Mechanically sync a project's manual-only-skill routing tables against reality.

Installed by `context-bootstrap` into a project's `scripts/` folder and wired to
run once per session (SessionStart, on Kiro/Claude Code/Cursor) via the canonical
`plugin-routing-sync-sessionStart` hook. Exists because manual-only skills
(`disable-model-invocation: true`) never self-activate on a description match --
the *only* way anyone (human or AI) discovers one exists is a hand-maintained
table listing it by name in each tool's routing file. That table drifts every
time ANY plugin gains a new manual-only skill, in EVERY consuming project, with
nothing catching it until someone happens to notice. Found directly in a consuming project: two
of its three routing files listed only 3 plugins (context/devops/vuln) while a
third (correctly) said all 10 plugins/44 skills are discoverable.

This is NOT the same problem `plugin_version_drift.py` solves. That check answers
"has a plugin the project already knows about changed content since we synced?"
-- it requires the project to have registered the plugin in the first place. This
script answers "does the project's routing even know a given manual-only skill
exists at all?" -- a plugin the project has never registered has no version to
compare, so version drift never catches it. Existence and freshness are separate
questions; this script only answers the first.

Design choices, and why:

- **Auto-write, not report-only.** The fix here is fully mechanical (a skill's
  name + its own frontmatter `description`, no judgement call), same risk profile
  as `sync_steering.py` at the plugins-repo root, which this repo already trusts
  to write unattended. A report-only design would leave the exact gap this exists
  to close sitting there until a human happens to read the notice.
- **stdlib-only Python, not PowerShell/bash.** Every other hook script in this
  system is PowerShell (`.ps1`/`.ps1.txt`) with a bash counterpart, per
  `cross-os-compatibility.md`'s "both OS forms" contract -- but that contract
  exists because those scripts speak each tool's *hook JSON protocol* (stdin/
  stdout shapes differ per tool), which is genuinely OS/shell-shaped work. This
  script's actual job -- parse YAML-ish frontmatter, diff two sets of skill
  names, insert markdown table rows -- is markdown/text processing that Python's
  stdlib handles far more reliably than PowerShell regex, and Python is already
  a load-bearing dependency in this repo (`lint_plugins.py`, every
  `context-closure` script). One script, one implementation, invoked identically
  (`python scripts/sync_manual_skill_routing.py`) from all three tools' hook
  command fields -- no Kiro/Claude/Cursor-specific wrapper needed for the LOGIC,
  only for each tool's stdout-shape expectation (see the three thin hook scripts
  this pairs with).
- **Routing files are found by content marker, not a fixed filename.** The
  canonical templates ship as `kiro-context-agents-routing.md` /
  `context-agents-routing.mdc`, but a project may rename its installed copy
  (the consuming project's Kiro file is `use-shared-agents.md`, its Cursor file is
  `project-shared-agents-routing.mdc`) -- a fixed-filename lookup would silently
  miss both. Instead this scans each tool's steering/rules directory for a file
  whose content contains a routing heading that is exactly "Manual-only skills"
  (an optional "N. " prefix is allowed). A prose heading such as
  "Manual-only skills must be offered, not performed" is not a routing table
  and must not be selected — that match used to append skill rows into
  universal-standards. A later pass removes those rows when they still sit
  immediately above that prose heading. It deletes only `| `/skill-name` |`
  rows (and blank lines between repeated copies) and stops at any other line,
  so a real routing table under `## Manual-only skills` is left alone.
- **Presence test is "does `` `/skill-name` `` appear anywhere in the section",
  not "does a whole matching row exist".** the consuming project's Claude table combines several
  skills into one comma-separated row (`` `/plugin-bootstrap`, `/plugin-contribution`, ... ``)
  rather than one row per skill. A strict per-row match would treat every one of
  those as missing and duplicate them. Scanning the whole Manual-only section for
  the bare `` `/name` `` token, regardless of which row it's inside, avoids that
  false positive. New skills are still always appended as their own new row --
  this script never tries to imitate the older combined-row style.
- **Idempotent.** A second run against an unchanged plugins root makes no edits,
  because the presence scan above already finds every previously-appended row.

Usage:
    python scripts/sync_manual_skill_routing.py             # sync, write changes
    python scripts/sync_manual_skill_routing.py --check      # report only, exit 1 on drift, no writes
    python scripts/sync_manual_skill_routing.py --plugins-root PATH   # skip auto-detection
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Global skill-discovery dirs each deploy script junctions plugin skills into.
# Used to auto-detect the plugins root without requiring a project config file:
# resolve context-bootstrap's junction target (always deployed, since context is
# the plugin bootstrap itself depends on) and walk up from
# <root>/context/skills/context-bootstrap to <root>.
_GLOBAL_SKILL_DIRS = (
    Path.home() / ".kiro" / "skills",
    Path.home() / ".claude" / "skills",
    Path.home() / ".cursor" / "skills",
)
# Project-level skill dirs, in case plugin skills were deployed with -Project
# rather than globally (see deploy.py kiro/-cursor.ps1/-claude.ps1's -Project flag).
_PROJECT_SKILL_DIRS = (
    Path(".kiro") / "skills",
    Path(".claude") / "skills",
    Path(".cursor") / "skills",
)

# A routing-table heading only. Prose like "Manual-only skills must be offered,
# not performed" shares the words and must not match — session-start sync was
# appending skill rows into universal-standards on that looser pattern.
_MANUAL_HEADING_RE = re.compile(
    r"^##+\s+(?:\d+\.\s*)?Manual-only skills\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# The universal-standards sentence the old loose matcher treated as a table.
_PROSE_HEADING_RE = re.compile(
    r"^##+\s+Manual-only skills must be offered, not performed\s*$",
    re.IGNORECASE,
)
# Rows this script itself inserts: `| `/skill-name` | description |`
_INJECTED_ROW_RE = re.compile(
    r"^\|\s*`/([a-z0-9]+(?:-[a-z0-9]+)*)`\s*\|.*\|\s*$",
    re.IGNORECASE,
)
_SLASH_SKILL_RE = re.compile(r"`/([a-z0-9]+(?:-[a-z0-9]+)*)`")
_TABLE_ROW_RE = re.compile(r"^\|.+\|$")
_SECTION_HEADING_RE = re.compile(r"^##+\s")


def find_plugins_root() -> Path | None:
    """Locate the canonical plugins root via a deployed skill's junction target.

    Every consuming project that ran any deploy script has `context-bootstrap`
    junctioned somewhere (it's the skill that bootstraps a project in the first
    place). Resolving that junction's real target and walking up three levels
    (`<root>/context/skills/context-bootstrap` -> `<root>`) needs no project
    config file to maintain. Falls back through global dirs, then project-level
    dirs, then gives up (returns None) rather than guessing.
    """
    for base in (*_GLOBAL_SKILL_DIRS, *_PROJECT_SKILL_DIRS):
        candidate = base / "context-bootstrap"
        if not candidate.exists():
            continue
        real = Path(os.path.realpath(candidate))
        root = real.parent.parent.parent  # context-bootstrap -> skills -> context -> root
        if (root / "context" / "skills").is_dir():
            return root
    return None


@dataclass(frozen=True)
class ManualSkill:
    name: str
    description: str


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal frontmatter parser: enough for name/description/disable-model-invocation.

    Deliberately not a YAML parser (no PyYAML dependency, stdlib only) -- mirrors
    the same small folding logic `lint_plugins.py`'s own `parse_frontmatter` uses,
    reimplemented locally rather than imported, since this script must stay
    self-contained (it runs from a project's own `scripts/`, not from inside the
    plugins repo, so it cannot assume `lint_plugins.py` is importable).
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[3:end]
    fields: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fields[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] += " " + line.strip()
    return fields


def find_manual_only_skills(plugins_root: Path) -> tuple[ManualSkill, ...]:
    """Every skill across every plugin declaring `disable-model-invocation: true`."""
    found: list[ManualSkill] = []
    for plugin_dir in sorted(plugins_root.iterdir()):
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            md = skill_dir / "SKILL.md"
            if not md.is_file():
                continue
            fm = _parse_frontmatter(md.read_text(encoding="utf-8"))
            if fm.get("disable-model-invocation", "").strip().lower() == "true":
                name = fm.get("name", skill_dir.name)
                desc = fm.get("description", "")
                found.append(ManualSkill(name=name, description=desc))
    return tuple(found)


def _find_manual_section(lines: list[str]) -> tuple[int, int] | None:
    """Return (start, end) line indices of the Manual-only skills section.

    `start` is the heading line; `end` is the line index of the next `##`+
    heading, or len(lines) if the section runs to end of file.
    """
    start = None
    for i, line in enumerate(lines):
        if _SECTION_HEADING_RE.match(line) and _MANUAL_HEADING_RE.search(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _SECTION_HEADING_RE.match(lines[i]):
            end = i
            break
    return start, end


def _skills_already_listed(lines: list[str], start: int, end: int) -> set[str]:
    listed: set[str] = set()
    for line in lines[start:end]:
        listed.update(_SLASH_SKILL_RE.findall(line))
    return listed


def sync_routing_file(path: Path, manual_skills: tuple[ManualSkill, ...]) -> list[str]:
    """Sync one routing file. Returns the list of skill names appended (empty if none)."""
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    section = _find_manual_section(lines)
    if section is None:
        return []  # this file has no manual-only-skills section; not this script's concern
    start, end = section

    listed = _skills_already_listed(lines, start, end)
    missing = [s for s in manual_skills if s.name not in listed]
    if not missing:
        return []

    # Insert new rows right after the last existing table row in the section
    # (or right after the heading if the section has no table yet).
    insert_at = start
    for i in range(start, end):
        if _TABLE_ROW_RE.match(lines[i].strip()):
            insert_at = i + 1

    new_rows = [f"| `/{s.name}` | {s.description} |" for s in missing]
    lines[insert_at:insert_at] = new_rows

    new_text = newline.join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += newline
    path.write_text(new_text, encoding="utf-8", newline="")
    return [s.name for s in missing]


def _steering_files(project_root: Path) -> tuple[Path, ...]:
    found: list[Path] = []
    for d in (
        project_root / ".kiro" / "steering",
        project_root / ".claude",
        project_root / ".cursor" / "rules",
    ):
        if not d.is_dir():
            continue
        found.extend(sorted(d.glob("*.md")))
        found.extend(sorted(d.glob("*.mdc")))
    return tuple(found)


def misplaced_skill_row_spans(lines: list[str]) -> list[tuple[int, int, list[str]]]:
    """Spans of injected skill rows sitting immediately above the prose heading.

    Each span is `(start, end, skill names)` with `end` exclusive. Blank lines
    between repeated copies are included. The blank line that separates the
    block from the previous paragraph is not.
    """
    spans: list[tuple[int, int, list[str]]] = []
    for heading_at, line in enumerate(lines):
        if not _PROSE_HEADING_RE.match(line.strip()):
            continue
        i = heading_at - 1
        start = heading_at
        names: list[str] = []
        while i >= 0:
            stripped = lines[i].strip()
            match = _INJECTED_ROW_RE.match(stripped)
            if match:
                names.append(match.group(1))
                start = i
                i -= 1
                continue
            if stripped == "":
                j = i - 1
                while j >= 0 and lines[j].strip() == "":
                    j -= 1
                if j >= 0 and _INJECTED_ROW_RE.match(lines[j].strip()):
                    i -= 1
                    continue
            break
        if start < heading_at:
            spans.append((start, heading_at, names))
    return spans


def strip_misplaced_skill_rows(path: Path, *, write: bool = True) -> list[str]:
    """Remove injected rows above the universal-standards prose heading.

    Returns the skill names removed (or, when `write` is false, the names that
    would be removed). Empty when the file is already clean.
    """
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    spans = misplaced_skill_row_spans(lines)
    if not spans:
        return []
    names: list[str] = []
    for start, end, span_names in reversed(spans):
        del lines[start:end]
        names.extend(span_names)
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    if write:
        new_text = newline.join(lines)
        if text.endswith(("\n", "\r\n")) and not new_text.endswith(("\n", "\r\n")):
            new_text += newline
        path.write_text(new_text, encoding="utf-8", newline="")
    return seen


def find_routing_files(project_root: Path) -> tuple[Path, ...]:
    """Every file that plausibly holds a Manual-only skills section for this tool.

    Scanned by content marker (see module docstring) across each tool's
    steering/rules directory, rather than assuming a fixed filename -- a project
    may have renamed its installed copy from the canonical template's name.
    """
    candidates: list[Path] = []
    for f in _steering_files(project_root):
        try:
            if _MANUAL_HEADING_RE.search(f.read_text(encoding="utf-8")):
                candidates.append(f)
        except OSError:
            continue
    return tuple(candidates)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report only, no writes; exit 1 on drift")
    parser.add_argument("--plugins-root", type=Path, default=None, help="skip auto-detection")
    parser.add_argument("--project-root", type=Path, default=Path("."), help="defaults to cwd")
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    repaired: dict[str, list[str]] = {}
    for standards in _steering_files(project_root):
        try:
            removed = strip_misplaced_skill_rows(standards, write=not args.check)
        except OSError:
            continue
        if removed:
            repaired[str(standards)] = removed

    plugins_root = args.plugins_root or find_plugins_root()
    if plugins_root is None:
        repair_verb = "would remove misplaced rows from" if args.check else "removed misplaced rows from"
        for f, names in repaired.items():
            print(f"plugin-routing-sync: {repair_verb} {f}: {', '.join(names)}")
        print("plugin-routing-sync: could not locate the plugins root (no deployed context-bootstrap junction found) -- skipping.")
        return 1 if args.check and repaired else 0  # fail open; never a session blocker

    manual_skills = find_manual_only_skills(plugins_root)
    routing_files = find_routing_files(project_root)

    if not routing_files and not repaired:
        print("plugin-routing-sync: no routing file with a Manual-only skills section found -- skipping.")
        return 0

    all_changes: dict[str, list[str]] = {}
    for f in routing_files:
        if args.check:
            text = f.read_text(encoding="utf-8")
            lines = text.splitlines()
            section = _find_manual_section(lines)
            if section is None:
                continue
            start, end = section
            listed = _skills_already_listed(lines, start, end)
            missing = [s.name for s in manual_skills if s.name not in listed]
            if missing:
                all_changes[str(f)] = missing
        else:
            added = sync_routing_file(f, manual_skills)
            if added:
                all_changes[str(f)] = added

    repair_verb = "would remove misplaced rows from" if args.check else "removed misplaced rows from"
    for f, names in repaired.items():
        print(f"plugin-routing-sync: {repair_verb} {f}: {', '.join(names)}")

    if not all_changes:
        if repaired and not args.check:
            return 0
        if not repaired:
            print("plugin-routing-sync: routing tables already cover every manual-only skill.")
        return 1 if args.check and repaired else 0

    verb = "missing from" if args.check else "added to"
    for f, names in all_changes.items():
        print(f"plugin-routing-sync: {', '.join(names)} {verb} {f}")

    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
