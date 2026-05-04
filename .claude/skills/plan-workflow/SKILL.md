---
name: plan-workflow
description: Drive Stage 2 of the gan-harness — turn /prd's outputs (specs/_batch/prd.md + specs/_batch/research.md) into specs/_batch/feature-list.json plus new docs/adr/NNNN-*.md (status:proposed) via planner self-verify and a per-question human checkpoint walk. Make sure to use this skill whenever /plan runs, when the user asks to plan a batch of features, or when handoff from /prd to /execution-loop needs the planner's structured output.
---

# Plan Workflow

Stage 2 of the harness. One command (`/plan`), two phases, three scripts, one per-question human checkpoint. Produces a verifiable feature list and proposed ADRs that downstream stages (execution-loop, finalize) consume.

Research is **not** part of this stage anymore — `/prd` runs the blindfold codebase research as part of producing `prd.md` + `research.md`. By the time `/plan` runs, both files are already on disk.

## Mandatory before starting

Before spawning the planner subagent, surface your assumptions:

ASSUMPTIONS I'M MAKING:
1. <e.g., "specs/_batch/prd.md and research.md exist and are non-empty">
2. <e.g., "active stack skill is X based on .claude/skills/ contents">
3. ...
→ Correct me now or I'll proceed with these.

Do not silently fill in ambiguous requirements.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Phase 2 user looks tired, bulk-approve is enough" | Per-Q walk is contract. Each open_question and each ADR walked individually. No batch shortcut. |
| "Three-script trio: 2 PASS, 1 FAIL — close enough" | All three PASS or none. Any FAIL → planner re-fixes. No "two out of three". |
| "After 3 escalates the user is frustrated, push through anyway" | 3 escalates = batch scope is genuinely wrong. Abort to /prd, don't grind. |

## When to use

- `/plan` is invoked after `/prd` has produced `specs/_batch/prd.md` and `specs/_batch/research.md`
- The user wants to plan a batch of features for vertical-slice execution
- A previous `/plan` aborted and needs resuming (state under `specs/_batch/` indicates partial progress)

## Inputs

- **From /prd**: `specs/_batch/prd.md` (batch-level PRD; H2 sections per R; Domain terms draft per R), `specs/_batch/research.md` (batch-level codebase facts with base_commit + timestamp)
- **Alive masters**: `CODEMAP.md` (navigation), `CONTEXT.md` (domain language), `docs/adr/index.md` (ADR graph). Design concepts (guides/sensors, three-layer model) live in `README.md` § Core design concepts.
- **Active stack skill**: whatever `.claude/skills/<active-stack>/` exposes via its `references/` (idiom library)
- **Schema**: `.claude/schemas/feature-list.schema.json`

## Outputs

- `specs/_batch/feature-list.json` — validates against the schema; primary handoff to /execution-loop
- `docs/adr/NNNN-<slug>.md` × M — new ADRs with `status: proposed` (promoted to `accepted` at /finalize)

## Phases

### Phase 1 — Pre-flight + Planner self-verify

MAIN verifies `specs/_batch/prd.md` and `specs/_batch/research.md` exist and are non-empty; if missing, abort with clear diagnostic ("/prd must run first").

MAIN spawns the `planner` agent (single agent, opus model). The planner reads inputs above, designs vertical-slice features with deep-module interfaces, drafts new ADRs as `docs/adr/NNNN-*.md` (status:proposed), and writes `specs/_batch/feature-list.json`.

Before declaring done, the planner runs the **three-script trio** (see [planner-handbook/references/self-verify-loop.md](../planner-handbook/references/self-verify-loop.md)):

```
scripts/plan_validator.py    specs/_batch/feature-list.json
scripts/lift_capabilities.py specs/_batch/feature-list.json
scripts/plan_lint.py         specs/_batch/feature-list.json
```

All three are PASS/FAIL only. Any FAIL → planner reads violations → fixes the source design → retries (max 3 rounds). All PASS → exit Phase 1, hand to Phase 2 checkpoint.

If 3 rounds elapse and any script still FAILs, MAIN aborts with diagnostic. The design is fundamentally wrong — escalate to /prd for re-scope, do not grind further.

### Phase 2 — Pre-walk surfacing + per-question human checkpoint

#### Phase 2.0 — Pre-walk: surface planner's ASSUMPTIONS + escalations

Read the planner subagent's final summary (the message returned to MAIN at the end of Phase 1). Extract the following H2 blocks (header text must match verbatim — see planner.md § Outputs for the contract):

- `## Assumptions I made` — premises planner proceeded with
- `## Cannot recommend` — `Q-NN (Fxx): <reason>` entries planner couldn't answer

**If both blocks are absent**: skip Phase 2.0 entirely, proceed to Phase 2.1.

**If either block is present**: render one `AskUserQuestion` with the rendered blocks and three options:

```
Planner self-verify is complete. Before walking the open_questions and ADRs,
review the planner's surfaced premises:

## Assumptions I made
<rendered bullets, or omit this H2 if planner emitted no assumption block>

## Cannot recommend
<rendered Q-NN list, or omit this H2 if planner recommended every answer>

Options:
- Approve            — premises are correct; proceed to per-Q walk.
- Re-spawn planner   — at least one assumption is wrong, or a "Cannot
                       recommend" needs your answer now; re-spawn planner
                       with corrections, then loop back here.
- Abort              — batch scope is wrong; exit /plan and re-enter /prd.
```

Branch:

- **Approve** → continue to Phase 2.1.
- **Re-spawn planner** → user provides corrections (free-form text). MAIN re-spawns the `planner` subagent with a scoped amendment prompt:

  ```
  You are amending an existing batch's feature-list.json after the
  pre-walk checkpoint. The user has reviewed your prior assumptions /
  escalations and provided corrections. Apply them, then re-run the
  three-script self-verify trio.

  Corrections:
  <user-supplied text>

  After applying: run scripts/plan_validator.py, lift_capabilities.py,
  and plan_lint.py. Return a fresh final summary in the same H2 format
  (## Assumptions I made + ## Cannot recommend, omitting either H2 if
  empty).
  ```

  After the re-spawned planner returns, **loop back to Phase 2.0** with the new final summary. No round budget on re-spawns — user keeps Re-spawning until satisfied or chooses Abort.

- **Abort** → exit /plan with a "rerun /prd to re-scope" diagnostic. Do NOT delete `feature-list.json` or any ADR files — user may want to inspect them.

The pre-walk checkpoint is conversation, not a gate (same exemption Phase 2.1 uses), so it does not violate the "single human checkpoint per stage" invariant.

#### Phase 2.1 — Per-question walk

MAIN walks every open_question (across all features) where `resolution_kind ∈ {feature_local, architectural, glossary}` AND every proposed ADR. One AskUserQuestion per item, in this order:

1. All open_questions, ordered by feature id then question id
2. All proposed ADRs, ordered by ADR id

For each open_question, present:
- Feature id + name + the question text
- Planner's recommended `resolution` text + rationale
- Three options:
  - **Approve** — keep planner's resolution as-is
  - **Edit** — user provides corrected resolution; MAIN updates `feature-list.json` in place
  - **Escalate** — user cannot answer; abort the entire batch back to /prd for re-scope

For each proposed ADR, present:
- ADR file path + title + body + which features reference it
- Three options:
  - **Approve** — ADR stays `status: proposed`, included in next /finalize promotion
  - **Edit** — user provides corrected body / title; MAIN updates the ADR file
  - **Reject** — MAIN deletes the ADR file AND removes its path from every `decision_refs[]` in feature-list.json; planner must re-route the underlying concern (typically into `spec.business_rules` or an open_question with `resolution_kind: feature_local`)

After each Edit or Reject, MAIN re-runs the three-script trio. If any FAIL, surface violations to user before continuing the walk; remaining items wait until trio passes.

After the walk completes (no remaining items), MAIN prints the final report; `/execution-loop` is the suggested next step.

If any Escalate fired during the walk, MAIN aborts immediately — no point continuing the walk when scope is wrong. User reruns `/prd` to fix the affected R, then `/plan` again.

## Where the heavy thinking lives

This skill describes the orchestration. The actual design doctrine the planner agent uses is in [planner-handbook](../planner-handbook/SKILL.md), which the planner subagent auto-loads at startup via its `skills:` frontmatter. Stack-specific idioms (barrel patterns, test commands) live in the active stack skill's `references/` (see [stack-skill-creator](../stack-skill-creator/SKILL.md) to bootstrap one).

## Anti-patterns

- **Bulk-approve at Phase 2** — every question and every ADR is walked individually; no "Approve all".
- **Phase 1 humans editing live** — humans only see results after self-verify trio PASSES, not mid-loop.
- **Skipping the three-script trio** — the trio is the anti-rot guarantee; without it `feature-list.json` drifts from the schema.
- **Persisting a `plan.md` summary file** — the human review surface is rendered on-the-fly from `feature-list.json` per item; do not write `plan.md` as an intermediate file.
- **Cross-R Risks / Tech Debt section anywhere** — zero-debt rule: every risk resolves into an ADR, an open_question, or a feature. Schema's `additionalProperties: false` at top level rejects rogue fields.
- **Planner writing into alive masters** — planner only writes `specs/_batch/feature-list.json` and `docs/adr/NNNN-*.md` (proposed); all other masters are touched only at /finalize.
- **Running blindfold research from /plan** — research happened at /prd. /plan reads `research.md`; it does not spawn fact-finders.

## Done when

- [ ] `specs/_batch/feature-list.json` exists, three-script trio PASS
- [ ] `docs/adr/NNNN-*.md` × M (status:proposed) exist for every architectural decision the planner identified
- [ ] Phase 2.0 pre-walk completed (skipped if planner emitted no assumptions/escalations, OR user Approved, OR user Re-spawned and re-Approved)
- [ ] Phase 2.1 walked every open_question and every proposed ADR; all answered Approve or Edit (no Escalate, no Reject leaving inconsistent state)
- [ ] Final report printed; `/execution-loop` suggested
