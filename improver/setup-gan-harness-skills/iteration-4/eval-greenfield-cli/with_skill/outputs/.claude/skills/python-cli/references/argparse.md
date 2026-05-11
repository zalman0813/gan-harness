# argparse conventions

Use stdlib `argparse` (no third-party CLI lib) unless the project explicitly
requires click/typer features. Stdlib keeps the dep graph minimal and the
import cost low — both matter for CLI tools that are invoked from shells
where startup time is visible.

## Top-level parser shape

```python
# src/<pkg>/cli.py
import argparse
import sys
from typing import Sequence

from <pkg> import __version__
from <pkg>.commands import get, list_keys, set_, delete


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="<project-slug>",
        description="<one-line description>",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # one add_parser per verb; keep wiring in this file only
    p_get = sub.add_parser("get", help="Read a key from a JSON file")
    p_get.add_argument("file")
    p_get.add_argument("key")
    p_get.set_defaults(func=get.run)

    # ... etc.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
```

## Exit code convention

- `0` — success
- `1` — generic operational failure (file not found, parse error, etc.)
- `2` — usage / argument error (argparse itself uses 2)
- `>2` — domain-specific failure modes; document in the project README

`commands/<verb>.py` returns the int directly; `main()` propagates it via
`SystemExit` in `__main__.py`. Do NOT call `sys.exit()` from inside
`commands/` — return the code so callers (tests, other commands) can
compose.

## Error message convention

User-facing errors go to `sys.stderr` and the function returns a non-zero
exit code:

```python
def run(args: argparse.Namespace) -> int:
    try:
        data = load_json(args.file)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.file}: {exc.msg}", file=sys.stderr)
        return 1
    ...
```

Do not raise uncaught exceptions for expected error paths — those produce
tracebacks which are noise for CLI users. Reserve tracebacks for genuine
bugs.
