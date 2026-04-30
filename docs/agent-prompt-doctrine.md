# Agent Prompt Doctrine

The rules every "doing work" prompt in this harness must embed. Living
document — update when a new drift pattern is observed across the harness.

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
agent) talked themselves into. This doctrine is the universal constraint
layer every worker prompt embeds. Per-agent customization sits on top.

## What "worker prompt" means

In scope (must embed all sections below):

- Every `.claude/agents/*.md` (subagent definitions)
- Every `.claude/skills/*-workflow/SKILL.md` (orchestration skills)
- Every `.claude/skills/*-handbook/SKILL.md` only if the skill drives
  decisions (not pure routing index)
- Future stack skills' SKILL.md when they implement non-trivial behaviour

Out of scope (do not need this doctrine):

- `.claude/commands/*.md` (thin routers — they invoke skills, do not work)
- `.claude/skills/*/references/*.md` (loaded by agents but don't drive
  behaviour themselves)
- Pure index/routing skills (e.g., `planner-handbook/SKILL.md` that only
  lists "when to read which reference")
- Schema / data files (`.claude/schemas/*.json`)

## The three mandatory sections

Every worker prompt embeds these three, in this order, at the top of the
prompt body (after frontmatter, before the agent's specific Process /
Phases section):

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

Per-agent canonical tables are catalogued in § "Per-agent rationalization
catalogue" below. When updating a row in an agent's prompt, also update
the catalogue entry — they must stay in sync.

### 3. Anti-patterns (carry-over)

If the prompt already has an Anti-patterns / Red-flags section listing
concrete behaviour patterns to avoid, keep it. Rationalizations capture
*self-deception*; anti-patterns capture *behaviour shape*. Both stay.

## Universal rules (apply to every worker prompt)

These are constraints embedded by reference. Every worker prompt carries
a one-line pointer back here:

> See `docs/agent-prompt-doctrine.md` § Universal rules.

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

Canonical tables. Each agent's own prompt carries its own copy; this
catalogue is the SSoT when they need to be updated.

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

### grill-master

| Rationalization | Reality |
|---|---|
| "User probably means X" | Don't infer intent. Ask. |
| "I have enough to write the spec now" | If any branch of the design tree is unresolved, you don't. Walk every branch. |
| "This decision can wait until /plan figures it out" | No. /plan does not grill. Surface as draft term, AC bullet, constraint, or research-queue question — but resolve before declaring grill done. |
| "User's dump is contradictory, I'll resolve by picking the later statement" | Don't auto-resolve contradictions. Surface them: "You said A on line 3 and not-A on line 7 — which?" |
| "I'll save the user time by skipping obvious questions" | Obvious to you, not to them. Skipping bakes in your assumptions silently. Ask. |

### prd-workflow

| Rationalization | Reality |
|---|---|
| "Skip codebase research, just go from grill to /plan" | No. /plan has no research phase; that work happens here. Skipping leaves planner blind to existing code. |
| "User approved at checkpoint, even though one R is still vague" | Re-grill the vague R, do not proceed. Approve means all R are concrete. |
| "Fact-finder failed on Q-03, just skip that finding" | A failed Q means research.md is incomplete. Surface to user before declaring /prd done. |
| "User said 'just figure it out for me' — I'll fill in the rest" | Don't. /prd's entire purpose is to surface assumptions before code is written. Filling in silently is the worst possible mode. |

### generator (T8 future)

| Rationalization | Reality |
|---|---|
| "AC doesn't say so but I'll add this safety check" | Implement exactly what AC says. No silent extras. |
| "This edge case is unlikely, I'll skip it" | AC defines the cases. Untested edges → not-implemented. |
| "I'll add a try/catch wrapper just in case" | Errors are AC-specified. Don't invent error handling not in spec. |
| "The test passes locally, ship it" | Test passes when L1+L2+L5 from test_contract pass — not when "the one I wrote" passes. |

### evaluator (T8 future)

| Rationalization | Reality |
|---|---|
| "Test fails on a typo but spirit is right" | Test fails = AC fails. Spirit is not the contract. |
| "Minor issue, not worth blocking the round" | P1 fail blocks. Trust the priorities; don't second-guess. |
| "Code looks reasonable, I'll PASS even though one anchor missing" | eval_anchors is the contract. Missing anchor = FAIL. |

### setup-gan-harness-skills / finalize-workflow (T9 / T12 future)

| Rationalization | Reality |
|---|---|
| "User didn't choose, sane default is fine" | For load-bearing decisions (stack, layout), ask. For purely cosmetic, default may be fine but say which you picked. |
| "This file might be needed later, I'll create a stub now" | Lazy creation. No empty stubs. Producer creates on first real content. |
| "User's edits to ARCHITECTURE.md template look wrong" | Not your call to revise. They own per-project invariants once setup hands off. |

## Updating this doctrine

Triggers for update:

- New worker prompt added (new agent / new workflow skill) → add its
  rationalization table to § Per-agent rationalization catalogue
- New drift pattern observed across multiple agents → add to § Universal
  rules + relevant per-agent tables
- New soft escape ratified by accident (e.g., a new `deferred` analogue
  slipped in) → add to § Why this exists as a cautionary case + remove
  the escape from schema/lint

When updating:

1. Edit this file (catalogue + universal rules)
2. Sync the affected agent prompt(s) — copy the row(s) verbatim
3. Note the change rationale in commit message; this file is doctrine,
   so the why matters

## What this file is NOT

- A skill (no `name` / `description` frontmatter — it is loaded by
  reference, not auto-invoked)
- A schema (no machine validation)
- An ADR (no decision record format — though decisions to add new
  universal rules MAY also produce an ADR if hard-to-reverse)
- The agent's full instruction (per-agent prompts have their own
  Process / Phases / Outputs sections; doctrine is the constraint
  layer above)
