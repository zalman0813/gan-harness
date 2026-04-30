---
name: prd-workflow
description: Drive Stage 1 of the gan-harness — turn free-form user intent into specs/_batch/prd.md (per-batch PRD, all R as H2 sections) plus specs/_batch/research.md (blindfold codebase facts) ready for /plan to consume. Make sure to use this skill whenever /prd runs, when the user wants to start a new batch, or when handoff to /plan needs structured PRD + research artefacts.
---

# PRD Workflow

Stage 1 of the harness. One command (`/prd`), four phases, one human checkpoint, one structural lint. Produces a per-batch PRD draft + a snapshot of the relevant codebase facts that downstream stages (plan, execute, finalize) consume.

Pipeline shape (locked by `TODO.md` § Locked decisions):

```
/prd
  ├─ Pre-flight (specs/_batch/ empty? abort if half-done batch present)
  ├─ Phase 1 — Grill (spawn grill-master subagent; produces prd.md draft + _research-queue.md)
  ├─ Phase 2 — Post-grill checkpoint (single AskUserQuestion: Approve / Revise / Abort)
  ├─ Phase 3 — Codebase research dispatch (codebase-fact-finder × N, blindfold = prd.md, parallel ≤6/turn)
  ├─ Phase 4 — Synth (compile research.md, run prd_lint, delete transient queue)
  ↓
specs/_batch/prd.md + specs/_batch/research.md ready
```

## Mandatory before starting

Before spawning grill-master or dispatching fact-finders, surface your assumptions:

ASSUMPTIONS I'M MAKING:
1. <e.g., "specs/_batch/ is empty (no half-done batch from a prior run)">
2. <e.g., "active stack skill is X based on .claude/skills/ contents">
3. <e.g., "user's intent dump is in $ARGUMENTS or will be supplied during grill">
→ Correct me now or I'll proceed with these.

Do not silently fill in ambiguous requirements. See `docs/agent-prompt-doctrine.md` § Universal rules.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Skip codebase research, just go from grill to /plan" | No. /plan has no research phase; that work happens here. Skipping leaves planner blind to existing code. |
| "User approved at checkpoint, even though one R is still vague" | Re-grill the vague R, do not proceed. Approve means all R are concrete. |
| "Fact-finder failed on Q-03, just skip that finding" | A failed Q means research.md is incomplete. Surface the failure to user before declaring /prd done; let them decide skip vs retry vs abort. |
| "User said 'just figure it out for me' — I'll fill in the rest" | Don't. /prd's entire purpose is to surface assumptions before code is written. Filling in silently is the worst possible mode. |

## Inputs

- `$ARGUMENTS` — user's intent dump (paragraph, list, file path, or empty)
- `CONTEXT.md` — domain ubiquitous language
- `docs/adr/index.md` — accepted ADR catalogue
- `ARCHITECTURE.md` — invariants
- `docs/agent-prompt-doctrine.md` — universal constraint layer
- Active stack skill at `.claude/skills/<active-stack>/`

## Outputs

- `specs/_batch/prd.md` — per-batch PRD; all R as H2 sections; passes `prd_lint.py`; primary handoff to `/plan`
- `specs/_batch/research.md` — blindfold codebase facts compiled from fact-finders; `base_commit` + `timestamp` header

Transient (created and deleted within `/prd`):

- `specs/_batch/_research-queue.md` — questions for fact-finder dispatch; deleted after Phase 4 synth

## Phases

### Pre-flight

MAIN checks `specs/_batch/`. Allowed states:

- **Empty / not exists** — fresh batch, proceed.
- **Contains stale `_research-queue.md` only** — prior `/prd` aborted mid-flight; delete the queue, proceed (user will re-grill).
- **Contains `prd.md` or `feature-list.json`** — abort with diagnostic. Either run `/finalize` to archive the prior batch, or delete `specs/_batch/` manually if the prior batch was abandoned.

### Phase 1 — Grill

MAIN spawns the `grill-master` subagent (single agent, sonnet model). Pass `$ARGUMENTS` as the intent dump. Grill-master conducts the interview directly with the user (its own AskUserQuestion turns), one question at a time, until every R has all required sub-sections concrete.

Grill-master returns when both files are written:

- `specs/_batch/prd.md` (PRD draft, all R as H2 sections, all 6 sub-sections per R)
- `specs/_batch/_research-queue.md` (research questions, one per Q-NN stanza)

If grill-master returns early (e.g., user typed "abort"), MAIN deletes any partial files and exits cleanly.

### Phase 2 — Post-grill checkpoint

MAIN runs **one** `AskUserQuestion`. The payload is rendered on-the-fly from `prd.md`:

- Batch slug + one-line summary
- Per R: id + slug + story count + AC count + draft term count
- Research queue: Q count

Three options:

- **Approve** — proceed to Phase 3.
- **Revise** — user provides a section / R to revise. MAIN re-spawns grill-master with the revision request scoped to that section. Loop back to Phase 2 after revision.
- **Abort** — MAIN deletes `prd.md` and `_research-queue.md`, exits cleanly.

### Phase 3 — Codebase research dispatch

MAIN reads `_research-queue.md`, parses Q-NN stanzas. For each Q, spawn a `codebase-fact-finder` subagent (parallel batches ≤6 per assistant turn).

Each fact-finder receives:

- Its own Q-NN question text (only)
- An output path: `specs/_batch/_research-findings/Q-NN.md`
- A blindfold list of forbidden paths: `specs/_batch/prd.md` (the PRD must not leak into research)

If `_research-queue.md` is empty (rare — the grill produced no codebase questions), skip Phase 3 entirely; Phase 4 writes a minimal `research.md` with header only.

### Phase 4 — Synth

MAIN compiles `specs/_batch/research.md`:

```markdown
# Batch Research — <batch-slug>

base_commit: <output of `git rev-parse HEAD` at synth time>
timestamp: <ISO 8601 at synth time>

## Q-01 — <question text>

(content from specs/_batch/_research-findings/Q-01.md)

## Q-02 — <question text>

(...)
```

If a fact-finder reported `Unanswerable` or `Unverified`, that finding still goes into research.md verbatim — downstream consumers (planner) need to know what wasn't established.

After research.md is written, MAIN runs:

```
python3 .claude/skills/prd-workflow/scripts/prd_lint.py specs/_batch/prd.md
```

PASS/FAIL only. Any FAIL → MAIN reports violations to user; user must run `/prd` revision loop or manually fix prd.md before declaring /prd done.

After lint PASSES, MAIN deletes `specs/_batch/_research-queue.md` and `specs/_batch/_research-findings/` (transient files served their purpose).

MAIN prints final summary:

```
═══════════════════════════════════════════════════════════════
/prd COMPLETE — <batch-slug>
═══════════════════════════════════════════════════════════════

PRD:       specs/_batch/prd.md (<R> R, <S> stories, <A> ACs)
Research:  specs/_batch/research.md (<Q> questions, <F> findings)
base_commit: <sha>

Next step: /plan
═══════════════════════════════════════════════════════════════
```

## Where the heavy thinking lives

This skill describes the orchestration. The grilling discipline (one-question-at-a-time, surface assumptions, no silent inference) lives in `.claude/agents/grill-master.md`. The codebase research discipline (facts only, file:line evidence, blindfold) lives in `.claude/agents/codebase-fact-finder.md`. The universal constraint layer (rationalizations, surface-assumptions, no-silent-inference) lives in `docs/agent-prompt-doctrine.md`. Stack-specific idioms live in the active stack skill's `references/`.

## Anti-patterns

- **Multi-question grill at the checkpoint** — Phase 2 is ONE AskUserQuestion (Approve / Revise / Abort). All grill happened in Phase 1.
- **Fact-finder reading prd.md** — blindfold is a hard rule; pass the blindfold list to every fact-finder dispatch.
- **Embedding research findings inside prd.md** — research goes to `research.md`. prd.md is intent. Different rot lifecycles, different files.
- **Skipping prd_lint.py** — lint is the contract. /plan trusts that prd.md is well-formed because /prd ran lint.
- **Persisting `_research-queue.md` past Phase 4** — transient by design. Deletion at end of synth is the contract.
- **Per-R subdirs (`specs/R1/`, `specs/R2/`)** — single batch-level files, H2 sections per R. See `TODO.md` § Locked decisions.
- **Forbidden PRD sections** — prd_lint.py rejects `## Implementation Decisions`, `## Tech Stack`, `## Architecture`, `## Risks`, `## Tech Debt`, `## Timeline`. Industry convention: PRD = what/why, plan = how.

## Done when

- [ ] `specs/_batch/prd.md` exists, prd_lint.py PASSES
- [ ] `specs/_batch/research.md` exists with `base_commit` + `timestamp` header
- [ ] `specs/_batch/_research-queue.md` and `specs/_batch/_research-findings/` deleted
- [ ] Phase 2 checkpoint answered Approve (or Abort/Revise loop completed)
- [ ] Final summary printed; `/plan` suggested as next step
