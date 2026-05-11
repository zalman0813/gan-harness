# Python project layout

Adopt the `src/` layout for `kvstore`. Tradeoff vs flat-layout is well
known: src-layout guarantees that tests run against the *installed*
package (via editable install) and not against the working-tree
directory, which catches packaging bugs early.

```
kvstore/
├── pyproject.toml
├── src/
│   └── kvstore/
│       ├── __init__.py      # package marker; `__version__` lives here
│       ├── __main__.py      # enables `python -m kvstore`
│       ├── cli.py           # argparse / click entry point (see cli.md)
│       ├── inspector.py     # core module — load & query JSON kv-stores
│       └── ...
└── tests/
    ├── conftest.py          # shared fixtures (tmp_path, sample configs)
    ├── test_cli.py
    └── test_inspector.py
```

## Module / package rules

- Each subdirectory of `src/kvstore/` that contains code must have an
  `__init__.py`. Empty `__init__.py` is fine.
- Public surface lives at `kvstore.__init__`. Submodule-private names use
  the leading-underscore convention.
- Re-exports use explicit `from .inspector import KVStore as KVStore`
  (the `as Name` form keeps `ruff --select=F401` and mypy `--strict`
  happy).
- No circular imports. If A imports B and B imports A, extract the
  shared types into a `kvstore.types` module.

## Install for development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

`[dev]` extras live in `pyproject.toml [project.optional-dependencies]`
and include `pytest`, `ruff`, `mypy`.
