---
name: batch-gc
description: "/finalize ceremony — drain gen-dreamer + eval-dreamer proposals via AskUserQuestion, promote glossary/codemap, archive batch to specs/completed/{slug}/, spawn doc-garden agent. Use when user runs /finalize after all features DONE/BLOCKED and both DREAM-*.md files exist."
user-invocable: false
---

# Finalize Skill (/finalize ceremony)

## Overview

Invoked by `/finalize`. Runs AFTER:
1. All features in `docs/feature-list.json` reached terminal state
   (DONE or BLOCKED) via `/execution-loop`.
2. `gen-dreamer` + `eval-dreamer` ran at the tail of the execution
   loop and wrote `docs/progress/DREAM-gen.md` +
   `docs/progress/DREAM-eval.md` as PROPOSAL LISTS (no direct writes
   to capsules/SKILL.md/anti-patterns).

Finalize has four phases plus a commit step, executed in order. No
skipping. Each phase writes small, reviewable diffs; failures abort
the whole ceremony so partial state never lands in a commit.

```
/execution-loop completes (all DONE/BLOCKED)
  ↓
gen-dreamer + eval-dreamer run (post-loop tail)
  → docs/progress/DREAM-gen.md (P-NN proposals)
  → docs/progress/DREAM-eval.md (P-NN proposals)
  ↓
/finalize
  ├─ Phase 1: Dreamer Review — AskUserQuestion per proposal; apply approved
  ├─ Phase 2: Promote — glossary merge, codemap sync, barrel backlog
  ├─ Phase 3: Archive — specs/_batch/ → specs/completed/{slug}/; summarize progress; delete raw
  ├─ Phase 4: Scan — spawn doc-garden agent
  └─ Phase 5: Commit — single chore(finalize) commit
  ↓
/prd (for next batch)
```

## When to Use

- All features terminal (DONE or BLOCKED)
- Both `docs/progress/DREAM-gen.md` + `docs/progress/DREAM-eval.md` exist
- `specs/_batch/plan.md` present (slug source)

## When NOT to Use

- Features still in TODO or WIP — finish the batch first
- Either DREAM file missing — re-run `/execution-loop` so the dreamers
  emit their proposals
- Mid-batch — /finalize is post-batch only

---

## Phase 1: Dreamer Review

Goal: Drain the proposal queue from `DREAM-gen.md` + `DREAM-eval.md`
via `AskUserQuestion`; apply approved changes to the skill system.

### 1a. Pre-flight

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/preflight.py docs/feature-list.json
```

Validates:
- `docs/feature-list.json` exists + all features terminal
- `specs/_batch/plan.md` exists (for slug parsing)
- `docs/progress/DREAM-gen.md` AND `docs/progress/DREAM-eval.md` exist

If any check fails → STOP with diagnostic. Exit 1.

### 1b. Parse proposals

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_dream.py docs/progress/DREAM-gen.md
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_dream.py docs/progress/DREAM-eval.md
```

Output (JSON list per file): for each P-NN proposal — `id`, `category`,
`target`, `reason`, `payload`. Aggregate both into one review queue,
ordered: gen first, then eval. Inside each file, preserve the order
the dreamer emitted.

### 1c. Walk the queue via AskUserQuestion

For each proposal:

1. Show header + reason + diff/draft to the user (one proposal per
   question). The question label is the proposal id + category,
   e.g., `"DREAM-gen P-03 [update-heuristic] async-value-guard-rethrow-gap"`.
2. Ask the user one question with 3 options: `Approve`, `Reject`,
   `Edit`. The preview field renders the full payload so the user can
   compare side-by-side.
3. Handle the response:
   - **Approve** → apply the change using the dispatch table below.
   - **Reject** → no file change; record `reason: <rejected-reason>`
     in the applied audit log.
   - **Edit** → re-prompt via `AskUserQuestion` (free text) for the
     corrected payload; validate payload; then apply.

### 1d. Proposal dispatch table

| Category | Applied action |
|---|---|
| P-NN [create-recipe] | Write a new capsule file from the draft. **Liveness gate**: if `recipe_liveness.py --gate --threshold 30` exits 1, REFUSE this proposal (promotion-only mode) regardless of user approval — record `skipped: gate-tripped`. |
| P-NN [append-fm] | Append the `FM-NN:` line under the target capsule's `## Failure Modes` section. Bump the capsule's `version:` frontmatter by 1; record prior version in `parents:`. |
| P-NN [update-heuristic] | Replace the matching line in the target capsule's `## Heuristics` section. Bump version + parents. |
| P-NN [update-worked-example] | Replace the target capsule's `## Worked Example` block. Bump version + parents. |
| P-NN [skill-md-quick-ref] | Insert the row into the target SKILL.md's Quick Reference table at the natural L1 → L5 order position. |
| P-NN [anti-pattern] | Append the NEVER/ALWAYS bullet under the specified H2 in `learned-anti-patterns/<domain>.md`. If the H2 doesn't exist, create it under a sensible place. Bump the Quick Reference occurrence counts at the top of the domain file. |
| P-NN [prune] | `git rm` the capsule file; update the corresponding `recipes/README.md` (remove row; add a "Pruned" note if appropriate). Refuse if the capsule is referenced from any active config path (run a reverse-grep before removing). |

### 1e. Append applied audit log

At the end of Phase 1, append to each DREAM file in place:

```markdown
## Applied (by /finalize on {YYYY-MM-DD})

- P-01: approved, applied
- P-02: approved, applied
- P-03: rejected (user: "overlap with existing FM-02")
- P-04: edited + applied (user swapped "ALWAYS" for "NEVER")
- P-05: skipped (gate tripped; dormant_pct={N}%)
```

This is the only edit to the DREAM files themselves before archive.

---

## Phase 2: Promote

Goal: Push batch-produced facts into canonical places the next batch
will read.

### 2a. Glossary draft merge

If `specs/_batch/glossary-draft.md` exists:

1. Diff each term in the draft against `CONTEXT.md`:
   - New term (not in glossary) → candidate for append.
   - Existing term with new synonym / correction → candidate for update.
2. For each candidate, ask the user via `AskUserQuestion(approve /
   reject / edit)`. Approved terms append to `CONTEXT.md` under
   the existing sort order.
3. If all terms rejected or draft absent, skip silently.

### 2b. Codemap sync

1. Parse `docs/feature-list.json` for `touches` paths of DONE features.
2. For any path matching `apps/*/lib/features/<new-dir>/` that isn't
   in `app_docs/codemap.md`, surface to the user as a proposed codemap
   line (`<dir>/ — <one-line purpose, ≤15 字>`).
3. `AskUserQuestion` per new dir. Approved lines append under the
   appropriate section of `codemap.md`.

### 2c. Feature-barrel backlog pass

If a `feature_barrel_audit.py` script exists:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/feature_barrel_audit.py
```

For any feature dir missing a barrel, append a line to
`docs/tech-debt-tracker.md` under the "Feature barrel backlog" section
(create it if absent). No user prompt — backlog accumulates silently.

If the script doesn't exist yet, skip this sub-phase with a note in
the final report.

---

## Phase 3: Archive

Goal: Move the batch's spec artifacts + proposals + summary into a
single frozen `specs/completed/{slug}/` directory; delete raw progress
logs; re-open empty containers for the next batch.

### 3a. Parse slug

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/preflight.py --print-slug \
  specs/_batch/plan.md
```

Script reads H1 of `plan.md`: `# Plan — batch {slug}`.

### 3b. Move artifacts

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/finalize_archive.sh {slug}
```

Script performs:
1. `mkdir -p specs/completed/{slug}/`
2. Move `specs/_batch/*` (plan, research, glossary-draft, questions,
   dep-hints, tmp/) → `specs/completed/{slug}/`
3. Move `docs/feature-list.json` → `specs/completed/{slug}/feature-list.json`
4. Move `docs/progress/DREAM-gen.md` + `docs/progress/DREAM-eval.md`
   → `specs/completed/{slug}/`
5. Generate `specs/completed/{slug}/BATCH_SUMMARY.md` (see 3c)
6. `git rm` all raw per-feature artifacts in `docs/progress/`:
   `F*-progress-R*.md`, `F*-eval-R*.md`, `F*-gen-trace-R*.md`,
   `F*-eval-trace-R*.md`, `F*-contract.md`
7. Re-create empty `docs/progress/.gitkeep` + `specs/_batch/.gitkeep`
8. Also move the `docs/progress/.traces/` dir into
   `specs/completed/{slug}/traces/` if non-empty; else delete it.

### 3c. Summary generation

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/summarize_progress.py \
  --out specs/completed/{slug}/BATCH_SUMMARY.md
```

Script reads each `F*-progress-R*.md` + `F*-eval-R*.md` in
`docs/progress/` BEFORE the archive move. For each feature, extract:
- Terminal state (DONE / BLOCKED) and round
- One-line headline (from the progress file's `## Outcome` section if
  present; else the first paragraph trimmed to ≤ 80 chars)
- Any `infraBlocked: true` flag from eval

Output format:

```markdown
# Batch Summary — {slug}

Base commit: {baseCommit}
Completed: {YYYY-MM-DD}
Features: {done}/{total} DONE, {blocked} BLOCKED

## Feature Outcomes

| Feature | State | Round | Headline |
|---|---|---|---|
| F01 | DONE | R1 | {headline} |
| F02 | DONE | R2 | {headline} |
| F03 | BLOCKED | R3 | {headline} (infraBlocked) |
...

## Notes

- Proposals applied: {N}/{total} (see DREAM-*.md Applied section for
  audit trail)
```

---

## Phase 4: Scan

Goal: Detect drift introduced by this batch before starting the next.

Spawn the `doc-garden` agent as a sub-agent. Prompt template:

```
Post-finalize drift scan for batch {slug}. Scans:
1. docs/design-docs/ reference integrity
2. docs/adr/ ADR lifecycle vitality (proposed/accepted/superseded chain integrity)
3. learned-anti-patterns/*.md currency
4. Recipe liveness (recipe_liveness.py)

Auto-fix trivial drift. Log everything else to
docs/tech-debt-tracker.md under a new H2
"## Post-{slug} drift scan ({YYYY-MM-DD})".

Report summary inline when complete.
```

Record the agent's summary (1-3 lines) for Phase 5's commit message.

---

## Phase 5: Commit + Report

### 5a. Commit

```bash
git add -A
git commit -m "chore(finalize): close batch {slug}

- Dreamer proposals: {applied}/{total} applied ({rejected} rejected, {skipped} skipped)
- Archived to specs/completed/{slug}/
- Doc-garden: {scan-summary}"
```

If the commit is empty (nothing applied, nothing scanned), abort with
diagnostic — /finalize should never land an empty commit.

### 5b. Report

```
═══════════════════════════════════════════════════════════════
/finalize COMPLETE — {slug}
═══════════════════════════════════════════════════════════════

Proposals:   {applied}/{total} applied
             {rejected} rejected, {skipped} skipped (gate-tripped)
Glossary:    {N} terms appended
Codemap:     {N} feature dirs added
Barrels:     {N} features logged to tech-debt-tracker.md
Archive:     specs/completed/{slug}/
             ({spec-files} + feature-list.json + DREAM-*.md + BATCH_SUMMARY.md)
Progress:    {N} raw F*-*.md deleted
Doc-garden:  {scan-findings-count} findings

Next step: /prd (for next batch)
═══════════════════════════════════════════════════════════════
```

---

## Rules

- NEVER apply a proposal without explicit `AskUserQuestion` approval.
- NEVER skip Phase 4 (doc-garden) — drift is a concern even when
  nothing else changed.
- NEVER modify source code in this skill (apps/*, dandan_server/*).
- NEVER re-run `/finalize` against an already-archived batch — Phase 1a
  pre-flight detects the empty `specs/_batch/` and aborts.
- ALWAYS commit exactly once at the end. No partial /finalize state
  left in working tree.

## Red Flags

- DREAM-*.md files touched outside the "Applied" append
- Direct writes to capsules/SKILL.md/anti-patterns outside Phase 1d
  dispatch table
- Empty commit at Phase 5
- `specs/_batch/` left non-empty after Phase 3
- `docs/progress/F*-*.md` surviving past Phase 3

## Verification

After /finalize completes:

- [ ] `docs/progress/` contains only `.gitkeep` (no `F*-*.md`, no `DREAM-*.md`)
- [ ] `specs/_batch/` contains only `.gitkeep`
- [ ] `specs/completed/{slug}/` contains plan/research/glossary-draft/
      questions/dep-hints + feature-list.json + DREAM-gen.md +
      DREAM-eval.md + BATCH_SUMMARY.md (+ tmp/ and traces/ if any)
- [ ] `docs/feature-list.json` does NOT exist (archived)
- [ ] `docs/tech-debt-tracker.md` has the "Post-{slug} drift scan" H2
- [ ] `CONTEXT.md` has the approved terms (if any)
- [ ] `app_docs/codemap.md` has the approved new feature dirs (if any)
- [ ] Single clean `chore(finalize):` git commit
