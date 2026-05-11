# argparse subcommands — testable CLI pattern

Stdlib `argparse` is sufficient for kvstore. Avoid third-party CLI
frameworks (Click, Typer) unless a sprint contract requires them — the
extra dependency is only worth it past a few subcommands.

## Pattern: factor parser construction

`build_parser()` returns a fresh parser; `main()` parses + dispatches.
This split is what makes the CLI unit-testable.

```python
# src/kvstore/cli.py
from __future__ import annotations
import argparse
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level parser. Pure: no side effects."""
    parser = argparse.ArgumentParser(
        prog="kvstore",
        description="Inspect local JSON config files as a kv store.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # `kvstore get <file> <key>` — print value at key
    p_get = sub.add_parser("get", help="Print the value at a key path.")
    p_get.add_argument("file", help="Path to the JSON config file.")
    p_get.add_argument("key", help="Dotted key path, e.g. db.host")

    # Add more subcommands as sprints introduce them.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns process exit code (0 = success)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "get":
        return _run_get(args)
    # argparse `required=True` makes this branch unreachable, but mypy
    # --strict wants a return on every path.
    return 2


def _run_get(args: argparse.Namespace) -> int:
    # Real handler lives in a domain module; cli.py only dispatches.
    from kvstore.inspector import get_by_path
    value = get_by_path(args.file, args.key)
    print(value)
    return 0
```

## Why `argv: Sequence[str] | None = None`

Tests pass an explicit list (`main(["get", "config.json", "db.host"])`);
production calls `main()` with no argument and argparse reads
`sys.argv[1:]` itself.

## Error handling

- Argparse handles parse errors (it calls `sys.exit(2)` on its own —
  acceptable because tests capture `SystemExit` via `pytest.raises`).
- Domain errors (file not found, key not present, invalid JSON) raise
  typed exceptions in the domain module. `main()` catches them, prints
  a single-line message to `stderr`, and returns a non-zero code.

```python
class KVError(Exception):
    """Base for all kvstore domain errors."""

# In main():
try:
    return _run_get(args)
except KVError as e:
    print(f"kvstore: {e}", file=sys.stderr)
    return 1
```

This keeps stack traces out of normal user errors while preserving them
for unexpected exceptions (which propagate and crash loudly — the
correct default for bugs).
