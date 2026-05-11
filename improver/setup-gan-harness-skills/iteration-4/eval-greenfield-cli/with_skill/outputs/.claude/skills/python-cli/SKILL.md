---
name: python-cli
description: Python CLI stack reference library for gan-harness. Vendors conventions for argparse-based command-line entrypoints, project layout (src/<pkg>/__main__.py), Ruff lint, mypy --strict typecheck, and pytest unit tests. Make sure to use this skill whenever harness agents work on Python CLI code or need Python-CLI-specific idioms.
---

# Python CLI Stack Skill

Reference library of Python CLI conventions for gan-harness. Downstream harness agents (planner, generator, evaluator, /finalize) consult specific references as needed; this SKILL.md is the index.

Default toolchain (from setup-gan-harness-skills canonical-defaults table):

- CLI framework / entrypoint: argparse (stdlib, no extra dep)
- Lint: Ruff
- Typecheck: mypy --strict
- Test: pytest

## When to use

- Generator writes or edits code in a Python CLI project
- Planner needs Python-CLI-specific test-runner / module / entrypoint conventions
- /finalize regenerates docs from Python CLI code

## References

- [layout.md](references/layout.md) — project layout (src/<pkg>/__main__.py, console_scripts entrypoint)
- [argparse.md](references/argparse.md) — argparse conventions for subcommands, exit codes, and error messages
- [testing.md](references/testing.md) — pytest conventions for CLI testing (CliRunner-equivalent, capsys, subprocess smoke)

## Provenance

Inline templates (Mode 2 of setup-gan-harness-skills). No `references/upstream.md` is produced in Mode 2 — see setup-gan-harness-skills SKILL.md Phase 4b for the rationale.

## Stack-specific anti-patterns

- **Using `print()` for CLI errors.** Write to `sys.stderr` and exit with a non-zero status; the harness gate's smoke tests assert exit codes.
- **Mutating `sys.argv` from inside tests.** Use `argparse.ArgumentParser.parse_args(argv)` with an explicit `argv` list so tests stay pure.
- **One-mega-module CLI.** Split into `cli.py` (argparse wiring), `commands/<verb>.py` (one verb per file), and pure-function core in `<pkg>/core/`. Keep `__main__.py` thin.
