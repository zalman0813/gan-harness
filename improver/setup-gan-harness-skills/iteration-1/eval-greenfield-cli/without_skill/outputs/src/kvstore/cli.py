"""kvstore CLI entry point.

Skeleton only — subcommands will be added per sprint contract negotiated
inside /loop. See .claude/skills/python-cli/references/argparse-subcommands.md
for the pattern.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level parser. Pure: no side effects."""
    parser = argparse.ArgumentParser(
        prog="kvstore",
        description="Inspect local JSON config files as a kv store.",
    )
    # Subparsers will be registered here as sprints add subcommands.
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns process exit code (0 = success)."""
    parser = build_parser()
    # With no subcommands yet, --help / --version exit via argparse;
    # any other input prints help and returns 0 for now.
    parser.parse_args(argv)
    parser.print_help()
    return 0
