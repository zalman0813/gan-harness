# Python CLI conventions

`kvstore` is a CLI. Pick **one** of argparse (stdlib, zero deps) or
click (third-party, richer ergonomics). For a small inspector tool with
1-5 subcommands, argparse is typically enough.

## argparse skeleton (recommended for kvstore)

```python
# src/kvstore/cli.py
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kvstore",
        description="Inspect local JSON config files as kv-stores.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="Get the value at a dotted key path.")
    p_get.add_argument("file", help="Path to the JSON config file.")
    p_get.add_argument("key", help="Dotted key path (e.g. server.host).")

    p_list = sub.add_parser("keys", help="List all top-level keys.")
    p_list.add_argument("file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Dispatch to handlers; return non-zero on user-level errors.
    ...
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `__main__.py` (enables `python -m kvstore`)

```python
# src/kvstore/__main__.py
from kvstore.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## `pyproject.toml [project.scripts]`

```toml
[project.scripts]
kvstore = "kvstore.cli:main"
```

After `pip install -e .` the user can run `kvstore get config.json server.host`
from any shell.

## click alternative (skip unless deps warrant it)

```python
import click

@click.group()
def cli() -> None:
    """Inspect local JSON config files as kv-stores."""

@cli.command()
@click.argument("file")
@click.argument("key")
def get(file: str, key: str) -> None:
    ...
```

Adds a single dep (`click>=8`). Worth it only if you want `--help`
formatting niceties or nested groups beyond two levels.

## Exit code convention

- `0` — success
- `1` — user error (file not found, key not found, invalid JSON)
- `2` — usage error (argparse already returns 2 on parse failure)
- `>=64` — reserved for internal programming errors (rare)
