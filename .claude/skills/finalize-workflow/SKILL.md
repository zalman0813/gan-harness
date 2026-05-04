---
name: finalize-workflow
description: Drive Stage 4 of the gan-harness — close out a /execution-loop batch. Branches on feature.status. Archive path (all passed) promotes proposed ADRs, merges Domain terms into CONTEXT.md, regenerates CODEMAP.md, and archives specs/_batch/ → specs/completed/{slug}/. Retro path (any deferred / blocked-by-ancestor) walks each deferred feature's open_questions via AskUserQuestion, hands fixes to the planner agent, and resets affected features to status:todo so the user can re-run /execution-loop. Make sure to use this skill whenever /finalize runs, when the user asks to close a batch, or when handoff from /execution-loop needs ADR/glossary/codemap promotion.
---

# Finalize Workflow

Stage 4 of the harness. One command (`/finalize`), one workflow skill, one
single human checkpoint, two internal branches:

- **Archive path** — every feature is `status: passed`. Promote proposed
  ADRs, merge Domain terms into `CONTEXT.md`, regen `CODEMAP.md`, archive
  the batch to `specs/completed/{slug}/`, single commit.
- **Retro path** — any feature is `status: deferred` or
  `status: blocked-by-ancestor`. Walk each deferred feature's
  `open_questions` via `AskUserQuestion`, route the answers to the planner
  agent, reset affected features to `status: todo`. The batch stays alive;
  user manually re-runs `/execution-loop` after retro completes.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. <e.g., "specs/_batch/feature-list.json was produced by /plan and walked through /execution-loop">
2. <e.g., "the active stack skill is unchanged since /plan ran">
3. ...
→ Correct me now or I'll proceed with these.

If `specs/_batch/feature-list.json` is missing or any feature.status is
non-terminal (`todo`), ABORT. /execution-loop must run first.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "User didn't choose, sane default is fine" | For load-bearing decisions (stack, layout), ask. For purely cosmetic, default may be fine but say which you picked. |
| "This file might be needed later, I'll create a stub now" | Lazy creation. No empty stubs. Producer creates on first real content. |
| "User's edits to the project's master docs (`README.md`, `CONTEXT.md`) look wrong" | Not your call to revise. They own per-project decisions once setup hands off. |
| "Some features deferred — I'll archive anyway, retro can wait" | No. Archive only when every feature is `passed`. Otherwise the alive `specs/_batch/` is the truth and retro is the next move. |
| "Retro is small, skip the planner agent and edit feature-list.json directly" | No. Planner owns feature-list.json invariants (schema + trio). Direct edits skip lint and risk drift; reuse the planner agent. |
| "Single commit feels too coarse — split into multiple" | No. /finalize lands as one `chore(finalize): close batch <slug>` commit so the archival is atomic and reviewable. |

## When to use

- All features in `specs/_batch/feature-list.json` are at terminal status
  (`passed` / `deferred` / `blocked-by-ancestor`)
- Either: archive a clean batch, OR: walk the retro fixes for a batch
  with deferred features
- A previous /finalize aborted partway and needs resuming (the active
  `specs/_batch/` indicates work to finish)

## When NOT to use

- Any feature still `todo` — finish /execution-loop first
- `specs/_batch/feature-list.json` does not exist — /plan must run first
- An archive already exists at `specs/completed/{slug}/` — /finalize is
  idempotent-by-refusal: it will not overwrite a prior archive

## Inputs

- `specs/_batch/feature-list.json` — the batch contract (planner-locked)
- `specs/_batch/prd.md` — Domain terms source for archive path
- `specs/_batch/_evals/F{NN}-R{N}.json` — evaluator verdicts (verdict +
  eval_feedback) consumed by `summarize_batch.py` and the retro walk
- `specs/_batch/_traces/F{NN}-{gen|eval}-trace-R{N}.md` — per-round agent
  traces (preserved by archive; not parsed)
- `specs/_batch/progress.tsv` — execution log (preserved by archive; not parsed)
- `docs/adr/*.md` — proposed ADRs awaiting promotion
- `CONTEXT.md` (lazy — created if missing)
- `CODEMAP.md` (lazy — created on first regen)

## Outputs

### Archive path
- `docs/adr/NNNN-*.md` — `status: proposed → accepted` (in place); `index.md` regenerated
- `CONTEXT.md` — new Domain terms appended under `## Language`
- `CODEMAP.md` — regenerated from current barrel docstrings
- `specs/completed/{slug}/` — full archive of the batch (everything that
  was under `specs/_batch/` plus a generated `BATCH_SUMMARY.md`)
- `specs/_batch/` — empty (just `.gitkeep`)
- One git commit: `chore(finalize): close batch <slug>`

### Retro path
- `specs/_batch/feature-list.json` — affected features' `status` reset
  from `deferred`/`blocked-by-ancestor` → `todo`; `open_questions[].resolution`
  updated with user-approved answers
- Possibly new/updated `docs/adr/NNNN-*.md` if the retro produces an
  architectural answer (planner emits as `status: proposed`; promotion
  waits for the next /finalize archive run)
- No commit by /finalize (the next /execution-loop pass is the real
  follow-on); user manually re-runs `/execution-loop`

## Phases

### Phase 0 — Pre-flight

```
python3 .claude/skills/finalize-workflow/scripts/preflight.py
```

Outputs `SLUG`, `BASE_COMMIT`, `BRANCH=archive|retro`, plus per-status
feature id lists. Any non-zero exit → STOP, surface diagnostic.

### Phase 1 — Branch on `BRANCH`

If `BRANCH=retro` → § Retro path below.
If `BRANCH=archive` → § Archive path below.

---

## Retro path

The batch stays alive. Goal: turn each `deferred` feature's open
questions into approved resolutions, hand the corrections to planner,
return the affected features to `status: todo` so /execution-loop can
re-run them.

### R1 — Walk each deferred feature

For every feature with `status: deferred`:

1. Read its `spec.open_questions[]` from feature-list.json. Read the
   final-round eval JSON `specs/_batch/_evals/{fid}-R{N}.json` (max
   round) — the `verdict_reason` / `eval_feedback.overall` fields are
   the evaluator's signal for *why* it deferred, which you surface to
   the user alongside each question.
2. For each open_question, ask the user via `AskUserQuestion` (one
   question per call):
   - **Approve** — keep planner's existing `resolution` text
   - **Edit** — user provides corrected resolution text; record it
   - **Escalate** — user cannot answer; abort the entire retro back to
     /prd for re-scope of this batch (no point grinding when scope is
     wrong)
3. `blocked-by-ancestor` features have no own questions — they cascade
   automatically when their ancestor returns to `todo`. Do not walk
   them individually.

The walk is conversation, not a gate, so it does not violate the
"single human checkpoint per stage" invariant — same logic as /plan
Phase 2.

### R2 — Hand fixes to the planner agent

Spawn a single `planner` subagent with a scoped task. Prompt template:

```
You are amending an existing batch's feature-list.json after retro
review. Do NOT redesign features — you are only updating
open_question resolutions and resetting feature.status.

For each (feature_id, question_id, new_resolution) below, update
specs/_batch/feature-list.json:
  1. Set spec.open_questions[<question_id>].resolution = <new_resolution>
  2. Set feature.status = "todo" for the affected feature
  3. Cascade: every feature whose status is "blocked-by-ancestor"
     AND whose depends_on chain includes the affected feature →
     also set status: "todo"

Updates to apply:
  <list each (fid, qid, new_resolution)>

If a resolution requires a new architectural decision (i.e. the answer
introduces an interface, boundary, or trade-off that passes the
three-test gate), write a new docs/adr/NNNN-*.md with status:proposed
and add its path to the affected feature's decision_refs[]. The next
/finalize archive run promotes it.

After all updates: run the three-script trio
  scripts/plan_validator.py
  scripts/lift_capabilities.py
  scripts/plan_lint.py
on specs/_batch/feature-list.json. If any FAIL, fix and retry; if 3
rounds elapse with FAILs, STOP and report.
```

Wait for the planner to return.

### R3 — Report and stop

Print a retro report:

```
═══════════════════════════════════════════════════════════════
/finalize retro complete — <slug>
═══════════════════════════════════════════════════════════════

Resolved questions:    <N>
Reset to todo:         <list of feature ids>
New proposed ADRs:     <count, paths>
Trio:                  <PASS|FAIL>

Next: /execution-loop
═══════════════════════════════════════════════════════════════
```

Do NOT commit. Do NOT proceed to archive. The batch is alive again.

---

## Archive path

Every feature is `status: passed`. Goal: promote, merge, regen, archive,
commit — single atomic transaction.

### A0 — Single human checkpoint

One `AskUserQuestion` BEFORE any mutation, with a preview of what's
about to change:

```
Ready to close batch "<slug>". Will perform:

  - Promote N proposed ADRs (docs/adr/*) → accepted; regen index.md
  - Merge K Domain terms from prd.md → CONTEXT.md (lazy-create if missing)
  - Regenerate CODEMAP.md from current barrel docstrings
  - Move specs/_batch/* → specs/completed/<slug>/ + BATCH_SUMMARY.md
  - Single commit: chore(finalize): close batch <slug>

Approve / Edit slug / Abort
```

- **Approve** → continue with steps A1–A5
- **Edit slug** → user provides corrected slug; update
  `feature-list.json.batch_slug` first, re-run preflight, then loop back
  to this checkpoint with the new slug
- **Abort** → STOP, no mutations

### A1 — Promote ADRs

```
python3 .claude/skills/plan-workflow/scripts/finalize_adr.py \
    --decisions-dir docs/adr \
    --batch <slug>
```

The script handles three passes:
1. Promote `status: proposed` → `accepted` (only ADRs whose
   frontmatter `batch:` matches `<slug>`)
2. Retroactive supersedes backfill (predecessors get `superseded_by`)
3. Regen `docs/adr/index.md`

Lazy: if `docs/adr/` is missing entirely, the script reports zero ADRs
and writes an empty index — that's fine (first batch with no ADRs).

### A2 — Merge Domain terms

```
python3 .claude/skills/finalize-workflow/scripts/merge_domain_terms.py \
    --prd specs/_batch/prd.md \
    --context CONTEXT.md
```

The script extracts `### Domain terms (draft)` blocks from each R
section of `prd.md`, dedupes across R, skips terms already present in
`CONTEXT.md` (case-insensitive bold-name match), appends new terms
under `## Language`. Lazy-creates `CONTEXT.md` with H1 + `## Language`
stub if missing.

Stdout is JSON: `{"appended": [...], "skipped_existing": [...],
"skipped_duplicate_in_batch": [...]}`. Capture for the final report.

### A3 — Regenerate CODEMAP.md

```
python3 .claude/skills/plan-workflow/scripts/regen_codemap.py \
    --src-root . \
    --out CODEMAP.md
```

Walks barrel files (`index.ts`/`__init__.py`/`mod.rs`/`doc.go`/dart
`library;`), extracts module-level docstrings, writes a flat
`CODEMAP.md`. Lazy-creates if missing. Deterministic, no LLM.

### A4 — Generate summary + archive

```
python3 .claude/skills/finalize-workflow/scripts/summarize_batch.py \
    --out specs/_batch/BATCH_SUMMARY.md
bash   .claude/skills/finalize-workflow/scripts/archive_batch.sh \
    <slug>
```

`summarize_batch.py` reads feature-list.json + `_evals/F*-R*.json` and
writes `BATCH_SUMMARY.md` into `specs/_batch/` so the archive script
sweeps it along with everything else.

`archive_batch.sh` moves `specs/_batch/*` (everything except `.gitkeep`)
into `specs/completed/<slug>/` atomically; refuses to overwrite an
existing archive.

### A5 — Commit

```
git add -A
git commit -m "chore(finalize): close batch <slug>

- ADRs promoted: <count>
- Domain terms appended: <count>
- CODEMAP entries: <count>
- Archived to specs/completed/<slug>/"
```

Refuse to land an empty commit (would mean nothing changed — that's a
bug, not a clean finalize).

### A6 — Report

```
═══════════════════════════════════════════════════════════════
/finalize archive complete — <slug>
═══════════════════════════════════════════════════════════════

ADRs promoted:    <N>
Domain terms:     <K> appended (<S> already present, <D> dupes in batch)
Codemap entries:  <M>
Archive:          specs/completed/<slug>/
Commit:           <short sha>

Next: /prd  (for the next batch)
═══════════════════════════════════════════════════════════════
```

---

## Anti-patterns

- **Skipping the BRANCH check.** Archive on a batch with deferred
  features destroys the retro signal. Always trust `preflight.py`'s
  BRANCH output.
- **Multiple commits in archive path.** /finalize lands one commit; if
  you find yourself splitting, you're scope-creeping the ceremony.
- **Editing feature-list.json by hand in retro.** The planner agent owns
  its invariants (schema + trio). Hand-edits skip validation.
- **Pre-creating `CONTEXT.md` / `CODEMAP.md` / `docs/adr/index.md` stubs
  before they have content.** Lazy creation per locked decision; an
  empty stub is a lie.
- **Re-running /finalize against an archived batch.** The active
  `specs/_batch/` will be empty, preflight aborts; do not "fix" preflight
  to swallow this case.
- **Recreating `gen-dreamer` / `eval-dreamer` / `doc-garden` /
  `tech-debt-tracker.md`.** Explicitly removed; the zero-debt
  invariant means every concern resolves upstream — at /plan or
  /finalize retro — not into a debt log. (Future post-batch
  proposal agents land via T17 design, not by resurrecting the old
  shape.)
- **Committing in the retro path.** Retro is mid-batch. The next
  /execution-loop pass is the real continuation; no commit until
  archive.

## Done when

### Archive path
- [ ] Preflight passed and `BRANCH=archive`
- [ ] User approved at A0 checkpoint
- [ ] All proposed ADRs for this batch promoted; index.md regenerated
- [ ] New Domain terms merged into `CONTEXT.md` (or none to merge)
- [ ] `CODEMAP.md` regenerated
- [ ] `specs/_batch/` empty; `specs/completed/<slug>/` populated
- [ ] Single `chore(finalize):` commit landed
- [ ] Report printed; `/prd` suggested

### Retro path
- [ ] Preflight passed and `BRANCH=retro`
- [ ] Every `deferred` feature's `open_questions` walked
- [ ] Planner agent applied the user-approved resolutions and ran the
      three-script trio (PASS)
- [ ] Affected features reset to `status: todo`; cascade applied
- [ ] No commit; report printed; `/execution-loop` suggested
