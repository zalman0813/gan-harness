---
name: python
description: Python stack reference library for gan-harness. Vendors conventions for Python 3.11+ CLI projects (argparse / click, pytest, Ruff, mypy, src/ layout). Make sure to use this skill whenever harness agents work on Python code or need Python-specific idioms.
---

# Python Stack Skill

Reference library of Python conventions for a stdlib-leaning CLI project
(`kvstore`). Downstream harness agents (planner, generator, evaluator,
/finalize) consult specific references as needed; this SKILL.md is the
index.

Scope: Starter — seed topics covering project layout, CLI entry,
testing, lint/typecheck.

## When to use

- Generator writes or edits Python code in this repo
- Planner needs Python-specific test-runner / module / packaging conventions
- /finalize regenerates docs from Python code

## References

- [layout.md](references/layout.md) — `src/` layout, package vs module, `__init__.py`
- [cli.md](references/cli.md) — argparse / click entry points, `pyproject.toml [project.scripts]`
- [testing.md](references/testing.md) — pytest conventions, fixtures, `tests/` layout
- [lint-typecheck.md](references/lint-typecheck.md) — Ruff + mypy `--strict` defaults
- [upstream.md](references/upstream.md) — provenance of vendored material

## Provenance

See [references/upstream.md](references/upstream.md). This Starter skill
was scaffolded from canonical, well-known Python conventions (PEP 621,
pytest docs, Ruff docs, mypy docs). No URLs were fetched during
scaffolding; the operator should re-vendor with WebFetch when deeper
references are needed.

## Stack-specific anti-patterns

- Mixing flat-layout and src-layout in one repo — pick `src/kvstore/` and stay.
- Putting tests inside the package (`src/kvstore/tests/`) — keep `tests/`
  at repo root so `pytest` discovery and `mypy --strict src/` stay clean.
- Skipping `pyproject.toml [project.scripts]` and relying on
  `python -m kvstore` only — install with `pip install -e .` so the
  `kvstore` console entrypoint exists for L5 smoke tests.
