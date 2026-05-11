---
name: python-cli
description: Python CLI stack reference library for gan-harness. Vendors conventions for argparse/click/typer entry points, project layout (src/ + tests/), Ruff lint, mypy --strict typecheck, and pytest unit/smoke testing. Make sure to use this skill whenever harness agents work on Python CLI code or need Python CLI-specific idioms.
---

# Python CLI Stack Skill

Reference library of Python CLI conventions (argparse / click / typer entry-point
patterns, src-layout project structure, Ruff + mypy --strict + pytest tooling).
Downstream harness agents (planner, generator, evaluator, /finalize) consult
specific references as needed; this SKILL.md is the index.

## When to use

- Generator writes or edits code in a Python CLI project
- Planner needs Python-CLI-specific test-runner / module / layout conventions
- Evaluator runs L1/L2 verification using the sensors.ini commands
- /finalize regenerates docs from Python CLI code

## Tooling baseline

| Concern | Tool | Notes |
|---|---|---|
| Lint | Ruff | `ruff check --fix` (autofix in pre-commit) + `ruff check` (read-only gate) |
| Typecheck | mypy --strict | strict mode is the default; loosen only with cause |
| Unit tests | pytest | `pytest -x --tb=short`, scoped via {scope} |
| Smoke tests | pytest | invokes CLI entry point via `subprocess.run` / Click `CliRunner` / Typer `CliRunner` |
| Packaging | `pyproject.toml` | PEP 621 metadata + `[project.scripts]` entry-point declaration |

## Project layout

```
kvstore/
  pyproject.toml
  src/
    kvstore/
      __init__.py
      __main__.py          # `python -m kvstore`
      cli.py               # entry-point function
      ...
  tests/
    unit/
    smoke/
```

The `src/` layout prevents accidental import of the un-installed package during
test runs (forces editable install / `pip install -e .`).

## References

- [project-layout.md](references/project-layout.md) — src-layout, pyproject.toml, entry points
- [cli-frameworks.md](references/cli-frameworks.md) — argparse vs click vs typer, when to pick each
- [testing.md](references/testing.md) — pytest patterns for CLI, CliRunner, subprocess smoke

## Provenance

All references in this skill are authored from canonical Python packaging /
Ruff / mypy / pytest documentation conventions, summarized for the gan-harness
use case. No upstream HTML was fetched; see references/upstream.md if/when web
vendoring is added.

## Stack-specific anti-patterns

- **Mixing `src/` layout with `python script.py` invocation in tests.** Run via
  the installed entry point or `python -m <pkg>`; ad-hoc script invocation
  bypasses the package import path and hides packaging bugs.
- **Wrapping every CLI command in a giant try/except for "nice errors".** Let
  argparse/click/typer's built-in error reporting do its job; only catch
  exceptions you can act on.
- **Hand-rolling argparse when typer would do.** For non-trivial subcommand
  trees with typed arguments, typer collapses 100 lines of argparse into 20.
  Pick the framework once; don't mix.
