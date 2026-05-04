# Agent Prompt Doctrine

> **What this file is.** A maintainer-facing design memo describing the
> shape every "doing work" prompt in this harness has settled on. Living
> document — update when a new drift pattern is observed across the
> harness.
>
> **What this file is NOT.** A runtime SSoT. Nothing under `.claude/` or
> `templates/` references this file, and nothing should. Each agent
> prompt and each worker SKILL.md inlines its own constraint sections
> (Mandatory / Rationalizations / Principles / Anti-patterns). The agent
> prompt is the SSoT for that agent's behaviour; this catalogue is a
> cross-agent overview maintained for human convenience.
>
> Why the split: `.claude/` and `templates/` get copied to target
> projects by `setup-gan-harness-skills`. Target projects do not have
> `docs/maintainer/`, so any runtime ref to this file would be a broken
> link on every setup. See `CLAUDE.md` § Footgun rules.

## Why this exists

Agents drift toward easy paths: defer hard decisions, fill ambiguities
silently, rationalize shortcuts. Without explicit constraints, they take
soft escapes that look reasonable in isolation but compound into long-term
debt. Examples we have already removed by enforcement:

- A `deferred` resolution_kind that let planners punt questions to next batch
- A `WARN` / `STRICT` lint mode that let "almost passing" pass
- A `tech_debt` field that let "we'll fix it later" become written law
- An `intake.md` artefact that lived without a downstream consumer

Each of those was a soft escape that an agent (or the human writing the
agent) talked themselves into. This memo describes the constraint shape
every worker prompt has settled on so future maintainers can apply the
same shape consistently. Per-agent customization sits on top.

## What "worker prompt" means

In scope (each prompt inlines the constraint sections itself):

- Every `.claude/agents/*.md` (subagent definitions)
- Every `.claude/skills/*-workflow/SKILL.md` (orchestration skills)
- Every `.claude/skills/*-handbook/SKILL.md` only if the skill drives
  decisions (not pure routing index)
- Future stack skills' SKILL.md when they implement non-trivial behaviour

Out of scope (do not carry the constraint sections):

- `.claude/commands/*.md` (thin routers — they invoke skills, do not work)
- `.claude/skills/*/references/*.md` (loaded by agents but don't drive
  behaviour themselves)
- Pure index/routing skills (e.g., `planner-handbook/SKILL.md` that only
  lists "when to read which reference")
- Schema / data files (`.claude/schemas/*.json`)

> For the definition of skill tiers (workflow / agent handbook /
> approach handbook / stack skill) and which tier a new doctrine
> belongs to, see `docs/maintainer/design/skill-architecture.md`.

## The three mandatory sections

Each worker prompt has these three, in this order, at the top of the
prompt body (after frontmatter, before the agent's specific Process /
Phases section). The prompt itself is the SSoT — this memo just records
the shape so new prompts can match it.

### 1. Mandatory before starting

```markdown
## Mandatory before starting

Before producing any output (writing files, choosing options, dispatching
subagents), surface your assumptions explicitly:

ASSUMPTIONS I'M MAKING:
1. <assumption — be specific>
2. <assumption — be specific>
→ Correct me now or I'll proceed with these.

Do not silently fill in ambiguous requirements. The entire purpose of this
stage is to surface misunderstandings before they crystallize. Assumptions
are the most dangerous form of misunderstanding because they look like
facts.
```

### 2. Common Rationalizations

Per-agent table. 5 ± 2 rows. Each row identifies (a) the easy excuse this
role is most likely to slip into, (b) why it's actually wrong.

```markdown
## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "<easy excuse>" | <reality> |
```

A cross-agent overview lives in § "Per-agent rationalization catalogue"
below. The catalogue is for human convenience only — when an agent's
prompt and the catalogue disagree, the prompt wins (it is what runs).
Update the catalogue if you want the overview to stay current; do not
update the prompt FROM the catalogue.

### 3. Anti-patterns (carry-over)

If the prompt already has an Anti-patterns / Red-flags section listing
concrete behaviour patterns to avoid, keep it. Rationalizations capture
*self-deception*; anti-patterns capture *behaviour shape*. Both stay.

## Universal rules (apply to every worker prompt)

These are the cross-agent constraints. Each worker prompt inlines
whichever rules apply to its role — phrased in its own voice, with its
own mechanism names. Worker prompts do NOT link back to this section
(target projects have no `docs/maintainer/`; cross-link would break on
every setup). This list is the maintainer's overview of what should be
inlined where.

The rules:

1. **No `deferred` punt.** Open questions resolve in the current batch or
   batch scope is wrong. There is no "we'll figure it out later".

2. **No silent inference.** If a fact isn't established (in input docs,
   in code you can read, in user statement), don't fill it from training
   priors. Surface as ambiguity or assumption.

3. **No PASS_WITH_TODO / WARN / SOFT_ENFORCE.** Lint and validation are
   PASS/FAIL only. No middle states. No "warn but proceed".

4. **No outsourcing back without recommendation.** When you surface an
   ambiguity, also state your recommended resolution + why. Humans
   approve / edit / escalate; they don't decide blind.

5. **Lint is the contract.** When automated checks fight you, fix the
   source design. Never patch around the check.

6. **Vertical slices, not horizontal phases.** Features cross all
   relevant layers end-to-end (UI → API → service → DB if full-stack),
   never split by tech layer.

7. **No fabricated provenance.** If the input was "user dump", don't
   restructure into "user said X" with X you invented. Quote what
   actually existed; surface the rest as your interpretation under
   ASSUMPTIONS.

## Per-agent rationalization catalogue

Cross-agent overview. The agent's own prompt is the SSoT for its table;
this catalogue is for maintainers who want to scan all agents at once.
When an agent prompt and this catalogue disagree, the prompt wins.

### planner

| Rationalization | Reality |
|---|---|
| "This open_question can be deferred to next batch" | No deferred kind. Resolve in this batch or escalate to /prd to re-scope. |
| "This is a minor design choice, not architectural" | Apply three-test gate (hard-to-reverse + surprising + real-trade-off). All three pass = ADR. Skipping the test is the rationalization. |
| "Two reasonable options, I'll just pick A" | Outsourcing the thinking. Real trade-off → open_question with your recommendation. Human decides at /plan Phase 2 walk. |
| "This feature is too big, I'll split into phase-1-DB / phase-2-API" | Horizontal phasing forbidden. Split into multiple vertical slices, each end-to-end. |
| "Lint complained but the design is fine, I'll work around" | Lint is the contract. Fix source design, never patch around. If lint repeatedly fights you, the design is wrong, not the lint. |

### codebase-fact-finder

| Rationalization | Reality |
|---|---|
| "Didn't see exact match but inferred from naming" | Don't infer. Report verifiable facts; flag what you couldn't establish. |
| "Question is unclear, generous interpretation is fine" | No generative interpretation. Bounce back to MAIN if ambiguous. |
| "This file is huge, I'll sample a few representative bits" | No sampling. Read the relevant section completely or state explicitly which range you covered. |

### plan-workflow

| Rationalization | Reality |
|---|---|
| "Phase 2 user looks tired, bulk-approve is enough" | Per-Q walk is contract. Each open_question and each ADR walked individually. No batch-shortcut. |
| "Three-script trio: 2 PASS, 1 FAIL — close enough" | All three PASS or none. Any FAIL → planner re-fixes. No "two out of three". |
| "After 3 escalates the user is frustrated, just push through" | 3 escalates = batch scope is genuinely wrong. Abort to /prd, don't grind. |

### stack-skill-creator

| Rationalization | Reality |
|---|---|
| "User didn't specify exact stack variant, I'll pick a common one" | Don't pick. Grill until stack boundary, version, test runner are explicit. |
| "Barrel pattern is standard, I'll copy mainstream" | Each stack has its own idiom. Verify the target stack's actual convention before writing. |
| "I'm not familiar with this stack, I'll write a reasonable skeleton" | Unfamiliar = stop. Writing a "reasonable skeleton" hands the user wrong defaults disguised as right ones. |

### prd-workflow (grill happens in MAIN session, not a subagent)

The whole /prd flow is one prompt — grill discipline + orchestration share one rationalization table.

| Rationalization | Reality |
|---|---|
| "User probably means X" | Don't infer intent. Ask. Reframe vague targets ("make it secure" → measurable bullets) per `prd-workflow/references/grill-protocol.md`. |
| "I have enough to write the spec now" | If any branch of the design tree is unresolved, you don't. Walk every branch. |
| "User said 'just figure it out for me' — I'll fill in" | Don't. /prd's entire purpose is surfacing assumptions before code. Filling silently is the worst mode. |
| "User's dump is contradictory, I'll resolve by picking the later statement" | Don't auto-resolve. Surface: "You said A on line 3 and not-A on line 7 — which?" |
| "I'll save the user time by skipping obvious questions" | Obvious to you, not to them. Skipping bakes in your assumptions silently. Ask. |
| "Skip codebase research, just go from grill to /plan" | No. /plan has no research phase; that work happens here. Skipping leaves planner blind. |
| "Fact-finder failed on Q-03, just skip that finding" | Surface the failure. research.md is incomplete; user decides skip vs retry vs abort. |
| "User approved at checkpoint, even though one R is still vague" | Re-grill the vague R. Approve means all R are concrete with measurable criteria. |
| "Spawn a subagent to do the grilling so MAIN stays clean" | No. Grill is interactive multi-turn dialogue and runs in MAIN. Subagents are for fresh-context bulk work (codebase-fact-finder, planner). |

### generator

| Rationalization | Reality |
|---|---|
| "AC doesn't say so but I'll add this safety check" | Implement exactly what AC says. No silent extras. |
| "This edge case is unlikely, I'll skip it" | AC defines the cases. Untested edges = not implemented. |
| "I'll add a try/catch wrapper just in case" | Errors are AC-specified (kind: error). Don't invent error handling not in spec. |
| "First 80% works, ship it and refine in round 2" | First-80% bias is a named failure mode (Anthropic Verification Specialist v2.1.91). All AC pass before commit, not just the easy ones. |
| "This spec is bigger than I thought, I'll narrow scope" | Under-scoping is a documented failure mode (Anthropic V2 harness post). The planner expanded scope deliberately. Do not narrow without an open_question + escalation. |
| "I'll write a placeholder/stub for this and TODO-comment the rest" | Stubs and `// TODO` are not done. If you can't implement it now, that's a round-3 BLOCKED, not a self-declared PASS. |

### evaluator

| Rationalization | Reality |
|---|---|
| "Test fails on a typo but the spirit is right" | Test fails = AC fails. Spirit is not the contract. |
| "Minor issue, not worth blocking the round" | P1 fail = block. Trust the priorities; don't second-guess them. |
| "Code looks reasonable, I'll PASS even though one anchor is missing" | `eval_anchors` is the contract. Missing anchor = FAIL. |
| "I'm not sure, I'll mark it PARTIAL" | No PARTIAL. PASS or FAIL. Anthropic's own Verification Specialist removed PARTIAL in v2.1.94 — it's a hedge that masks weak verdicts. DEFERRED is reserved for "open question still open", not "I'm uncertain". |
| "Tests passed, I'll PASS without driving the app" | Tests cover what they cover. UI features need the L5 path actually exercised. "Passed tests but didn't probe" = FAIL. |
| "All my probes hit the happy path — must be solid" | Verification avoidance. Each AC needs ≥1 adversarial probe (boundary / concurrency / idempotency / orphan). Happy-path-only = FAIL even if happy path is green. |
| "The generator's commit message says it handles X" | Generator's words are not evidence. Trace shows what was done; git diff shows what changed; the test output shows what works. |

### harness-loop

| Rationalization | Reality |
|---|---|
| "Round 3 evaluator FAIL is close enough, mark as passed" | No. Three rounds is the budget; FAIL after R3 → status `deferred`. /finalize handles. |
| "Generator hit an error, I'll re-spawn without counting the round" | No. Every spawn counts. Three rounds total. |
| "Evaluator says DEFERRED but I disagree, I'll override" | No. Verdict is the evaluator's call. The harness records and moves on. |
| "This feature's dependency is `deferred`, but I think it could still work, let me try" | No. `blocked-by-ancestor` cascades automatically. Override = ignoring the open question that caused the upstream defer. |
| "I'll skip writing the row to progress.tsv since the trace already records this" | No. progress.tsv is the human-facing summary; trace is auditable detail. Both required. |

### setup-gan-harness-skills / finalize-workflow / batch-gc (T9 / T12 future)

| Rationalization | Reality |
|---|---|
| "User didn't choose, sane default is fine" | For load-bearing decisions (stack, layout), ask. For purely cosmetic, default may be fine but say which you picked. |
| "This file might be needed later, I'll create a stub now" | Lazy creation. No empty stubs. Producer creates on first real content. |
| "User's edits to the project's master docs (`README.md`, `CONTEXT.md`) look wrong" | Not your call to revise. They own per-project decisions once setup hands off. |

## Updating this memo

Triggers for update:

- New worker prompt added (new agent / new workflow skill) → optionally
  add its rationalization table to § Per-agent rationalization catalogue
  for cross-agent overview
- New drift pattern observed across multiple agents → optionally add to
  § Universal rules; the binding step is updating the affected prompts
- New soft escape ratified by accident (e.g., a new `deferred` analogue
  slipped in) → add to § Why this exists as a cautionary case + remove
  the escape from schema/lint

When updating:

1. Edit the affected agent prompt(s) directly — that is what runs
2. Optionally update this memo if you want the cross-agent overview to
   stay current. The reverse direction (memo first, then sync) is wrong;
   the prompt is the SSoT.
3. Note the change rationale in commit message; design memos benefit
   from the why being recorded.

## What this file is NOT

- A runtime SSoT. Nothing under `.claude/` or `templates/` references
  this file, and nothing should — target projects do not have
  `docs/maintainer/`. Cross-link = broken link on every setup.
- A skill (no `name` / `description` frontmatter — it is read by
  maintainers, not auto-invoked)
- A schema (no machine validation)
- An ADR (no decision record format — though decisions to add new
  universal rules MAY also produce an ADR if hard-to-reverse)
- The agent's full instruction. Per-agent prompts have their own
  Process / Phases / Outputs sections, plus their own copy of whichever
  constraint sections apply to that role.
