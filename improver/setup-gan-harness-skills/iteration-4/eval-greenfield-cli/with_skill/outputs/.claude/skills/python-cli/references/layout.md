# Project layout (Python CLI)

Default layout for a Python CLI app under gan-harness:

```
<project>/
  pyproject.toml          # build + tool config (Ruff, mypy, pytest)
  src/
    <pkg>/                # underscored package name; mirrors project slug
      __init__.py         # exports __version__ only
      __main__.py         # `python -m <pkg>` entry; calls cli.main()
      cli.py              # argparse wiring (parser, subparsers, dispatch)
      commands/           # one file per verb; pure I/O boundary
        __init__.py
        <verb>.py         # def run(args) -> int (exit code)
      core/               # pure-function domain code; no I/O, no argparse
        __init__.py
        ...
  tests/
    unit/
      test_<module>.py
    smoke/
      test_cli_smoke.py   # subprocess-level end-to-end
```

## Entrypoint convention

`pyproject.toml` should declare a console_scripts entry so the CLI is invokable
by its kebab-case name after `pip install -e .`:

```toml
[project.scripts]
<project-slug> = "<pkg>.cli:main"
```

`__main__.py` enables `python -m <pkg>` for ad-hoc / test invocations:

```python
# src/<pkg>/__main__.py
from <pkg>.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## Module boundaries

- `cli.py` is the ONLY module that imports `argparse`. Everything else
  receives parsed values (or plain function args).
- `commands/<verb>.py` translates parsed args into calls on `core/`. It
  owns user-facing exit codes and error messages.
- `core/` is pure: no argparse, no sys.exit, no print. Returns values or
  raises domain exceptions that `commands/` translates.

This split keeps `core/` directly unit-testable without subprocess or
argparse fixtures, and keeps `commands/` thin enough to cover with smoke.
