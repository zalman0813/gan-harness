# Context

The domain ubiquitous language for this project. AI agents read this before exploring code so terms used in output (specs, contracts, ADRs, code identifiers) stay consistent with the project's actual vocabulary.

The codebase is the source of truth for code (signatures, tests, runtime behaviour). This file fills what code cannot express: what domain experts mean, which words collapse to one canonical, which words mean different things, and how concepts relate.

How to consume this file is described in each agent's own prompt — not here. This file is pure substrate.

## Language

**Vertical slice**:
A unit of work spanning every layer the requirement implies (UI → API → service → DB if full-stack), delivering end-to-end user-observable value. Sprints in `## Sprint plan` are vertical slices; features described under `## Features` are vertical-slice user-facing capabilities.
_Avoid_: phase, horizontal slice, layer-only feature

**Epic**:
The set of work delivered together by one /init → /loop → /finalize cycle, materialised as `specs/_epic/` while live and archived to `specs/epics/<slug>/` at /finalize. Replaces the v1 "Batch" term.
_Avoid_: batch, sprint, iteration, milestone, project

**Spec**:
The single immutable artefact at `specs/_epic/spec.md` produced by /init's planner agent. Contains vision + features + sprint plan + 4 archetype evaluation criteria + cross-cutting + overall success + references. Stays high-level (no granular AC, no implementation details). Schema at `.claude/schemas/spec.schema.md`.
_Avoid_: PRD, requirements doc, design doc

**Feature**:
A user-facing capability listed under `## Features` in spec.md as `### F{NN} — <name>`. Has user stories (Cohn pattern) and optional data model. Multiple features may live in one sprint. NOT a synonym for sprint.
_Avoid_: task, story (story is reserved for Cohn-pattern user stories within a feature)

**Sprint**:
An implementation slice listed under `## Sprint plan` in spec.md as `### S{NN} — <name>`. Delivers ≥1 feature; has Depends-on (sequencing) and a Smoke check (one-line user-observable verb). Sprint contracts are negotiated per-sprint inside /loop. Sprints may legitimately be single-layer (UI-only redesign, etc.) when explicitly tagged `(pure-frontend)`/`(pure-backend)`/`(pure-lib)`/`(pure-cli)`/`(pure-data)`.
_Avoid_: phase, milestone, iteration

**Sprint contract**:
A per-sprint testable agreement negotiated between generator and evaluator at the start of each sprint inside /loop. Contains done_looks_like[], verification_plan[], criterion_mapping (to the 4 spec.md criteria), thresholds. Append-only entries in `specs/_epic/contracts.jsonl` track lifecycle: `agreed` → `completed` → optional `amended`. Schema at `.claude/schemas/contract.schema.json`.
_Avoid_: feature-list, AC bundle, test contract

**Archetype**:
The single-line `## Archetype` field in spec.md naming the kind of artefact this epic produces. One of: `frontend`, `backend`, `library`, `cli`, `data-pipeline`, `hybrid`. Drives the 4 evaluation criteria template (see `.claude/skills/planner-handbook/SKILL.md`).
_Avoid_: project type, app type, kind

**Evaluation criteria**:
The 4-entry rubric in spec.md `## Evaluation criteria`, sourced from the archetype template. Globally shared across the epic; per-sprint contracts reference them via `criterion_mapping`. Reworded but never dropped.
_Avoid_: AC, success metric, KPI

**ADR** (architecture decision record):
A MADR-format markdown file under `docs/adr/` recording one architectural decision that passed the three-test gate (hard-to-reverse + surprising + real-trade-off). Frontmatter `status` flows `proposed` → `accepted` → `superseded`; body is immutable from creation. Authored by **planner** (during /init, for spec-level decisions) OR **generator** (during /loop IMPLEMENT, for impl-time decisions); evaluator does not author but may flag undocumented decisions via `standards_axis.findings[].source: "missing_adr"`. /finalize promotes all `proposed` → `accepted` regardless of author.
_Avoid_: design doc, RFC

**Stack skill**:
A pluggable skill at `.claude/skills/<stack>/` providing language- / framework-specific idioms (test runner, barrel patterns, lint commands, inner-gate scripts). Consumed by core skills; core never modifies stack skill.
_Avoid_: framework skill, language skill, plugin

**Inner gate**:
The pre-commit gate script (`gate_gen_precommit.py` typically) the generator runs before each commit. Runs lint + typecheck + unit + verification step coverage + module ACL. RED at any stage = commit rejected. Stack-specific implementation; conceptually shared.
_Avoid_: pre-commit, CI gate

**Transcript-as-evidence**:
The pattern where evaluator reads the Claude Code runtime-written subagent transcript JSONL slice (captured by SubagentStop hook) as primary evidence of what the generator did, in preference to any generator-authored narrative. The runtime can't be lied to; the narrative can.

## Relationships

- A **Feature** is always a **Vertical slice**
- An **Epic** holds many **Feature**s grouped into many **Sprint**s
- A **Feature** is delivered by exactly one **Sprint**; a **Sprint** delivers ≥1 **Feature**
- An **Epic** has exactly one **Spec** (spec.md); the spec has exactly 4 **Evaluation criteria**
- A **Sprint** has 0..N **Sprint contract** entries in contracts.jsonl over its lifetime (≥1 negotiation rounds + 1 completion + 0..N amendments)
- A **Sprint contract**'s `criterion_mapping` covers all 4 spec.md criteria
- A **Feature** may reference zero or more accepted **ADR**s indirectly via spec.md's `## References`
- An **ADR** lifecycle: proposed → accepted → superseded; only accepted ADRs are referenced from specs
- A **Stack skill** is consumed by core skills; the dependency never reverses

## Example dialogue

> **User**: "I want to add password reset."
>
> **Planner**: "Let me grill: is this a backend service epic or full-stack? The success criterion at the user level — what does the user observably do once shipped?"
>
> **User**: "Full-stack: user clicks 'forgot password', gets an email with a link, clicks it, sets a new password. Stack is React + FastAPI + Postgres."
>
> **Planner**: "OK, archetype = frontend (UI prominent in the user flow). Three sprints: S01 'Forgot-password form + token issuance', S02 'Email delivery + link routing', S03 'Reset confirmation'. Each is a vertical slice. The 4 criteria from frontend archetype: design quality, originality, craft, functionality. I see one **ADR** candidate — token storage strategy is hard-to-reverse and a real trade-off (Redis vs DB column vs JWT), so it passes the three-test gate. Recommendation: Redis with 15-min TTL. Approve, edit, or escalate?"
>
> **User**: "What if the email service is down?"
>
> **Planner**: "That's not a spec-level question — it's a sprint-level testable detail that the **sprint contract** for S02 will cover. Generator and evaluator negotiate it at /loop time: 'verification_plan must include API step that simulates email-service-down and asserts 503 with retry-after'. The spec stays high-level."
>
> **User**: "We also have a 'customer' concept — is that the same as User?"
>
> **Planner**: "I don't see Customer defined in CONTEXT.md. I'll add a glossary entry. Recommendation: distinct concepts. Customer = the human owning the account; User = an authentication identity (a Customer can have multiple Users for shared corporate accounts). Approve / edit / escalate?"
