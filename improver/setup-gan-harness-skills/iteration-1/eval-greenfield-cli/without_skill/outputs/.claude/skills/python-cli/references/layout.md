# Layout — Python CLI with src/ layout

Project skeleton (PEP 621, src layout):

```
kvstore/
├── pyproject.toml
├── src/
│   └── kvstore/
│       ├── __init__.py     # package marker; may expose __version__
│       ├── __main__.py     # enables `python -m kvstore`
│       ├── cli.py          # argparse wiring; defines build_parser() + main()
│       └── ...             # one module per domain concern
└── tests/
    ├── __init__.py
    └── test_cli.py
```

## Why src/ layout

`src/` prevents accidental imports of the in-repo package when running
tests from the project root — tests must import the installed
distribution (editable install via `pip install -e .`), which mirrors
how end users will use the CLI. This catches "works in dev, broken when
packaged" before it reaches users.

## Entry point

In `pyproject.toml`:

```toml
[project]
name = "kvstore"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
kvstore = "kvstore.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

After `pip install -e .`, both `kvstore <args>` and
`python -m kvstore <args>` work; the test suite invokes `main()`
in-process.

## `__main__.py`

```python
"""Enable `python -m kvstore`."""
from kvstore.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## Module boundaries

Keep one concern per module. For kvstore (a kv-store inspector for
local JSON config files), expected modules grow with sprints:

- `cli.py` — argparse parser + `main()` dispatch
- `loader.py` — load + validate JSON files (returns a typed view)
- `inspector.py` — query / traverse / pretty-print kv data

Do NOT pre-create modules speculatively; let the sprint plan drive them.
