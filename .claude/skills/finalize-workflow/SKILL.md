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

In all these cases, output a clear "/loop must complete first" message.

## Inputs

- `specs/_epic/spec.md` (immutable, will be archived).
- `specs/_epic/contracts.jsonl` (append-only, will be archived).
- `specs/_epic/_evals/`, `_traces/`, `progress.tsv` (will be archived).
- `docs/adr/*.md` with `status: proposed` (will be considered for
  promotion).
- `CONTEXT.md` (will be appended to with new domain terms).
- `CODEMAP.md` (will be regenerated from barrel docstrings).

## Process

### Phase 0 — Pre-flight

1. Run `python .claude/skills/harness-loop/scripts/epic_status.py
   --is-done`. Exit 0 = epic done; non-zero = refuse with message.
2. Extract `epic_slug` from `specs/_epic/spec.md`'s H1 line.
3. Verify `specs/epics/<epic_slug>/` does not yet exist (archive
   collision).

### Phase 1 — Promote ADRs

For each `docs/adr/NNNN-*.md` with `status: proposed`:
- Change `status: proposed` → `status: accepted`. Add `accepted_date:
  <today>`.
- If the ADR has `supersedes: [old_id]`, retroactively backfill the
  superseded ADR's frontmatter with `superseded_by: <new_id>`.
- Regenerate `docs/adr/index.md` from the now-accepted set.

(The actual ADR file edits use the `adr-lifecycle` skill's helpers if
present; otherwise direct frontmatter edits.)

### Phase 2 — Merge domain terms into CONTEXT.md

Run `merge_domain_terms.py` (TODO Phase D, lives in finalize-workflow/
scripts/):
- Parse `specs/_epic/spec.md` for domain terms (proper nouns in
  `## Features`, `## Cross-cutting constraints`).
- Compare against existing `CONTEXT.md` `## Language` entries.
- For each NEW term, append a stub entry to CONTEXT.md (lazy-create
  CONTEXT.md if missing).
- Idempotent: re-running on the same epic does nothing.

### Phase 3 — Regenerate CODEMAP.md

Run `regen_codemap.py` (TODO Phase D, lives in finalize-workflow/
scripts/):
- Walk barrel files (`__init__.py`, `index.ts`, `mod.rs`, etc. per
  active stack skill) and extract docstrings.
- Render to `CODEMAP.md` (lazy-create if missing). Format: one section
  per top-level module, with sub-modules nested.

### Phase 4 — Archive

Run `archive_batch.sh` (TODO Phase D, lives in finalize-workflow/
scripts/) or equivalent:
- `mkdir -p specs/epics/<epic_slug>/`
- `mv specs/_epic/* specs/epics/<epic_slug>/`
- `rmdir specs/_epic/`

### Phase 5 — Single commit

```bash
git add docs/adr/ CONTEXT.md CODEMAP.md specs/epics/<epic_slug>/
git commit -m "epic: <epic_slug> finalized

- Promoted N proposed ADRs to accepted
- Added M new domain terms to CONTEXT.md
- Regenerated CODEMAP.md from K barrel files
- Archived specs/_epic/ -> specs/epics/<epic_slug>/
"
```

### Phase 6 — Summary

Output a brief summary:
```
finalize complete.
  Epic: <epic_slug>
  Sprints completed: N
  ADRs promoted: M
  CONTEXT.md terms added: K
  Archive: specs/epics/<epic_slug>/

Next: start a new epic with /init.
```

## Outputs

- `docs/adr/NNNN-*.md` updated with `status: accepted`.
- `docs/adr/index.md` regenerated.
- `CONTEXT.md` lazy-created or appended.
- `CODEMAP.md` regenerated.
- `specs/epics/<epic_slug>/` — final archive directory.
- One git commit.

## Anti-patterns

**Running /finalize on an unfinished /loop.** /finalize refuses; this is
the right behaviour. The escape valve is the operator: stop the run,
diagnose, restart /loop or abandon. There is no half-finish.

**Forcing archive when epic_status.py says not done.** Don't override.
The status reflects the contracts.jsonl state. If contracts.jsonl is
wrong, fix it; if status is wrong (read bug), fix the script.

**Editing accepted ADRs.** Accepted ADR bodies are immutable. To revise,
write a new ADR with `supersedes: [old_id]`; /finalize backfills
`superseded_by` on the predecessor.

**Skipping CONTEXT.md merge.** Domain terms accumulate per epic. If you
skip the merge, future epics' planner won't know existing vocabulary,
and CONTEXT.md drifts from the actual domain language.

**Multi-commit.** One commit for the entire finalize. Bisects are
easier; the commit message lists everything that happened.

## Scripts

(Phase D will fill these in. Currently placeholders.)

- `scripts/finalize_adr.py` — promote proposed → accepted, supersedes
  backfill, index regen.
- `scripts/merge_domain_terms.py` — extract terms, append to CONTEXT.md.
- `scripts/regen_codemap.py` — barrel docstring → CODEMAP.md.
- `scripts/archive_batch.sh` — mv specs/_epic/ → specs/epics/<slug>/.
- `scripts/summarize_batch.py` — final summary.
