---
name: finalize-workflow
description: Drive Stage 3 of the gan-harness v3.8 — close out a /loop epic. Archive-only path (v3.8 removed retro path along with escalate). Verifies all sprints completed, promotes proposed ADRs to accepted (with retroactive supersedes), merges new domain terms into CONTEXT.md, regenerates CODEMAP.md, archives specs/_epic/ → specs/epics/<slug>/. Single git commit. Make sure to use this skill whenever /finalize runs, when the user asks to close an epic, or when handoff from /loop has produced a fully-completed contracts.jsonl.
disable-model-invocation: false
---

# finalize-workflow

Stage 3 of v3.8. Closes out a `/loop` epic by promoting keep-alive docs
and archiving the in-flight directory.

**Single path: archive.** v3.8 removed the v1 retro path because v3.8
removed the escalate mechanism. There is no `status: deferred` in v3.8.
A loop either completes (all sprints `phase: completed` in
`contracts.jsonl`) or it doesn't (operator stopped before completion);
in the latter case, /finalize refuses to run.

**Run scripts, do not improvise.** Every keep-alive file (ADRs,
CONTEXT.md, CODEMAP.md) is produced by a script in `scripts/`. The
script either succeeds with a JSON summary on stdout, or fails with a
diagnostic on stderr — there is no "fall back to manual edits" path. If
a script fails, fix the script (or the input it choked on), then re-run.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. `specs/_epic/contracts.jsonl` exists and every sprint in
   `specs/_epic/spec.md`'s sprint plan has a `phase: completed` entry.
2. `specs/_epic/_pending/` is empty or contains only stale drafts.
3. The user understands archiving is one-way: spec.md becomes
   `specs/epics/<slug>/spec.md` and is no longer mutable.

## Pre-flight refusal cases

`finalize` refuses to run when:

- Any sprint has `phase: agreed` but not `phase: completed` (loop
  unfinished).
- Any sprint has zero entries in contracts.jsonl (loop never started).
- `specs/_epic/spec.md` doesn't exist (no epic to archive).
- `specs/epics/<slug>/` already exists (would overwrite a prior archive).

In all these cases, output a clear "/loop must complete first" message.

## Inputs (read-only until each phase mutates its narrow target)

- `specs/_epic/spec.md` (immutable; archived in Phase 4).
- `specs/_epic/contracts.jsonl` (append-only; archived in Phase 4).
- `specs/_epic/_evals/`, `_traces/`, `progress.tsv` (archived in Phase 4).
- `docs/adr/*.md` with `status: proposed` (mutated in Phase 1).
- `CONTEXT.md` (appended in Phase 2; lazy-created if missing).
- `CODEMAP.md` (regenerated in Phase 3; lazy-created if missing).

## Process — every phase is `run script, check exit, react to JSON`

Each script prints a JSON summary on stdout on success and a diagnostic
on stderr on failure. Always read both. The SKILL is responsible for
sequencing — the scripts are responsible for the actual mutation.

### Phase 0 — Pre-flight

```bash
python .claude/skills/harness-loop/scripts/epic_status.py --is-done
# exit 0 = ok; exit 1 = refuse
```

If exit 1, also run the full status view for the user:

```bash
python .claude/skills/harness-loop/scripts/epic_status.py
```

…then stop. Do NOT proceed.

Once `--is-done` returns 0, extract the slug:

```bash
SLUG=$(python .claude/skills/harness-loop/scripts/epic_status.py --json | python -c "import sys, json; print(json.load(sys.stdin)['epic_slug'])")
```

Then verify archive collision:

```bash
test ! -e "specs/epics/${SLUG}" || { echo "archive exists; refusing"; exit 1; }
```

### Phase 1 — Promote ADRs

```bash
python .claude/skills/finalize-workflow/scripts/finalize_adr.py
```

The script:
- Sets `status: accepted` + `accepted_date: <today>` for every proposed ADR.
- Retroactively backfills `superseded_by` on any predecessor listed in
  the promoted ADR's `supersedes: [...]` (refuses to overwrite an
  existing pointer; warns to stderr).
- Regenerates `docs/adr/index.md` sorted by ADR id.

Read the JSON summary; report `promoted` and `backfilled_superseded_by`
counts to the user. Stop on non-zero exit.

`--check` (dry-run) is available if you want to preview before
mutating.

### Phase 2 — Merge domain terms into CONTEXT.md

```bash
python .claude/skills/finalize-workflow/scripts/merge_domain_terms.py
```

The script:
- Parses `specs/_epic/spec.md`'s `### Domain terms` block (under
  `## Cross-cutting constraints`; format enforced by spec_lint.py L08).
- Appends each NEW term to `CONTEXT.md`'s `## Language` section. Terms
  already present (case-insensitive bold-name match) are skipped.
- Lazy-creates `CONTEXT.md` with a `# Domain Context` / `## Language`
  scaffold if missing.
- Idempotent: re-running with the same inputs produces zero new
  appends.

Read the JSON summary; report `appended` count and the names. Stop on
non-zero exit (means malformed spec.md — see L08 lint output).

### Phase 3 — Regenerate CODEMAP.md

```bash
python .claude/skills/finalize-workflow/scripts/regen_codemap.py
```

The script:
- Walks every `__init__.py` package, emits one section per package with
  the barrel docstring as the section header.
- Lists sibling modules with their docstring (Purpose column) and
  public `def`/`class` signatures (Entry points column).
- Walks `tests/test_*.py`, emits a "tests — Test suite" section with
  module-docstring or first `def test_*` name as the Covers column.
- Refuses to invent: missing barrel docstring → `_(no barrel
  docstring — add one to surface this module)_`. Missing test docstring
  → `_(no docstring; first test: ...)_` or `_(no docstring; no test_*
  function found)_`.
- Idempotent.

Read the JSON summary's `missing_barrel_docstrings` and
`missing_module_docstrings` lists; if non-empty, surface them to the
user as TODOs for the next epic's generator (per generator-handbook's
barrel-docstring requirement).

If the script exits 1 because there are no Python packages (e.g.,
non-Python stack), the active stack skill is responsible for providing
a stack-specific replacement. For now, log "skipped — no Python
packages found" and continue.

### Phase 4 — Archive

```bash
bash .claude/skills/finalize-workflow/scripts/archive_batch.sh "${SLUG}"
```

The script:
- Moves `specs/_epic/*` (including dotfiles like `_pending/`, `_evals/`,
  `_traces/`) into `specs/epics/<slug>/`.
- Uses `find -mindepth 1 -maxdepth 1 -exec mv` (not bash glob) so
  dotfiles are NOT silently dropped (the regression that hit Apollo;
  see commit history of handoff D6).
- Removes the now-empty `specs/_epic/` directory.
- Refuses to overwrite an existing `specs/epics/<slug>/`.

Stop on non-zero exit.

### Phase 5 — Summary file (optional but recommended)

```bash
python .claude/skills/finalize-workflow/scripts/summarize_batch.py \
  --epic-dir "specs/epics/${SLUG}" \
  --out "specs/epics/${SLUG}/EPIC_SUMMARY.md"
```

Generates a per-sprint outcome table from `contracts.jsonl` +
`_evals/`. Recommended for repos where epic count grows beyond a
handful; safe to skip for one-shot scaffolds.

### Phase 6 — Single commit

```bash
git add docs/adr/ CONTEXT.md CODEMAP.md "specs/epics/${SLUG}/"
git commit -m "epic: ${SLUG} finalized

- Promoted N proposed ADRs to accepted
- Added M new domain terms to CONTEXT.md
- Regenerated CODEMAP.md (K packages, L tests)
- Archived specs/_epic/ -> specs/epics/${SLUG}/
"
```

Substitute N, M, K, L from the JSON summaries you collected.

### Phase 7 — Operator summary

Output a brief summary:

```
finalize complete.
  Epic: <epic_slug>
  Sprints completed: N
  ADRs promoted: M (P backfilled superseded_by)
  CONTEXT.md terms added: K
  CODEMAP.md: X packages, Y modules, Z tests
  Missing barrel docstrings (next epic TODO): [...]
  Archive: specs/epics/<epic_slug>/

Next: start a new epic with /init.
```

## Outputs

- `docs/adr/NNNN-*.md` updated with `status: accepted` + `accepted_date`.
- `docs/adr/NNNN-*.md` of superseded predecessors updated with
  `superseded_by`.
- `docs/adr/index.md` regenerated.
- `CONTEXT.md` lazy-created or appended.
- `CODEMAP.md` regenerated.
- `specs/epics/<epic_slug>/` — final archive directory.
- `specs/epics/<epic_slug>/EPIC_SUMMARY.md` — per-sprint outcome table.
- One git commit.

## Anti-patterns

**Running /finalize on an unfinished /loop.** /finalize refuses; this is
the right behaviour. The escape valve is the operator: stop the run,
diagnose, restart /loop or abandon. There is no half-finish.

**Forcing archive when epic_status.py says not done.** Don't override.
The status reflects the contracts.jsonl state. If contracts.jsonl is
wrong, fix it; if status is wrong (read bug), fix the script.

**Editing accepted ADRs.** Accepted ADR bodies are immutable. To revise,
write a new ADR with `supersedes: [old_id]`; finalize_adr.py backfills
`superseded_by` on the predecessor.

**Hand-rolling Domain terms merge.** The `### Domain terms` format is
strict (spec_lint.py L08) precisely so merge_domain_terms.py can run
deterministically. If parsing fails, fix the spec, don't paste manually
— next epic will hit the same failure.

**Hand-writing CODEMAP.md.** The previous regen-by-hand on Apollo
produced rows that were inferred from filenames rather than real
docstrings (handoff D1/D2). Always run `regen_codemap.py` and treat
its output as authoritative. If the diff against an earlier hand-
written CODEMAP looks worse, the earlier version was guessing —
adding real docstrings to the source is the fix, not editing CODEMAP.md
to "look richer".

**Skipping CONTEXT.md merge.** Domain terms accumulate per epic. If you
skip the merge, future epics' planner won't know existing vocabulary,
and CONTEXT.md drifts from the actual domain language.

**Multi-commit.** One commit for the entire finalize. Bisects are
easier; the commit message lists everything that happened.

## Scripts (all v3.8, all required for the run)

| Script | Phase | Purpose |
|--------|-------|---------|
| `scripts/finalize_adr.py` | 1 | Promote proposed → accepted, supersedes backfill, index regen |
| `scripts/merge_domain_terms.py` | 2 | Parse `### Domain terms` from spec.md, append new entries to CONTEXT.md |
| `scripts/regen_codemap.py` | 3 | Walk `__init__.py` + module docstrings + public signatures → CODEMAP.md |
| `scripts/archive_batch.sh` | 4 | `specs/_epic/ → specs/epics/<slug>/` with dotfile-safe move |
| `scripts/summarize_batch.py` | 5 | Per-sprint outcome table from contracts.jsonl + _evals |
