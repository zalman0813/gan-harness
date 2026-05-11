# Python CLI — Project Layout

## Canonical src-layout

```
<project>/
  pyproject.toml
  README.md
  src/
    <package>/
      __init__.py
      __main__.py
      cli.py
  tests/
    __init__.py
    unit/
    smoke/
```

Why `src/`: ensures the package is imported only after install (`pip install -e .`),
preventing the "works on dev, fails in prod" trap where tests accidentally
import from CWD instead of the installed package.

## pyproject.toml (PEP 621) minimum

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "kvstore"
version = "0.1.0"
description = "A small kv-store inspector for local JSON config files."
requires-python = ">=3.11"
dependencies = []

[project.scripts]
kvstore = "kvstore.cli:main"

[project.optional-dependencies]
dev = ["ruff", "mypy", "pytest"]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Entry point pattern

`src/<package>/cli.py`:

```python
def main() -> int:
    """CLI entry point. Returns process exit code."""
    ...
    return 0
```

`src/<package>/__main__.py`:

```python
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

This makes both `kvstore ...` (via `[project.scripts]`) and `python -m kvstore ...`
work identically.
