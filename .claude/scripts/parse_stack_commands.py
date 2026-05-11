#!/usr/bin/env python3
"""parse_stack_commands.py — read a stack skill's SKILL.md `## Commands`
markdown table and emit a single command string (with {scope} substituted).

Replaces the legacy `sensors.ini` structured format. SKILL.md `## Commands`
becomes the single source of truth: LLM agents (planner / generator /
evaluator) read the table as natural markdown; the pre-commit hook reads
it via this small Python parser. No INI parser, no duplicate file.

Table format expected in <stack>/SKILL.md:

    ## Commands

    Harness gate contract. Pre-commit hook reads this via
    `.claude/scripts/parse_stack_commands.py`. Required keys:
    `lint.fix`, `lint.check`, `typecheck`, `test.unit`. Optional:
    `test.smoke`. `{scope}` is substituted at invocation time.

    | Key | Command |
    |---|---|
    | lint.fix | `ruff check --fix --silent {scope}` |
    | lint.check | `ruff check {scope}` |
    | typecheck | `mypy --strict {scope}` |
    | test.unit | `pytest -x --tb=short {scope}` |
    | test.smoke | `pytest --no-header {scope}` |

Usage:
    parse_stack_commands.py <stack-name> --key lint.check [--scope "f1 f2"]
    parse_stack_commands.py --skill-path .claude/skills/python-cli/SKILL.md \\
        --key test.unit --scope tests/
    parse_stack_commands.py --list                  # auto-detect stack, list all keys
    parse_stack_commands.py --validate <stack>      # exit non-zero if any required key missing

Output: one command string with {scope} substituted, to stdout.

Exit:
    0  OK
    1  SKILL.md / table / key not found
    2  malformed table or other parser error
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_KEYS = ("lint.fix", "lint.check", "typecheck", "test.unit")
OPTIONAL_KEYS = ("test.smoke",)
KNOWN_KEYS = REQUIRED_KEYS + OPTIONAL_KEYS


def find_skill(
    stack_name: str | None,
    skill_path: str | None,
    project_dir: Path,
) -> Path | None:
    """Locate SKILL.md by stack name, explicit path, or auto-detect.

    Auto-detect = first .claude/skills/*/SKILL.md that contains a
    `## Commands` heading. Used by the pre-commit hook in single-stack
    targets (the 99% case).
    """
    if skill_path:
        p = Path(skill_path)
        return p if p.is_file() else None
    if stack_name:
        p = project_dir / ".claude" / "skills" / stack_name / "SKILL.md"
        return p if p.is_file() else None
    skills_root = project_dir / ".claude" / "skills"
    if not skills_root.is_dir():
        return None
    for d in sorted(skills_root.iterdir()):
        skill = d / "SKILL.md"
        if not skill.is_file():
            continue
        try:
            text = skill.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"^##\s+Commands\s*$", text, re.MULTILINE):
            return skill
    return None


def parse_commands(skill_text: str) -> dict[str, str]:
    """Extract the `## Commands` markdown table into {key: command_string}.

    Header / separator rows are skipped. Only rows whose first cell is a
    KNOWN_KEYS entry are recorded; foreign rows are silently ignored so
    authors can mix in additional documentation rows safely.
    """
    m = re.search(r"^##\s+Commands\s*$", skill_text, re.MULTILINE)
    if not m:
        return {}
    section = skill_text[m.end():]
    next_h2 = re.search(r"^##\s+\S", section, re.MULTILINE)
    if next_h2:
        section = section[: next_h2.start()]

    out: dict[str, str] = {}
    for line in section.splitlines():
        if re.match(r"^\|\s*[-:|\s]+\|", line):
            continue
        row = re.match(r"^\|\s*([\w.]+)\s*\|\s*(.+?)\s*\|", line)
        if not row:
            continue
        key, cmd = row.group(1), row.group(2)
        cmd = cmd.strip().strip("`").strip()
        if key in KNOWN_KEYS:
            out[key] = cmd
    return out


def render(command_template: str, scope: str) -> str:
    return command_template.replace("{scope}", scope)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "stack_name",
        nargs="?",
        default=None,
        help="Stack name under .claude/skills/<stack>/. Optional if --skill-path "
        "is given or auto-detect (single-stack target) is acceptable.",
    )
    ap.add_argument(
        "--skill-path",
        default=None,
        help="Direct path to SKILL.md (overrides stack_name).",
    )
    ap.add_argument(
        "--project-dir",
        default=".",
        help="Project root (default: cwd).",
    )
    ap.add_argument(
        "--key",
        default=None,
        help=f"One of: {' '.join(KNOWN_KEYS)}",
    )
    ap.add_argument(
        "--scope",
        default="",
        help="Value substituted for {scope} placeholder.",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List every key+command parsed from the table (TSV).",
    )
    ap.add_argument(
        "--validate",
        action="store_true",
        help="Exit non-zero if any REQUIRED_KEYS entry is missing.",
    )
    args = ap.parse_args()

    project_dir = Path(args.project_dir).resolve()
    skill = find_skill(args.stack_name, args.skill_path, project_dir)
    if skill is None:
        print(
            f"ERROR: SKILL.md not found (stack={args.stack_name!r}, "
            f"path={args.skill_path!r}, auto-detect under {project_dir})",
            file=sys.stderr,
        )
        return 1

    try:
        text = skill.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {skill}: {exc}", file=sys.stderr)
        return 2

    cmds = parse_commands(text)
    if not cmds:
        print(
            f"ERROR: {skill} has no parseable `## Commands` table",
            file=sys.stderr,
        )
        return 1

    if args.validate:
        missing = [k for k in REQUIRED_KEYS if k not in cmds]
        if missing:
            print(
                f"ERROR: {skill} missing required keys: {missing}",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {skill.parent.name} has all required keys ({list(cmds.keys())})")
        return 0

    if args.list:
        for k in KNOWN_KEYS:
            print(f"{k}\t{render(cmds.get(k, ''), args.scope)}")
        return 0

    if not args.key:
        print(
            "ERROR: provide --key, --list, or --validate. See --help.",
            file=sys.stderr,
        )
        return 1

    if args.key not in cmds:
        print(
            f"ERROR: key {args.key!r} missing from {skill}'s `## Commands` table",
            file=sys.stderr,
        )
        return 1

    print(render(cmds[args.key], args.scope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
