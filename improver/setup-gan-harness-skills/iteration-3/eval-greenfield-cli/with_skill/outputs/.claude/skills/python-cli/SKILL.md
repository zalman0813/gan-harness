---
name: python-cli
description: Python CLI stack reference library for gan-harness. Vendors conventions for argparse-based CLI apps (stdlib, no extra runtime dep), Ruff linting, mypy --strict typechecking, and pytest. Make sure to use this skill whenever harness agents work on Python CLI code or need Python CLI idioms.
---

# Python CLI Stack Skill

Reference library of Python CLI conventions, vendored inline from the
gan-harness `python-cli` canonical defaults (argparse + Ruff + mypy
--strict + pytest). Downstream harness agents (planner, generator,
evaluator, /finalize) consult specific references as needed; this
SKILL.md is the index.

## When to use

- Generator writes or edits code in a Python CLI app
- Planner needs Python CLI-specific test-runner / module / packaging
  conventions
- /finalize regenerates docs from Python CLI code

## Stack profile

- **CLI framework**: `argparse` (Python stdlib — no extra runtime dep).
- **Entrypoint pattern**: `python -m <pkg>` via `__main__.py`, with a
  thin `main(argv: list[str] | None = None) -> int` function for
  testability.
- **Lint**: Ruff (`ruff check`). Auto-fix supported.
- **Typecheck**: `mypy --strict`. Strict mode is the default; loosen
  only with cause.
- **Test**: `pytest`. Property-based tests via Hypothesis are decorated
  unit tests; they run through the same `[test] unit` command.

## References

- [layout.md](references/layout.md) — package layout, entrypoint, argparse idiom.
- [testing.md](references/testing.md) — pytest conventions and PBT (Hypothesis) notes.

## Provenance

References in this skill were emitted inline by the
`setup-gan-harness-skills` Mode 2 (no web fetch). They reflect the
canonical defaults from that skill's Phase 4b table.

## Stack-specific anti-patterns

- Reaching for `click` or `typer` when argparse already covers the
  surface area — adds a runtime dep for no observable user benefit on a
  small CLI. Pick a CLI lib only when argparse's verbosity becomes the
  bottleneck.
- Mixing module entrypoint (`python -m pkg`) with a `console_scripts`
  entry without making both call the same `main()`. Pick one and have
  the other be a thin wrapper.
- Using `print()` for errors. Errors go to `sys.stderr`; the process
  exits non-zero. The CLI's exit code IS part of its contract.
