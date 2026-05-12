---
name: python-stdlib
description: Python standard library stack reference for gan-harness. Use whenever harness agents work on Python code that targets stdlib-only runtime (no third-party packages). Provides the harness gate command contract (ruff / mypy / unittest) plus PEP 8 style guidance.
---

# Python stdlib Stack Skill

Reference library for projects where the runtime dependency surface is the
Python standard library only — common for CLIs, single-file scripts,
data-processing one-shots, and library cores. Downstream harness agents
(planner / generator / evaluator / finalize) consult this skill when the
spec.md `## Tech stack` lists `python-stdlib`.

## When to use

- Generator writes or edits Python that targets `python3 -m unittest` and
  the standard library (no pandas, no requests, no click, no FastAPI).
- Planner needs to know which test runner + style guide apply when
  drafting a sprint plan for stdlib-scoped work.
- Evaluator re-runs lint / typecheck / test commands during VERIFY mode
  using the `## Commands` table below.

Dev tooling (`ruff`, `mypy`) is third-party — that is intentional. The
runtime stays stdlib-only; static-analysis tooling on the developer side
is a separate concern and uses the modern Python ecosystem default.

## Commands

Harness gate contract. Pre-commit hook reads this via
`.claude/scripts/parse_stack_commands.py`. Required keys: `lint.fix`,
`lint.check`, `typecheck`, `test.unit`. Optional: `test.smoke`. `{scope}`
is substituted at invocation time (typically `git diff --name-only` for
pre-commit; `verification_plan` targets for evaluator).

| Key | Command |
|---|---|
| lint.fix | `ruff check --fix --silent {scope}` |
| lint.check | `ruff check {scope}` |
| typecheck | `mypy --strict {scope}` |
| test.unit | `python -m unittest discover -s {scope}` |
| test.smoke | `python -m unittest -v {scope}` |

Rationale for `unittest` (not `pytest`) at `test.unit`: this stack is
named `python-stdlib`. The test runner is part of "what runs at runtime"
when CI executes the test command. `unittest` is stdlib; `pytest` is
not. If a project explicitly wants pytest, use the separate
`python-pytest` stack skill (not this one).

## References

- [pep-0008.rst](references/pep-0008.rst) — PEP 8: Style Guide for Python
  Code. Vendored verbatim from python/peps `main` for naming, indentation,
  line-length, and import-ordering conventions.
- [upstream.md](references/upstream.md) — provenance log (source URL,
  revision, license, fetched_at) for every file in `references/`.

## Stack-specific anti-patterns

- **Importing third-party at runtime** — `import requests`, `import
  pandas`, `from fastapi import ...` violates the stack. If a problem
  genuinely needs them, this is not the right stack — escalate to
  planner for a different stack skill (e.g., `python-fastapi`).
- **Printing diagnostics to stdout** — diagnostics go to `sys.stderr`;
  stdout is reserved for the program's actual output so pipes work.
- **Bare `except Exception`** — catch the specific exception type the
  stdlib raises (`FileNotFoundError`, `csv.Error`, `KeyError`, ...). The
  evaluator's matrix sensor `secret:scan` plus PEP 8's "Programming
  Recommendations" both flag bare catches.
- **Skipping `if __name__ == "__main__":` for scripts** — a script-as-a
  module must be importable in tests without side effects, so the entry
  point belongs inside the `__main__` guard.
