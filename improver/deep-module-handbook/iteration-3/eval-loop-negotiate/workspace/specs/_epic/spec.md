# Spec — config-diff

## Vision

A small command-line tool that diffs two JSON config files and lets the
user selectively apply changes from one onto the other. Target user: a
small-team SRE who maintains a set of service configs and routinely
needs to promote a subset of changes from one environment to another
without manually editing JSON.

The shipped tool reads two files, prints a unified, colour-coded diff
keyed by JSON path, asks the user to select which diffs to apply (TUI
or numeric prompt), and writes a patched file.

## Tech stack

- Python 3.11+
- stdlib only for parsing (json); third-party for CLI ergonomics (typer)
- pytest for tests

## Archetype

cli

## Features

### F01 — Two-way config diff with selective apply

**User stories (Cohn):**

- As an SRE, I want to see every difference between two JSON config
  files keyed by JSON path so I can review the full change set at a
  glance.
- As an SRE, I want to selectively apply a subset of those differences
  from the source onto the target so I can promote vetted changes
  without dragging untested ones along.
- As an SRE, I want a verifiable record of which diffs I applied so I
  can roll back or audit later.

**Data model (optional):**

A diff entry has `{path: JSONPath, kind: "added" | "removed" | "changed",
left_value, right_value}`. A patch plan is an ordered list of selected
diff entries.

## Sprint plan

### S01 — Parser, differ, applier wired into one CLI command

**Depends-on:** none

**Smoke check:** running `config-diff a.json b.json` on two example
files prints a numbered diff, accepts user-entered indices, writes
`a.patched.json`, and the patched file matches the user's expected
selection byte-for-byte.

## Evaluation criteria

The four archetype-aware criteria for `cli`:

1. **Functionality** — the user can complete the smoke-check end-to-end
   without inspecting source code.
2. **Reliability** — the tool does not corrupt either input file on any
   path (read-only against inputs; writes only to output).
3. **Diagnostics** — when input files are malformed or unreadable, the
   tool prints a clear error referencing the bad file and exits
   non-zero.
4. **Composability** — output is grep-able and the exit code conveys
   success/failure so the tool can compose into shell pipelines.

## Cross-cutting constraints

- Deep-module discipline applies — the code base SHOULD aim for few
  large deep modules with simple interfaces, not many shallow helpers.
- No third-party JSON parsing — stdlib `json` only.
- Test isolation — pytest tests must run without filesystem outside
  pytest's tmp_path.

## Overall success criteria

`config-diff a.json b.json` on the example pair under
`examples/{a,b}.json` produces a diff matching the gold file at
`examples/expected-diff.txt`, accepts numeric selection input, and
writes `a.patched.json` byte-identical to `examples/expected-patched.json`.

## References

(No accepted ADRs yet.)
