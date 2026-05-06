#!/usr/bin/env python3
"""validate_plan.py — Claude PostToolUse hook: validate feature-list.json.

After every Write / Edit / MultiEdit on specs/_batch/feature-list.json,
run the three plan-workflow check scripts:

    1. plan_validator.py     — JSON Schema + DAG
    2. lift_capabilities.py  — duplicate ids, decision_refs resolve, ...
    3. plan_lint.py          — phase-name reject, UI feature must have l5_smoke_path

If any of them exits non-zero, this hook collects every script's
stdout / stderr into one combined error message, writes it to stderr,
and exits 2. The planner subagent sees the error as a tool failure
and can edit the file to fix, which re-fires the hook. On all-pass,
the hook exits 0 silently.

All other tool calls / other file paths exit 0 silently.

Input:  Claude Code PostToolUse JSON on stdin
        (tool_name, tool_input.file_path, cwd, ...)
Output: stderr message listing every failed script's output, exit 2;
        silent exit 0 otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Tools that can mutate file content. Read/Grep/Glob/Bash do not write
# the file directly so are out of scope; if a Bash command writes the
# file, we miss it — acceptable, the planner is supposed to use Write.
WATCHED_TOOLS = {"Write", "Edit", "MultiEdit"}

# Suffix match — works regardless of repo absolute path. The contract
# is that planner ALWAYS writes to specs/_batch/feature-list.json (the
# planner-locked path); other locations are out of scope.
WATCHED_PATH_SUFFIX = "specs/_batch/feature-list.json"

# All scripts must exit 0 on PASS, non-zero on FAIL. Order matters:
# the cheaper / structural checks come first so the planner sees them
# before semantic / lint failures.
CHECK_SCRIPTS = [
    ".claude/skills/plan-workflow/scripts/plan_validator.py",
    ".claude/skills/plan-workflow/scripts/lift_capabilities.py",
    ".claude/skills/plan-workflow/scripts/plan_lint.py",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # malformed payload — fail-open, never block on infra glitches
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in WATCHED_TOOLS:
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(WATCHED_PATH_SUFFIX):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not project_dir:
        return 0

    project_dir = Path(project_dir)
    target = project_dir / WATCHED_PATH_SUFFIX
    if not target.exists():
        # write claimed to land but file isn't there — let the
        # underlying write error surface itself; don't add noise.
        return 0

    failures: list[tuple[str, str, str]] = []  # (script_name, stdout, stderr)
    for script_rel in CHECK_SCRIPTS:
        script = project_dir / script_rel
        if not script.exists():
            # this scaffolder isn't installed here — skip silently so
            # projects without plan-workflow aren't blocked
            continue
        result = subprocess.run(
            [sys.executable, str(script), str(target)],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=25,
        )
        if result.returncode != 0:
            failures.append((script.name, result.stdout, result.stderr))

    if not failures:
        return 0

    msg_lines = [
        "⛔ feature-list.json failed plan-workflow validation.",
        f"  ({len(failures)} of {len(CHECK_SCRIPTS)} check scripts reported FAIL)",
        "Fix the issues below and re-write specs/_batch/feature-list.json.",
        "This hook re-fires on every Write / Edit / MultiEdit to that file.",
        "",
    ]
    for name, out, err in failures:
        msg_lines.extend([
            f"━━━ {name} ━━━",
            "stdout:",
            (out or "").rstrip() or "(empty)",
            "stderr:",
            (err or "").rstrip() or "(empty)",
            "",
        ])
    sys.stderr.write("\n".join(msg_lines))
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        # validator hung — fail-open with a notice rather than block
        # the planner indefinitely
        sys.stderr.write(
            "validate_plan.py: plan_validator.py timed out after 25s; not blocking.\n"
        )
        sys.exit(0)
