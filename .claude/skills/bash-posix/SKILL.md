---
name: bash-posix
description: POSIX-compatible bash stack reference for gan-harness. Use whenever harness agents write or evaluate bash scripts targeting `/bin/sh` or `/bin/bash` portability (no zsh-only / no GNU-only extensions assumed). Provides the harness gate command contract (shellcheck / bash -n / inline test runner) plus Google's shell style guide vendored verbatim.
---

# bash-posix Stack Skill

Reference library for projects where the runtime is `/bin/bash` (or POSIX
`/bin/sh`) — typical for build scripts, install helpers, one-shot CLI
utilities, and CI glue. Downstream harness agents (planner / generator /
evaluator / finalize) consult this skill when the spec.md `## Tech stack`
lists `bash-posix`.

## When to use

- Generator writes or edits a `.sh` script that must run portably under
  `bash` (and ideally `dash`/`sh`).
- Planner is drafting a sprint plan for shell tooling and needs to know
  which test runner + style enforcement applies.
- Evaluator re-runs lint / syntax-check / test commands during VERIFY
  mode using the `## Commands` table below.

Dev tooling (`shellcheck`) is third-party; the runtime stays bash. If the
project genuinely cannot tolerate any dependency beyond bash itself,
note it in spec.md `## Cross-cutting constraints` — `lint.check` will
then run a degraded mode.

## Commands

Harness gate contract. Pre-commit hook reads this via
`.claude/scripts/parse_stack_commands.py`. Required keys: `lint.fix`,
`lint.check`, `typecheck`, `test.unit`. Optional: `test.smoke`. `{scope}`
is substituted at invocation time.

| Key | Command |
|---|---|
| lint.fix | `shellcheck --shell=bash --format=diff {scope}` |
| lint.check | `shellcheck --shell=bash --severity=warning {scope}` |
| typecheck | `bash -n {scope}` |
| test.unit | `bash {scope}` |
| test.smoke | `bash -x {scope}` |

Rationale: bash has no static type system; `bash -n` is the closest
equivalent (syntax-only parse, no execution). Test runner is direct
invocation of test scripts (typically `tests/test_*.sh` that runs a
series of assertions and `exit 1` on failure) — bats / shunit2 are
optional layers a sprint can add when complexity warrants. Lint is
shellcheck at warning severity (not info; info-level findings are
mostly style noise and would drown the gate).

## References

- [google-shell-style-guide.md](references/google-shell-style-guide.md)
  — Google's shell style guide, vendored verbatim from
  `google/styleguide` `gh-pages` for naming, quoting,
  pipefail-discipline, and array conventions.
- [upstream.md](references/upstream.md) — provenance log.

## Stack-specific anti-patterns

- **Forgetting `set -euo pipefail`** — bash defaults are dangerous
  (continue on error, undefined-var expands to empty, pipeline status
  reflects only last command). For any non-trivial script, the first
  non-shebang/comment line should be `set -euo pipefail`.
- **`[ ... ]` instead of `[[ ... ]]`** when using bash-specific features
  — fine if targeting POSIX `sh`, but inconsistent within the same
  script. Pick one and document.
- **Unquoted variable expansions** — `rm $file` breaks on filenames
  with spaces; always `rm "$file"`. Shellcheck SC2086 catches this.
- **Parsing `ls`** — `for f in $(ls *.txt)` breaks on whitespace and
  newlines in filenames. Use globbing (`for f in *.txt`) or `find` with
  `-print0`.
- **Using `==` instead of `=` for string comparison in POSIX `sh`** —
  `[ "$a" = "$b" ]` works everywhere; `[ "$a" == "$b" ]` is bashism.
- **Subshell variable scope confusion** — `cmd | while read line` runs
  the loop in a subshell; variables set inside don't survive. Use
  process substitution or here-strings when state must escape.
