#!/usr/bin/env python3
"""Append stack skill name(s) into the YAML frontmatter `skills:` list of
planner.md, generator.md, evaluator.md.

codebase-fact-finder.md is intentionally NOT touched (stack-agnostic
blindfold research).

Idempotent: if a stack name is already in the list, it's skipped.

Usage:
  wire_stack_skills.py --agents-dir <path> <stack-name>...

Frontmatter format expected (must be present, single-line flow list):
  skills: [deep-module-handbook, adr-lifecycle]

Exit:
  0 OK
  1 — frontmatter not found / malformed in any target file
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WIRE_TARGETS = ("planner.md", "generator.md", "evaluator.md")
SKILLS_LINE_RE = re.compile(r"^skills:\s*\[([^\]]*)\]\s*$", re.MULTILINE)


def wire_one(path: Path, stacks: list[str]) -> tuple[bool, str]:
    """Returns (changed, message)."""
    if not path.is_file():
        return False, f"SKIP: {path} does not exist"

    text = path.read_text(encoding="utf-8")
    m = SKILLS_LINE_RE.search(text)
    if not m:
        return False, f"WARN: {path} has no `skills: [...]` frontmatter line"

    inner = m.group(1).strip()
    current = [s.strip() for s in inner.split(",") if s.strip()] if inner else []

    added = []
    for s in stacks:
        if s not in current:
            current.append(s)
            added.append(s)

    if not added:
        return False, f"NOOP: {path} already wired ({', '.join(stacks)})"

    new_line = f"skills: [{', '.join(current)}]"
    new_text = text[:m.start()] + new_line + text[m.end():]
    path.write_text(new_text, encoding="utf-8")
    return True, f"OK: {path} += [{', '.join(added)}]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents-dir", required=True)
    ap.add_argument("stacks", nargs="+")
    args = ap.parse_args()

    agents_dir = Path(args.agents_dir).resolve()
    if not agents_dir.is_dir():
        print(f"ERROR: agents-dir not found: {agents_dir}", file=sys.stderr)
        return 1

    any_warn = False
    for fname in WIRE_TARGETS:
        changed, msg = wire_one(agents_dir / fname, args.stacks)
        print(msg)
        if msg.startswith("WARN"):
            any_warn = True

    return 1 if any_warn else 0


if __name__ == "__main__":
    sys.exit(main())
