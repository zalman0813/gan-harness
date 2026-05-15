---
name: init-workflow
description: Drive Stage 1 of the gan-harness v3.8 — turn free-form user intent into specs/_epic/spec.md (immutable high-level spec) plus optional fact-finder research, ready for /loop to consume. Replaces v1's prd-workflow + plan-workflow combo. Make sure to use this skill whenever /init runs, when the user asks to start a new epic, or when handoff to /loop needs a finalized spec.md and tech-stack confirmation.
disable-model-invocation: false
---

# init-workflow

Stage 1 of v3.8. Single skill, single agent (planner), single human
checkpoint. Replaces the v1 two-stage `/prd` + `/plan` combo because that
combo was producing over-prescribed specs that downstream agents couldn't
work around.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. The user has provided an intent dump (free-form text) and a target tech
   stack (or wants the planner to grill for it).
2. `specs/_epic/` does not yet exist (or has been archived from the
   previous epic). If it exists with content, ABORT — `/finalize` must
   run first to archive the previous epic.
3. The relevant stack skill already exists at `.claude/skills/<stack>/`.
   If not, the user needs to run `stack-skill-creator` first.

## Common rationalisations

| Rationalization | Reality |
|---|---|
| "Specs/_epic/ has stale content from a prior session, I'll just overwrite" | No. stale content = the prior epic didn't archive cleanly. Run /finalize on it first. |
| "Planner can use AskUserQuestion to ask the user" | No. Planner is a subagent; AskUserQuestion in subagent context does not reach the human. Planner writes `specs/_epic/_grill.html` and returns; MAIN session shows the file to the user and parses pasted-back `PLANNER REVISION:` / `PLANNER APPROVE:` blobs. |
| "I'll just take planner's recommended choices and skip the user review" | No. That's the silent-failure pattern we replaced. The user MUST see `_grill.html` and either revise or paste an explicit `PLANNER APPROVE:` blob. Only `--no-grill` legitimately auto-approves (and then it's the user's explicit opt-out). |
| "The user gave a frontend prompt but I think backend criteria are better" | Archetype goes into the grill as a pre-selected radio with planner's recommendation + tradeoff alternatives. If planner disagrees with the dump, surface it as a toggle group, not as a unilateral decision. |
| "I'll write the spec inline and skip lint" | spec_lint MUST pass before finalize returns DONE. Lint failure = the spec violates the contract; it can't be approved. |
| "I'll skip fact-finder for this brownfield because the codebase is small" | Brownfield always uses fact-finder. The blindfold pattern is what keeps planner-bias out of research. Surface the fact-finder questions as a toggle group in `_grill.html` so the user sees what's being researched. |
| "Planner will spawn the fact-finders since it knows the questions" | No. Planner is a subagent; subagents cannot spawn subagents (runtime nesting limit) and planner's tools list excludes `Agent` anyway. Planner writes the open-question list to `_research/_questions.json` and returns `research_pending=K`. The **MAIN session** dispatches the K `codebase-fact-finder` subagents in parallel (Phase 1.5), then re-spawns planner so it can read the `_research/<id>.md` answers first-hand. |
| "I'll merge two PLANNER REVISION blobs from the same round into one planner spawn" | No. Each user paste = one revision round = one fresh planner spawn. Merging blobs loses round-counter accuracy (12-round circuit breaker) and conflates user intent across two separate review passes. |

## Inputs

- User intent dump (free-form text; from the slash command's `$ARGUMENTS`).
- Optional flag from the user: `--no-grill` (skip the browser-review
  revision loop; auto-finalise with planner's own recommended choices).
  Legacy `--no-confirm` is aliased to `--no-grill` with a deprecation
  warning.
- `CONTEXT.md` (existing domain language).
- `docs/adr/index.md` (existing accepted architectural decisions).
- `specs/epics/` (recent archived epics for context, optional).
- For brownfield only: existing source code (read-only access;
  `codebase-fact-finder` subagents do this in parallel with blindfold
  protocol). **The MAIN session dispatches them** (Phase 1.5 below) —
  planner cannot, because subagents cannot nest and planner's tools
  list omits `Agent`. Planner only emits the question list to
  `specs/_epic/_research/_questions.json` and signals
  `research_pending=K` in its `GRILL READY:` line.

## Process

### Phase 0 — Pre-flight

1. If `specs/_epic/` exists with content, ABORT with: "previous epic
   not archived; run /finalize first".
2. Create `specs/_epic/` directory.
3. Parse user flag: `--no-grill` (with `--no-confirm` aliasing).

### Phase 1 — Spawn planner `--produce-grill` (initial round)

The planner agent (auto-loads `planner-handbook`, `adr-lifecycle`) runs
in `--produce-grill` mode. Pass it the intent dump and any flags. Note:
planner does NOT load `deep-module-handbook` in v3.8 — module-level
cognition is a /loop sprint-contract concern handled by generator and
evaluator, not planner.

The planner will:
- Run stack discovery (Glob + Read each `.claude/skills/<stack>/SKILL.md`).
- Read any existing `specs/_epic/_research/<id>.md` files first-hand
  (none yet on the initial round; populated on later rounds by Phase
  1.5).
- Draft best-guess answers for every required toggle group. For
  brownfield toggles whose answer depends on unanswered research, the
  draft renders `[research-pending: <question-id>]`.
- If brownfield, write `specs/_epic/_research/_questions.json` with the
  list of still-open blindfold questions. Greenfield → skip the file.
- Write `specs/_epic/_grill.html` with planner's drafts + tradeoffs +
  recommended pre-selections per the structure spec'd in
  `.claude/agents/planner.md > ## Grill artifact (_grill.html) —
  required structure`.
- Return `GRILL READY: specs/_epic/_grill.html (round=<R>; toggles=<N>;
  research_pending=<K>)`.

The planner cannot and must not dispatch fact-finder subagents itself.
Subagents cannot spawn subagents, and planner's tools list excludes
`Agent`. The dispatch lives in Phase 1.5, owned by the MAIN session.

### Phase 1.5 — Research dispatch (MAIN session, brownfield only)

Parse `research_pending=K` from the `GRILL READY:` line the planner
just returned.

- `K=0` (or missing — greenfield) → skip this phase entirely; proceed
  to Phase 2.
- `K>0` → MAIN session does the following:
  1. Read `specs/_epic/_research/_questions.json`. Expected schema:
     ```json
     {
       "round": <R>,
       "questions": [
         {"id": "kebab-case-id", "question": "...", "rationale": "..."}
       ]
     }
     ```
  2. Dispatch K `codebase-fact-finder` subagents **in parallel** — one
     Agent tool call per question, all in a single message so they
     execute concurrently. Each subagent prompt MUST be self-contained
     (subagents start in a fresh context with no view of the spec
     draft, the grill, or sibling questions — that is the blindfold).
     Pass the agent: (a) the `question` verbatim, (b) the `rationale`,
     (c) the required output path `specs/_epic/_research/<id>.md`.
  3. Wait for all K subagents to return. Verify each
     `_research/<id>.md` exists; if any is missing, re-dispatch only
     the missing ones.
  4. Re-spawn planner `--produce-grill` with the same intent dump (no
     new revision blob — this is a research-refresh, not a user
     revision). Planner reads the `_research/*.md` files first-hand
     and overwrites `_grill.html` + `_questions.json` accordingly.
  5. Repeat Phase 1.5 if the new `GRILL READY:` line still reports
     `research_pending>0` (e.g., follow-up questions emerged from
     research findings). Hard cap: 3 research rounds before surfacing
     `BLOCKED: research did not converge; check _questions.json for
     loops` and asking the user whether to proceed anyway.

This loop terminates with `research_pending=0`. Only then does Phase 2
fire.

### Phase 2 — Surface to user

MAIN session does this (planner has already returned). On darwin, call
`open <absolute path to _grill.html>` via Bash so the file launches in
the default browser. Otherwise just print the absolute path. Then tell
the user:

> Review the toggles. When satisfied, click **Copy as prompt — approve**
> at the bottom and paste here. To revise instead, click **Copy as
> prompt — revise** and paste here. Free-form feedback also works — I'll
> wrap it as a revision blob.

### Phase 3 — Revision loop (MAIN session owns this)

Loop:

1. Wait for the user's next message.
2. Inspect the first non-empty line:
   - `PLANNER REVISION:` → spawn planner `--produce-grill` with the
     full blob in the prompt; planner regenerates `_grill.html`; round
     counter increments. **Then re-run Phase 1.5** — if the revision
     added new questions or invalidated prior research, planner's new
     `GRILL READY:` line may report `research_pending>0` again,
     requiring MAIN-session dispatch before surfacing the grill. Once
     Phase 1.5 settles to `research_pending=0`, loop back to Phase 2.
   - `PLANNER APPROVE:` → exit loop, go to Phase 4.
   - Anything else → wrap as `PLANNER REVISION:\n- Free text: <user
     message verbatim>` and proceed as a revision round.
3. After 12 revision rounds without `PLANNER APPROVE:`, surface
   `BLOCKED: 12 revision rounds without approve` and ask the user
   whether to abort or continue beyond the cap.

`--no-grill` short-circuit: skip Phases 2 and 3 entirely. Phase 1.5
still runs for brownfield (research is non-negotiable; the blindfold
pattern is what keeps planner-bias out of fact gathering). After
Phase 1.5 settles to `research_pending=0`, go to Phase 4 with an
auto-approve blob built from planner's own recommended choices in the
HTML.

### Phase 4 — Spawn planner `--finalize`

Spawn planner in `--finalize` mode with the `PLANNER APPROVE:` blob in
the prompt. Planner will:

- Read `_grill.html` for full current state.
- Synthesise `specs/_epic/spec.md` per the 9-H2 schema, honouring the
  approve blob's choices verbatim.
- Run `python .claude/skills/init-workflow/scripts/spec_lint.py
  specs/_epic/spec.md`. Fix-and-rerun until PASS (cap 3 fix attempts).
- Optionally write `docs/adr/NNNN-*.md` with `status: proposed` (rare,
  only if a candidate accepted in the approve blob).
- Return `DONE: specs/_epic/spec.md (lint PASS; ...)`.

`_grill.html` stays in `specs/_epic/` as audit trail; `/finalize`
archives it alongside `spec.md` at the end of the epic.

### Phase 5 — Hand off

Write a one-line summary to stdout:
```
init complete. Epic: <slug>. Sprints: N planned. Next: /loop
```

## Outputs

- `specs/_epic/_grill.html` — the grill contract artifact, rewritten
  each revision round. Audit trail; archived at /finalize.
- `specs/_epic/spec.md` — the immutable spec.
- `specs/_epic/_research/_questions.json` — planner-authored open-question
  list, rewritten each `--produce-grill` round (brownfield only). MAIN
  session consumes it in Phase 1.5 to dispatch fact-finders.
- `specs/_epic/_research/<id>.md` × N — one per question; written by
  the `codebase-fact-finder` subagents that MAIN session dispatches in
  Phase 1.5 (brownfield only).
- `docs/adr/NNNN-*.md` × M — only when ADR-worthy decisions emerged.
  `status: proposed`. Promoted at `/finalize`.

That's all. No `feature-list.json`. No granular AC. No per-sprint
contract. Those come from `/loop`.

## Anti-patterns

**Producing a spec that fails lint.** The spec must PASS `spec_lint.py`
before finalize returns DONE. If lint flags an issue, fix it; don't
"override".

**Skipping the browser-review revision loop when the user didn't
explicitly opt-in.** `--no-grill` is opt-in. Default is "user reviews
`_grill.html`, pastes either REVISION or APPROVE blob, MAIN session
iterates until APPROVE". Auto-finalising on planner's recommendations
without user paste is silent fabrication — the failure mode this
redesign exists to eliminate.

**Filling in archetype/criteria from training priors.** If the dump
doesn't say what archetype, surface it as a toggle group in
`_grill.html` with planner's recommendation + tradeoff alternatives
pre-loaded. The user picks. Training priors only ever provide the
*recommendation*, never the *decision*.

**Skipping fact-finder for brownfield.** Blindfold research is what
keeps planner-bias out of code-state observation. If brownfield, MAIN
session always dispatches in Phase 1.5 — never relies on planner's
draft alone. The fact-finder question list is itself a toggle group in
`_grill.html` so the user sees what's being researched.

**Letting planner dispatch fact-finder.** Subagents cannot spawn
subagents (runtime nesting forbidden); planner's tools list also
excludes `Agent`. Planner emits `_research/_questions.json` and signals
`research_pending=K`. MAIN session dispatches the K
`codebase-fact-finder` subagents in parallel (single message, K Agent
tool calls), waits for all to write `_research/<id>.md`, then
re-spawns planner. Anything else is the silent-failure pattern this
design exists to eliminate.

**Writing prd.md or feature-list.json.** Those are v1 artefacts. v3.8
has spec.md (+ _grill.html as audit) only.

**Letting planner own the revision loop.** Planner runs fresh-context
per spawn and cannot block on user input. MAIN session owns the loop
counter, the user-paste detection, and the spawn cadence. Planner is
stateless across rounds beyond what `_grill.html` encodes.

**Merging two consecutive user pastes into one planner spawn.** Each
paste = one revision round = one fresh planner spawn. Merging breaks
the 12-round circuit breaker and conflates two separate review passes.

## Scripts

- `scripts/spec_lint.py <path>` — validates spec.md against L01-L07.
  Exit 0 on PASS; exit 1 with JSON-on-stderr findings on FAIL.
