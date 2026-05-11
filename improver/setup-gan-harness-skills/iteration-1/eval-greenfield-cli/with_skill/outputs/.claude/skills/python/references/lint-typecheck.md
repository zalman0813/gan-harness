# Lint & typecheck

Stack defaults: **Ruff** (lint + format) + **mypy** (`--strict`).

## Ruff

Configure in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
# Conservative enabled set; expand as the project matures.
select = [
    "E", "W",   # pycodestyle
    "F",        # pyflakes
    "I",        # isort
    "B",        # bugbear
    "UP",       # pyupgrade
    "SIM",      # simplify
]
ignore = []

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]   # asserts are fine in tests
```

Invocations:
- `ruff check --fix --silent <scope>` — pre-commit autofix stage (<1s)
- `ruff check <scope>` — pre-commit verify stage + evaluator L1 (<5s)
- `ruff format <scope>` — optional; not in the gate by default

## mypy

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_unreachable = true
warn_redundant_casts = true
```

Invocations:
- `mypy --strict <scope>` — pre-commit typecheck stage + evaluator L1

`--strict` implies: `disallow_untyped_defs`, `disallow_any_generics`,
`disallow_subclassing_any`, `warn_return_any`, plus several others.
Loosen only with explicit `# type: ignore[code]` comments and a
one-line rationale on the same line.

## When mypy and Ruff disagree

Mypy wins for typing rules (`from __future__ import annotations`,
`TYPE_CHECKING` imports). Ruff wins for style and bug patterns. They
don't overlap in normal config; if you hit a real conflict, narrow the
Ruff rule with `per-file-ignores` rather than disabling mypy.

## Performance hints

- `mypy --strict` is slow on cold cache. Set `MYPY_CACHE_DIR=.mypy_cache`
  and commit `.gitignore` entry; first run is slow, subsequent runs
  cache aggressively.
- `ruff` is fast enough that scoping (passing only changed files) is a
  micro-optimization; pass `{scope}` anyway for consistency with the
  sensors.ini contract.
