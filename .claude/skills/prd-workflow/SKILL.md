---
name: prd-workflow
description: Drive Stage 1 of the gan-harness — turn free-form user intent into specs/_batch/prd.md (per-batch PRD, all R as H2 sections) plus specs/_batch/research.md (blindfold codebase facts) ready for /plan to consume. Make sure to use this skill whenever /prd runs, when the user wants to start a new batch, or when handoff to /plan needs structured PRD + research artefacts.
---

# PRD Workflow

Stage 1 of the harness. One command (`/prd`), four phases, one human checkpoint, one structural lint. Produces a per-batch PRD draft + a snapshot of the relevant codebase facts that downstream stages (plan, execute, finalize) consume.

Pipeline shape:

```
/prd
  ├─ Pre-flight (specs/_batch/ empty? abort if half-done batch present)
  ├─ Phase 1 — Grill (MAIN session interviews user; produces prd.md draft + _research-queue.md)
  ├─ Phase 2 — Post-grill checkpoint (single AskUserQuestion: Approve / Revise / Abort)
  ├─ Phase 3 — Codebase research dispatch (codebase-fact-finder × N, blindfold = prd.md, parallel ≤6/turn)
  ├─ Phase 4 — Synth (compile research.md, run prd_lint, delete transient queue)
  ↓
specs/_batch/prd.md + specs/_batch/research.md ready
```

The grill happens **in MAIN session**, not in a subagent. Subagents are for fresh-context bulk work (codebase-fact-finder, planner); interactive multi-turn dialogue belongs in MAIN. Grill discipline lives in [`references/grill-protocol.md`](references/grill-protocol.md), loaded when entering Phase 1.

## Mandatory before starting

Before starting grill or dispatching any subagent, surface your assumptions:

ASSUMPTIONS I'M MAKING:
1. <e.g., "specs/_batch/ is empty (no half-done batch from a prior run)">
2. <e.g., "active stack skill is X based on .claude/skills/ contents">
3. <e.g., "user's intent dump is in $ARGUMENTS or will be supplied during grill">
→ Correct me now or I'll proceed with these.

Do not silently fill in ambiguous requirements.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "User probably means X" | Don't infer intent. Ask. (Reframe vague targets per `references/grill-protocol.md` § Reframe.) |
| "I have enough to write the spec now" | If any branch of the design tree is unresolved, you don't. Walk every branch. |
| "User said 'just figure it out for me' — I'll fill in" | Don't. /prd's entire purpose is surfacing assumptions before code. Filling silently is the worst mode. |
| "User's dump is contradictory, I'll resolve by picking the later statement" | Don't auto-resolve. Surface: "You said A on line 3 and not-A on line 7 — which?" |
| "Skip codebase research, just go from grill to /plan" | No. /plan has no research phase; that work happens here. Skipping leaves planner blind. |
| "Fact-finder failed on Q-03, just skip that finding" | Surface failure to user. research.md is incomplete; user decides skip vs retry vs abort. |
| "User approved at checkpoint, even though one R is still vague" | Re-grill the vague R. Approve means all R are concrete with measurable criteria. |

## Inputs

- `$ARGUMENTS` — user's intent dump (paragraph, list, file path, or empty)
- `CONTEXT.md` — domain ubiquitous language
- `docs/adr/index.md` — accepted ADR catalogue
- [`references/grill-protocol.md`](references/grill-protocol.md) — grill discipline + output formats (loaded at Phase 1)
- Active stack skill at `.claude/skills/<active-stack>/`

## Outputs

- `specs/_batch/prd.md` — per-batch PRD; all R as H2 sections; passes `prd_lint.py`; primary handoff to `/plan`
- `specs/_batch/research.md` — blindfold codebase facts compiled from fact-finders; `base_commit` + `timestamp` header

Transient (created and deleted within `/prd`):

- `specs/_batch/_research-queue.md` — questions for fact-finder dispatch; deleted at Phase 4 synth
- `specs/_batch/_research-findings/Q-NN.md` — per-fact-finder outputs; directory deleted at Phase 4 synth

## Phases

### Pre-flight

Check `specs/_batch/`. Allowed states:

- **Empty / not exists** — fresh batch, proceed.
- **Contains stale `_research-queue.md` only** — prior `/prd` aborted mid-flight; delete the queue, proceed (user will re-grill).
- **Contains `prd.md` or `feature-list.json`** — abort with diagnostic. Either run `/finalize` to archive the prior batch, or delete `specs/_batch/` manually if abandoned.

### Phase 1 — Grill (in MAIN session)

Load [`references/grill-protocol.md`](references/grill-protocol.md). Follow its rules:

- One AskUserQuestion at a time
- Recommend answer + rationale per question
- Reframe vague targets into measurable success criteria
- Surface assumptions explicitly
- Surface contradictions, don't auto-resolve
- Cross-check user terms against `CONTEXT.md`
- Cross-check user requests against `docs/adr/index.md`
- Codebase claims → `_research-queue.md`, not verified inline

When the grill protocol's done-with-grill checklist passes, write:

- `specs/_batch/prd.md` (per § Output format in grill-protocol.md)
- `specs/_batch/_research-queue.md` (per § Output format in grill-protocol.md)

If the user says "abort" mid-grill, delete any partial files and exit cleanly.

### Phase 2 — Post-grill checkpoint

Run **one** `AskUserQuestion`. Render the payload on-the-fly from `prd.md`:

- Batch slug + one-line summary
- Per R: id + slug + story count + AC count + draft term count
- Research queue: Q count

Three options:

- **Approve** — proceed to Phase 3.
- **Revise** — user provides a section / R to revise. Re-enter grill scoped to that section. Loop back to Phase 2 after revision.
- **Abort** — delete `prd.md` and `_research-queue.md`, exit cleanly.

### Phase 3 — Codebase research dispatch

Read `_research-queue.md`, parse Q-NN stanzas. For each Q, spawn a `codebase-fact-finder` subagent (parallel batches ≤6 per assistant turn).

Each fact-finder receives:

- Its own Q-NN question text (only)
- An output path: `specs/_batch/_research-findings/Q-NN.md`
- A blindfold list of forbidden paths: `specs/_batch/prd.md` (PRD must not leak into research)

If `_research-queue.md` is empty, skip Phase 3; Phase 4 writes a minimal `research.md` with header only.

### Phase 4 — Synth

Compile `specs/_batch/research.md`:

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

After research.md is written, run:

```
python3 .claude/skills/prd-workflow/scripts/prd_lint.py specs/_batch/prd.md
```

PASS/FAIL only. Any FAIL → report violations to user; user must run `/prd` revision loop or manually fix prd.md before declaring /prd done.

After lint PASSES, delete `specs/_batch/_research-queue.md` and `specs/_batch/_research-findings/`.

Print final summary:

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

This skill describes the orchestration. The grilling discipline (one-question-at-a-time, surface assumptions, reframe vague targets, output formats) lives in [`references/grill-protocol.md`](references/grill-protocol.md). The codebase research discipline (facts only, file:line evidence, blindfold) lives in `.claude/agents/codebase-fact-finder.md`. Stack-specific idioms live in the active stack skill's `references/`.

## Anti-patterns

- **Spawning a subagent for grill** — grill is interactive multi-turn dialogue; runs in MAIN. Subagents are for fresh-context bulk work.
- **Multi-question grill at the checkpoint** — Phase 2 is ONE AskUserQuestion (Approve / Revise / Abort). All grill happened in Phase 1.
- **Fact-finder reading prd.md** — blindfold is a hard rule; pass the blindfold list to every fact-finder dispatch.
- **Embedding research findings inside prd.md** — research goes to `research.md`. prd.md is intent. Different rot lifecycles, different files.
- **Skipping prd_lint.py** — lint is the contract. /plan trusts that prd.md is well-formed because /prd ran lint.
- **Persisting `_research-queue.md` past Phase 4** — transient by design. Deletion at end of synth is the contract.
- **Per-R subdirs (`specs/R1/`, `specs/R2/`)** — single batch-level files, H2 sections per R. With 1M context the planner needs cross-R coherence in one read; sharding wastes tokens and breaks `depends_on` reasoning across R boundaries.
- **Forbidden PRD sections** — prd_lint.py rejects `## Implementation Decisions`, `## Tech Stack`, `## Architecture`, `## Risks`, `## Tech Debt`, `## Timeline`. Industry convention: PRD = what/why, plan = how.
- **Auto-resolving vague targets** — reframe into measurable success criteria + bounce back ("Are these the right targets?"). Don't pick thresholds without confirmation.

## Done when

- [ ] `specs/_batch/prd.md` exists, prd_lint.py PASSES
- [ ] `specs/_batch/research.md` exists with `base_commit` + `timestamp` header
- [ ] `specs/_batch/_research-queue.md` and `specs/_batch/_research-findings/` deleted
- [ ] Phase 2 checkpoint answered Approve (or Abort/Revise loop completed)
- [ ] Final summary printed; `/plan` suggested as next step
