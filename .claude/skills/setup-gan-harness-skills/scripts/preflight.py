#!/usr/bin/env python3
"""setup-gan-harness-skills pre-flight.

Walks the target repo to gather state the SKILL needs before walking
the user through Sections A-E. Emits env-style stdout the SKILL sources.

Usage:
  preflight.py --target <path>

Exit:
  0 — clean preflight; output env vars
  1 — fatal collision (live batch / both CLAUDE.md+AGENTS.md / target == source)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def is_gan_harness_source(path: Path) -> bool:
    """Heuristic: is this path a gan-harness clone (not a target)?

    Marker = docs/maintainer/design/agent-prompt-doctrine.md exists.
    Maintainer-only file (excluded from setup copy), reliably present
    in any gan-harness clone, replaces the older gan-harness.md marker
    after that file was consolidated into the top-level README.
    """
    return (path / "docs" / "maintainer" / "design" / "agent-prompt-doctrine.md").is_file()


def specs_batch_non_empty(target: Path) -> bool:
    """Return True iff specs/_batch/ has files other than .gitkeep."""
    batch = target / "specs" / "_batch"
    if not batch.is_dir():
        return False
    for entry in batch.iterdir():
        if entry.name != ".gitkeep":
            return True
    return False


def git_remote_url(target: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def is_git_repo(target: Path) -> bool:
    return (target / ".git").exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    args = ap.parse_args()

    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"ERROR: target is not a directory: {target}", file=sys.stderr)
        return 1

    # Refuse to run if invoked inside gan-harness's own source.
    if is_gan_harness_source(target):
        print(
            "ERROR: target appears to be the gan-harness source repo itself. "
            "Run setup from a fresh target project.",
            file=sys.stderr,
        )
        return 1

    has_claude_md = (target / "CLAUDE.md").is_file()
    has_agents_md = (target / "AGENTS.md").is_file()

    # Pocock rule: never both. If both exist, abort — user must pick one.
    if has_claude_md and has_agents_md:
        print(
            "ERROR: both CLAUDE.md and AGENTS.md exist in target. Pocock "
            "convention is to pick one. Remove or merge one before re-running.",
            file=sys.stderr,
        )
        return 1

    if specs_batch_non_empty(target):
        print(
            "ERROR: specs/_batch/ has live batch artefacts. Finish "
            "/finalize or clear the batch before re-running setup.",
            file=sys.stderr,
        )
        return 1

    has_dot_claude = (target / ".claude").is_dir()
    if has_dot_claude:
        print(
            "ERROR: target already has a .claude/ directory. setup is for "
            "fresh targets; for an existing setup, edit files manually.",
            file=sys.stderr,
        )
        return 1

    has_readme = (target / "README.md").is_file()

    print(f"TARGET={target}")
    print(f"IS_GIT={'true' if is_git_repo(target) else 'false'}")
    print(f"GIT_REMOTE={git_remote_url(target)}")
    print(f"HAS_CLAUDE_MD={'true' if has_claude_md else 'false'}")
    print(f"HAS_AGENTS_MD={'true' if has_agents_md else 'false'}")
    print(f"HAS_DOT_CLAUDE=false")
    print(f"HAS_README={'true' if has_readme else 'false'}")
    print(f"BATCH_NON_EMPTY=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
