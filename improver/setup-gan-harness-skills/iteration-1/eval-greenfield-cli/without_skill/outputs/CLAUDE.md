# kvstore — instructions for Claude

`kvstore` is a small command-line inspector for local JSON config files.
It is written in Python 3.11+ with a `src/` layout, lints with Ruff,
typechecks with mypy `--strict`, and tests with pytest. The user invokes
the tool as `kvstore <subcommand>` after `pip install -e .`.

@CONTEXT.md

## Behavioral foundation

These four lines shape *how* you work on every task in this repo. They
are the behavioral layer; project-specific rules are layered on top.

1. **Don't assume. Don't hide confusion. Surface tradeoffs.**
   When a request is ambiguous (scope, format, target stack, which file),
   list the assumptions and ask before coding. Models are trained on
   completion, not on pausing — override that default.

2. **Minimum code that solves the problem. Nothing speculative.**
   Build for today's requirement, not tomorrow's. No premature
   abstraction, no "in case we later need it" config layers.

3. **Touch only what you must. Clean up only your own mess.**
   Every changed line traces to the request. If your own changes orphan
   an import or variable, clean those up; pre-existing dead code is the
   user's call.

4. **Define success criteria. Loop until verified.**
   Restate the goal as verifiable checks (a failing test, a lint command
   that must pass, the AC literal-id that must appear in a passing test).
   "Done" means verified — not "I think I'm done."

Source: <https://github.com/forrestchang/andrej-karpathy-skills> (distilled
from Karpathy's January 2026 thread on agent failure modes).

## Stack

The active stack skill is **`python-cli`** at
`.claude/skills/python-cli/`. Harness agents (planner / generator /
evaluator / finalize) load it for stack-specific idioms:

- `references/layout.md` — `src/` layout + entry-point conventions
- `references/argparse-subcommands.md` — testable subcommand pattern
- `references/testing.md` — pytest conventions
- `sensors.ini` — the lint / typecheck / test command contract the
  pre-commit gate and the evaluator both invoke

## Harness commands

This project uses the gan-harness three-stage flow:

- `/init` — turn a free-form intent dump into an immutable
  `specs/_epic/spec.md` (vision + features + sprint plan + 4 archetype
  evaluation criteria). One human checkpoint at the end.
- `/loop` — walk the sprint plan; per sprint, negotiate a contract
  (generator ⇌ evaluator), implement, evaluate. Append-only to
  `specs/_epic/contracts.jsonl`.
- `/finalize` — archive the live epic to `specs/epics/<slug>/`,
  promote proposed ADRs, merge any new domain terms into CONTEXT.md.

See the skill SKILL.md files under `.claude/skills/` for the full
mechanics.

## Quick start

```bash
# 1. Set up the virtualenv and install the package + dev tools
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e . pytest mypy ruff

# 2. Verify the toolchain
ruff check src tests
mypy --strict src
pytest

# 3. Run the CLI
kvstore --help
```

## Project conventions

- Source under `src/kvstore/`, tests under `tests/`.
- One module per domain concern; do NOT pre-create speculative modules.
- CLI: `argparse` only (no Click / Typer until justified by a sprint).
- `main(argv=None)` returns an int exit code; tests call it in-process.
- All public functions have type annotations; mypy `--strict` is the
  contract.
- Test names or docstrings include the AC literal-id they cover
  (`F01.AC03`) so the harness's AC-coverage gate can find them.
