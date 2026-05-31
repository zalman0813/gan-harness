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
An implementation slice listed under `## Sprint plan` in spec.md as `### S{NN} — <name>`. Delivers ≥1 feature; has 5 mandatory bullets in order: Delivers / Depends on / User story (Cohn pattern) / Success (user POV) 3-5 bullets / Smoke check. Sprint contracts are negotiated per-sprint inside /loop. Sprints may legitimately be single-layer (UI-only redesign, etc.) when explicitly tagged `(pure-frontend)`/`(pure-backend)`/`(pure-lib)`/`(pure-cli)`/`(pure-data)`.
_Avoid_: phase, milestone, iteration

**Success (user POV)**:
A per-sprint 3-5 bullet list in spec.md describing observable behaviour in **user language only** — no technical tokens (endpoint paths, schema keys, `data-testid`, `ETag`, HTTP status codes). Each bullet starts with `user` or `system`. The anchor source for generator's verification_plan inside /loop. spec_lint.py L09 enforces.
_Avoid_: AC, testable criteria, technical assertions

**Sprint contract**:
A per-sprint testable agreement negotiated between generator and evaluator at the start of each sprint inside /loop. Contains done_looks_like[], verification_plan[], criterion_mapping (to the 4 spec.md criteria), thresholds. Append-only entries in `specs/_epic/contracts.jsonl` track lifecycle: `agreed` → `completed` → optional `amended`. Schema at `.claude/schemas/contract.schema.json`.
_Avoid_: feature-list, AC bundle, test contract

**Archetype**:
The single-line `## Archetype` field in spec.md naming the kind of artefact this epic produces. One of: `frontend`, `backend`, `library`, `cli`, `data-pipeline`, `hybrid`. Drives the 4 evaluation criteria template (see `.claude/agents/planner.md` "Archetype → 4-criteria templates").
_Avoid_: project type, app type, kind

**Evaluation criteria**:
The 4-entry rubric in spec.md `## Evaluation criteria`, sourced from the archetype template. Globally shared across the epic; per-sprint contracts reference them via `criterion_mapping`. Reworded but never dropped.
_Avoid_: AC, success metric, KPI

**ADR** (architecture decision record):
A MADR-format markdown file under `docs/adr/` recording one architectural decision that passed the three-test gate (hard-to-reverse + surprising + real-trade-off). Frontmatter `status` flows `proposed` → `accepted` → `superseded`; body is immutable from creation. Authored only by **generator** during /loop IMPLEMENT (v3.8 single-author rule). Planner does NOT author — spec.md stays high-level without architectural decisions. Evaluator does not author but may flag undocumented decisions via `standards_axis.findings[].source: "missing_adr"`. `block_pretool.py` enforces write-deny for planner / evaluator. /finalize promotes all `proposed` → `accepted`.
_Avoid_: design doc, RFC

**Stack skill**:
A pluggable skill at `.claude/skills/<stack>/` providing language- / framework-specific idioms (test runner, barrel patterns, lint commands, inner-gate scripts). Consumed by core skills; core never modifies stack skill.
_Avoid_: framework skill, language skill, plugin

**Inner gate**:
The pre-commit gate script (`gate_gen_precommit.py` typically) the generator runs before each commit. Runs lint + typecheck + unit + verification step coverage + module ACL. RED at any stage = commit rejected. Stack-specific implementation; conceptually shared.
_Avoid_: pre-commit, CI gate

**Transcript-as-evidence**:
The pattern where evaluator reads the Claude Code runtime-written subagent transcript JSONL slice (captured by SubagentStop hook) as primary evidence of what the generator did, in preference to any generator-authored narrative. The runtime can't be lied to; the narrative can.

**Research gate**:
The /loop-start mechanism that drafts per-sprint blindfold codebase questions, runs `question_lint.py` (Q01-Q04 deterministic checks), surfaces to user for approval once, freezes the questions, then dispatches `codebase-fact-finder` subagents per-sprint at sprint kickoff (NOT upfront) so answers reflect the codebase state at that sprint's start. Files: `specs/_epic/_research/S{NN}/_questions.json` (per-sprint frozen questions) + `specs/_epic/_research/S{NN}/<id>.md` (fact-finder output). Replaces /init Phase 1.5.
_Avoid_: fact-finder dispatch (the act, not the gate), planner research

**next_action**:
The evaluator-emitted directive in `_evals/S{NN}-R{IR}.json` (and review.yaml) telling generator what to do on FAIL. Values: `proceed` (PASS only) / `refine` (same approach, address findings) / `restart_sprint` (discard, re-design from scratch) / `escalate_to_user` (stop, write failure report). Generator obeys verbatim — does NOT strategic-decide. Evaluator biases toward `restart_sprint` over `refine` when generator's hill-climb is ineffective.
_Avoid_: strategic decision, pivot decision, generator-decided refine vs pivot

**Anchor**:
A literal substring from spec.md (Success POV bullet) / intent.md / `_research/S{NN}/*.md` that grounds a contract `done_looks_like[]` statement or `verification_plan[].steps[]` substring. `anchor_ledger.py` verifies each anchor against these sources verbatim, producing `_audit/S{NN}/anchor-ledger-R{R}.tsv`. Un-anchored anchors are direct evidence of over-interpretation.
_Avoid_: spec reference (broader), assertion (narrower)

**Divergence diff**:
The post-round report at `_audit/S{NN}/divergence-R{R}.md` listing new identifiers (function names, route literals, class names, schema keys, data-testid values) in the generator's commit that don't appear in any anchor source. Surfaces "what generator invented this round" to maintainer in seconds, not minutes.
_Avoid_: lint findings (different layer), test failures (different category)

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
- A **Sprint** has 3-5 **Success (user POV)** bullets in spec.md; per-sprint contract's `verification_plan[]` anchors back to these bullets
- A **Research gate** runs once at /loop start (question drafting + user approval) plus once per **Sprint** kickoff (fact-finder dispatch)
- An **Anchor** lives in spec.md / intent.md / `_research/S{NN}/`; contract anchors reference these literally, verified post-round by `anchor_ledger.py`
- An evaluator FAIL verdict carries a **next_action** directive; generator obeys verbatim

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
