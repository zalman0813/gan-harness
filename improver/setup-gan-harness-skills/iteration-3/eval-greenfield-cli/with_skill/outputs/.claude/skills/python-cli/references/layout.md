# Python CLI layout and argparse idiom

## Package layout

```
src/<pkg>/
    __init__.py
    __main__.py        # python -m <pkg> entrypoint; calls cli.main()
    cli.py             # argparse + main(argv) -> int
    ...                # domain modules
tests/
    test_cli.py
pyproject.toml
```

The `src/`-layout is preferred so tests cannot accidentally import the
in-tree package without it being installed (catches missing `__init__`
files and stale wheels early).

## Entrypoint idiom

```python
# src/<pkg>/__main__.py
import sys

from . import cli


if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli.main(sys.argv[1:]))
```

```python
# src/<pkg>/cli.py
import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="<pkg>",
        description="<one-line description>",
    )
    # subparsers, args, etc.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # dispatch on args.command, return exit code
    return 0
```

## Why `main(argv) -> int`

- Testable. `cli.main(["sub", "--flag"])` returns an int we can assert
  on; no need to patch `sys.exit` or capture `SystemExit`.
- Composable. Other Python code can call the CLI as a function without
  spawning a subprocess.

## Exit codes

- `0` — success.
- `1` — generic failure (user-facing error, expected).
- `2` — argparse usage error (argparse emits this automatically).
- `>=3` — reserve for stack-specific failure modes when needed.

## pyproject.toml minimum

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "<pkg>"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
<pkg> = "<pkg>.cli:main"

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]
```
