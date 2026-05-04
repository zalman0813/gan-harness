# Context

The domain ubiquitous language for this project. AI agents read this before exploring code so terms used in output (PRDs, plans, tests, ADRs, code identifiers) stay consistent with the project's actual vocabulary.

The codebase is the source of truth for code (signatures, tests, runtime behaviour). This file fills what code cannot express: what domain experts mean, which words collapse to one canonical, which words mean different things, and how concepts relate.

How to consume this file is described in each agent's own prompt — not here. This file is pure substrate.

## Language

**Vertical slice**:
A feature spanning every layer the requirement implies (UI → API → service → DB if full-stack), delivering end-to-end user value in one batch unit.
_Avoid_: phase, horizontal slice, layer-only feature

**Feature**:
A vertical-slice unit listed in `feature-list.json` with its own ID, ACs, `depends_on`, and (optionally) `decision_refs`.
_Avoid_: task, epic, story (story is reserved for PRD user stories within a feature)

**AC** (acceptance criterion):
A binary, testable claim about a feature's completion, scoped to one of L1 (compile/lint), L2 (unit), L3 (integration), L4 (contract), L5 (smoke/e2e).
_Avoid_: requirement, success criterion, definition-of-done

**ADR** (architecture decision record):
A MADR-format markdown file under `docs/adr/` recording one architectural decision that passed the three-test gate (hard-to-reverse + surprising + real-trade-off). Frontmatter `status` flows proposed → accepted → superseded; body is immutable from creation.
_Avoid_: design doc, RFC, spec

**Open question**:
A spec-level uncertainty in a feature with planner's recommended `resolution`, awaiting user review at /plan Phase 2 per-Q walk. `resolution_kind ∈ {feature_local, architectural, glossary}` routes its sink at /finalize. No deferral — every question resolves in-batch or batch scope is wrong (escalate to re-grill at /prd).
_Avoid_: TODO, risk, deferred

**Stack skill**:
A pluggable skill at `.claude/skills/<stack>/` providing language- / framework-specific idioms (test runner, barrel patterns, lint commands). Consumed by core skills; core never modifies stack skill.
_Avoid_: framework skill, language skill, plugin

**Batch**:
The set of features delivered together by one /prd → /plan → /execution-loop → /finalize cycle, materialised as `specs/_batch/` while live and archived to `specs/completed/<slug>/` at /finalize.
_Avoid_: sprint, iteration, milestone

## Relationships

- A **Feature** is always a **Vertical slice**
- A **Feature** has many **AC**s, each scoped to L1–L5
- A **Feature** may reference zero or more accepted **ADR**s via `decision_refs`
- An **ADR** lifecycle: proposed → accepted → superseded; only accepted ADRs are referenced from features
- An **Open question** has exactly one `resolution_kind` that routes its sink at /finalize
- A **Stack skill** is consumed by core skills; the dependency never reverses
- A **Batch** holds many **Feature**s and zero or more proposed **ADR**s

## Example dialogue

> **User**: "I want to add password reset."
>
> **Planner**: "That's one **vertical slice** — UI form → API token endpoint → service for token validation → DB for token storage. I see one **open question** for you: token storage strategy is hard-to-reverse and a real trade-off (Redis vs DB column vs JWT), so it passes the three-test gate as an **ADR** candidate. My recommendation is Redis with 15-min TTL because it gives automatic expiry without DB schema change. Approve, edit, or escalate?"
>
> **User**: "What if the email service is down when we try to send the reset link?"
>
> **Planner**: "Good — that's an **AC** of kind=error in the L3 integration band: 'GIVEN email service unreachable WHEN /reset is called THEN return 503 with retry-after header'. It's not an ADR (the decision is feature-local, not architectural), so it goes into the feature's AC list directly."
>
> **User**: "We also have a 'customer' concept — is that the same as User?"
>
> **Planner**: "That's an **open question** with `resolution_kind: glossary` — I don't see Customer defined in `CONTEXT.md`. My recommendation: distinct concepts. Customer = the human owning the account; User = an authentication identity (a Customer can have multiple Users for shared corporate accounts). Approve / edit / escalate?"
