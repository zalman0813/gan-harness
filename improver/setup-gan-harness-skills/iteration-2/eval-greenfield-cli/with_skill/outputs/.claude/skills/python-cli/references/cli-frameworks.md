# Python CLI — Framework Choice

Three mainstream choices. Pick once per project; don't mix.

## argparse (stdlib)

- Zero dependencies. Built into Python.
- Verbose for nested subcommands and typed args.
- Good for: ≤3 subcommands, simple positional/flag args, stdlib-only constraint.

```python
import argparse

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kvstore")
    sub = p.add_subparsers(dest="cmd", required=True)
    get = sub.add_parser("get")
    get.add_argument("path")
    get.add_argument("key")
    return p

def main() -> int:
    args = build_parser().parse_args()
    ...
```

## click

- Decorator-driven; nested commands ergonomic.
- Mature, widely used (Flask ecosystem).
- Good for: medium CLIs with grouped subcommands and rich help text.

```python
import click

@click.group()
def cli() -> None:
    """kvstore — JSON config inspector."""

@cli.command()
@click.argument("path")
@click.argument("key")
def get(path: str, key: str) -> None:
    ...

def main() -> int:
    cli(standalone_mode=False)
    return 0
```

## typer

- Built on click; uses Python type hints for arg parsing.
- Lowest boilerplate for typed CLIs.
- Good for: type-driven CLIs, fast iteration.

```python
import typer

app = typer.Typer(help="kvstore — JSON config inspector.")

@app.command()
def get(path: str, key: str) -> None:
    ...

def main() -> int:
    app()
    return 0
```

## Decision rule for kvstore-style inspectors

- 1-3 flat commands, no fancy typing: **argparse** (zero deps).
- Subcommand tree with typed args: **typer**.
- Avoid click unless you already use it elsewhere.
