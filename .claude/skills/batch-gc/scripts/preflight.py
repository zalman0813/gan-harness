#!/usr/bin/env python3
"""/finalize pre-flight validation.

Usage:
    python3 ${CLAUDE_SKILL_DIR}/scripts/preflight.py [feature-list-path]
    python3 ${CLAUDE_SKILL_DIR}/scripts/preflight.py --print-slug [plan-md-path]

Modes:
  Default: validates the batch is ready for /finalize and prints env vars.
  --print-slug: parses H1 of specs/_batch/plan.md and prints only the slug.

Validates (default mode):
  1. Feature list file exists + parses as JSON
  2. meta.baseCommit is present and valid (exists in git history)
  3. All features are in terminal state (DONE or BLOCKED)
  4. specs/_batch/plan.md exists (slug source)
  5. docs/progress/DREAM-gen.md + docs/progress/DREAM-eval.md exist

Exit 0 = OK, exit 1 = validation failed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PLAN_PATH = Path("specs/_batch/plan.md")
DREAM_GEN = Path("docs/progress/DREAM-gen.md")
DREAM_EVAL = Path("docs/progress/DREAM-eval.md")


def parse_slug_from_plan(plan_path: Path) -> str | None:
    """Extract slug from plan.md H1: `# Plan — batch {slug}`."""
    if not plan_path.exists():
        return None
    first_line = plan_path.read_text(encoding="utf-8").splitlines()[0].strip()
    # Accept either U+2014 em-dash or ASCII hyphen as separator
    m = re.match(r"^#\s*Plan\s*[—\-]\s*batch\s+(.+?)\s*$", first_line)
    return m.group(1) if m else None


def print_slug_mode(argv: list[str]) -> int:
    plan_path = Path(argv[0]) if argv else PLAN_PATH
    slug = parse_slug_from_plan(plan_path)
    if not slug:
        print(f"ERROR: could not parse slug from H1 of {plan_path}", file=sys.stderr)
        return 1
    print(slug)
    return 0


def validate_default_mode(argv: list[str]) -> int:
    feature_list_path = Path(argv[0]) if argv else Path("docs/feature-list.json")

    try:
        data = json.loads(feature_list_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: {feature_list_path} not found.", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: {feature_list_path} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    # Check baseCommit
    base_commit = data.get("meta", {}).get("baseCommit")
    if not base_commit or base_commit == "MISSING":
        print("ERROR: No baseCommit in feature-list. Add it manually.", file=sys.stderr)
        return 1
    result = subprocess.run(
        ["git", "cat-file", "-t", base_commit],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: baseCommit {base_commit} not found in git history.", file=sys.stderr)
        return 1

    # Check all terminal
    non_terminal = [
        f["id"]
        for f in data["features"]
        if f["status"] not in ("DONE", "BLOCKED")
    ]
    if non_terminal:
        print(
            f"ERROR: Features {non_terminal} not terminal. Finish the batch first.",
            file=sys.stderr,
        )
        return 1

    # Check plan.md + slug
    slug = parse_slug_from_plan(PLAN_PATH)
    if not slug:
        print(
            f"ERROR: {PLAN_PATH} missing or H1 not in `# Plan — batch {{slug}}` form.",
            file=sys.stderr,
        )
        return 1

    # Check DREAM files (both required; /execution-loop tail must have run)
    missing_dreams = [p for p in (DREAM_GEN, DREAM_EVAL) if not p.exists()]
    if missing_dreams:
        names = ", ".join(str(p) for p in missing_dreams)
        print(
            f"ERROR: DREAM file(s) missing: {names}. Run /execution-loop first "
            "so gen-dreamer + eval-dreamer emit proposals.",
            file=sys.stderr,
        )
        return 1

    # Summary to stdout (env-var style for easy sourcing)
    done = [f["id"] for f in data["features"] if f["status"] == "DONE"]
    blocked = [f["id"] for f in data["features"] if f["status"] == "BLOCKED"]
    print(f"SLUG={slug}")
    print(f"BASE_COMMIT={base_commit}")
    print(f"DONE={','.join(done)}")
    print(f"BLOCKED={','.join(blocked)}")
    print(f"TOTAL={len(data['features'])}")
    print(f"DREAM_GEN={DREAM_GEN}")
    print(f"DREAM_EVAL={DREAM_EVAL}")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--print-slug":
        return print_slug_mode(argv[1:])
    return validate_default_mode(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
