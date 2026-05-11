---
name: python-cli
description: Python CLI stack reference library for gan-harness. Vendors conventions for argparse-based command-line apps with src/ layout, Ruff lint, mypy --strict typecheck, and pytest unit tests. Make sure to use this skill whenever harness agents work on Python CLI code or need Python-CLI-specific idioms (argparse subcommands, src/ layout, entry points, pytest fixtures).
---

# Python CLI Stack Skill

Reference library of Python CLI conventions for the `kvstore` project — a
small kv-store inspector for local JSON config files. Downstream harness
agents (planner / generator / evaluator / finalize) consult specific
references as needed; this SKILL.md is the index.

The toolchain is intentionally small:

- **Runtime**: Python 3.11+ (stdlib only by default; add deps only when needed).
- **Layout**: `src/` layout (PEP 621). Source under `src/kvstore/`,
  tests under `tests/`.
- **CLI**: stdlib `argparse` with subcommands. Entry point declared in
  `pyproject.toml` `[project.scripts]`.
- **Lint**: Ruff (auto-fix on pre-commit, read-only check elsewhere).
- **Typecheck**: mypy --strict (whole package, no per-file mode quirks).
- **Tests**: pytest. CLI behaviour tested by invoking the parser /
  `main()` in-process (no `subprocess` round-trip for unit tests).

## When to use

- Generator writes or edits Python CLI code
- Planner needs Python-CLI-specific test-runner / module / entry-point conventions
- /finalize regenerates docs from Python CLI code

## References

- [layout.md](references/layout.md) — `src/` layout + entry-point conventions
- [argparse-subcommands.md](references/argparse-subcommands.md) — subcommand patterns + testability
- [testing.md](references/testing.md) — pytest conventions for CLI code

## Stack-specific anti-patterns

- **Calling `sys.exit()` from anywhere except `main()`** — makes the
  parser unrunnable from tests. Raise an exception or return a non-zero
  status; let `main()` translate.
- **Reading argv directly in subcommand handlers** — handlers take the
  parsed `argparse.Namespace`, never `sys.argv`. Tests build a `Namespace`
  directly.
- **Mutating global state on import** — handlers must be pure-ish; no
  module-level file reads, no env-var snapshots at import time.
