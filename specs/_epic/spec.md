# Spec — todo-cli

## Vision
A tiny stdlib-only Python CLI for jotting personal tasks from the terminal. Used by a single developer who wants `todo add` and `todo list` against a JSON file at `~/.todo.json` — no daemon, no sync, no GUI. Built greenfield as the smallest possible vertical CLI on top of `argparse + json + pathlib`.

## Tech stack
- Backend: python-stdlib
- Test runner: python-stdlib

## Archetype
cli

## Features
### F01 — Add task
**Sprint**: S01
**User stories**: As a developer, I want to:
- Run `todo add <description>` and have a new task entry persisted to `~/.todo.json`
- See an auto-incremented integer id assigned to my new task
- Have each task carry a timestamp of when it was recorded

### F02 — List tasks
**Sprint**: S02
**User stories**: As a developer, I want to:
- Run `todo list` and see every task previously added, one per line
- See each line formatted as `[id] description (timestamp)` so I can scan ids quickly
- Get an empty (no-error) output when `~/.todo.json` has no entries yet

## Sprint plan
### S01 — Add task (pure-cli)
- Delivers: F01
- Depends on: (none)
- Smoke check: User runs `todo add buy milk` and sees `~/.todo.json` gain an entry with id 1, the description, and a timestamp.

### S02 — List tasks (pure-cli)
- Delivers: F02
- Depends on: S01
- Smoke check: User runs `todo add buy milk`, then `todo list`, and sees a line `[1] buy milk (<timestamp>)` printed to stdout.

## Evaluation criteria
1. **UX quality** — `--help` is a single screen; errors name the offending argument; subcommand flag style is consistent across `add` and `list`
2. **Robustness** — handles a missing or empty `~/.todo.json` cleanly; non-zero exit code on bad input; pipeline-safe stdout
3. **Craft** — subcommand parser organised cleanly; stdlib-only imports; unit tests cover happy path and edge cases
4. **Functionality** — `todo add` persists a well-formed JSON entry; `todo list` reads back every entry in insertion order, end-to-end

## Cross-cutting constraints
- Non-goals: GUI, network sync, multi-user, task edit / delete, due dates, priorities, tags, search
- Storage file path is fixed at `~/.todo.json` (no `--file` flag this epic)
- Timestamps are recorded in UTC ISO-8601 format
- Stdout is reserved for command output; diagnostics go to stderr
- Zero runtime dependencies outside the Python standard library

## Overall success criteria
1. A developer can install the CLI, run `todo add buy milk`, then `todo list`, and see `[1] buy milk (<timestamp>)` printed within one minute of install.
2. After three successive `todo add` calls, `todo list` prints exactly three lines with ids 1, 2, 3 in insertion order.
3. Running `todo list` against a fresh machine where `~/.todo.json` does not yet exist completes with exit code 0 and no traceback.

## References
- CONTEXT.md (existing domain language)
- .claude/skills/python-stdlib/SKILL.md (stack contract)
