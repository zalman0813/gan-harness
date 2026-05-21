---
name: planner-handbook
description: Methodology handbook for the planner agent — grill protocol, archetype selection, per-sprint User story + Success (user POV) bullet authoring, Cross-cutting H3 whitelist, spec.md authoring patterns. The planner agent must invoke this skill via the Skill tool at the start of /init, before grilling or producing/revising spec.md — registered in the agent skills frontmatter but NOT auto-injected, so load it first.
disable-model-invocation: false
---

# planner-handbook

The planner agent's identity and principles live in `.claude/agents/planner.md`.
This handbook holds the **methodology**: grill protocol, archetype templates,
per-sprint User story + Success (user POV) authoring, and authoring heuristics.

## Grill protocol

Default behaviour at `/init` is grill (skipped only with `--no-grill`). The
goal is to extract enough context that downstream agents don't need you again.

### Five questions you must resolve before drafting spec.md

1. **What does the user observably do once this epic is shipped?**
   - You're looking for 3-7 user-observable success outcomes.
   - Bad: "the system is fast" / "the code is clean"
   - Good: "a developer can install the CLI and run `kvstore get foo.bar`
     and see the value within 60 seconds of install"

2. **What's the tech stack?**
   - Frontend / Backend / Database / Infra / Test runner — name each.
   - Each named layer must correspond to a stack skill at
     `.claude/skills/<name>/`. If the stack skill doesn't exist, ask the
     user to create one first via `stack-skill-creator`.
   - Common gotchas: "Python" is not a stack — `python-fastapi` is. Be
     specific.

3. **What is explicitly out of scope?**
   - Capture as `## Cross-cutting constraints > Non-goals`. This list is
     the boundary the generator respects.
   - Common non-goals: GUI, network sync, multi-user, admin dashboard,
     internationalisation, accessibility (only when truly OOS — be honest).

4. **What archetype fits?**
   - frontend / backend / library / cli / data-pipeline / hybrid
   - Drives the 4 evaluation criteria (see below).
   - When mixed (e.g., a CLI that talks to an API), pick the **dominant**
     surface or use `hybrid`.

5. **Brownfield or greenfield?**
   - Brownfield = modifies existing codebase → flag in grill so MAIN
     session sets up per-sprint research gate at /loop start.
   - Greenfield = builds new app from zero → no research gate.
   - You do NOT author research questions; the MAIN session drafts them
     at /loop start based on spec.md sprint plan + intent. Your job at
     /init is only to flag brownfield vs greenfield so /loop knows
     whether to run the research gate.

6. **Per-sprint user story + 3-5 Success (user POV) bullets**
   - For each sprint you propose, draft a Cohn-pattern user story
     (`As a <role>, I can <action> so that <outcome>.`) and 3-5
     observable behaviour bullets in **user language only** — no
     endpoint paths, schema keys, ETag, data-testid, return codes.
   - These become the anchor source for generator's verification_plan
     in /loop. Vague bullets → vague contract → over-interpretation.
   - Bad: "User can reset password" (one bullet, too coarse)
   - Good: 4 bullets covering happy path + invalid email handled +
     expired link rejected + reset confirmation visible.

### When to stop grilling

When a senior product engineer reviewing your draft spec.md would not say
"wait, what about X?" — and your archetype + 4 criteria are clearly aligned.
Default budget: 3-6 grill questions. More than 8 = the user's intent is too
vague; consider an `abort` recommendation.

## Archetype 4-criteria templates

Pick one matching `## Archetype`. Reword for the epic but keep exactly 4.

### frontend
1. **Design quality** — coherent visual identity, mood, distinct
2. **Originality** — custom decisions vs library defaults vs AI slop
3. **Craft** — typography, spacing, contrast, technical fundamentals
4. **Functionality** — usability independent of aesthetics

### backend
1. **API design quality** — RESTful or RPC consistency, naming, versioning, documentation
2. **Robustness** — error handling, edge cases, idempotency, retry semantics
3. **Craft** — code structure, type safety, observability, test coverage
4. **Functionality** — endpoints work end-to-end, contracts honored, integrations correct

### library
1. **Interface design** — minimal surface, deep modules, pit-of-success defaults
2. **Originality** — thoughtful defaults vs scaffolded noise
3. **Craft** — API stability, error types, docstring completeness
4. **Functionality** — examples work, edge cases handled, semantic versioning honored

### cli
1. **UX quality** — helpful errors, consistent flag style, --help readability
2. **Robustness** — works in pipelines, signal handling, exit codes
3. **Craft** — code structure, subcommand organization, test coverage
4. **Functionality** — subcommands work, end-to-end flows reliable

### data-pipeline
1. **Correctness** — output invariants hold, schema match, deterministic
2. **Robustness** — idempotency, restart safety, error budget, observable
3. **Craft** — modular stages, structured logging, lineage tracking
4. **Functionality** — produces expected output for known input fixtures

### hybrid
- Pick 4 by mixing — typically: 1 from dominant archetype + 1 from secondary
  + 2 cross-cutting (Robustness + Craft are nearly always universal).
- Document the mix in `## Cross-cutting constraints` with rationale.

## ADRs are not yours

You do NOT author ADRs. Generator is the sole ADR author at IMPLEMENT
time (see `.claude/agents/generator.md` > `## ADR triggers during
implementation`). If a decision surfaces during grill that feels
architecturally weighty, treat it as a Cross-cutting `### Domain terms`
glossary entry (terminology) or as a Sprint plan user story
(capability) — not as an ADR proposal.

## Spec.md authoring heuristics

### Vision (2-4 sentences)
- Sentence 1: what the artefact is.
- Sentence 2: who uses it / why now.
- Sentences 3-4 (optional): notable constraint or differentiator.

### Features (5-15 typical, hard upper bound 25)
- Each feature is a `### F{NN} — <name>` block.
- Feature names: noun phrases describing user-facing capabilities. Phase
  markers (backend, api layer, scaffolding) are rejected by lint L02.
- User stories: Cohn pattern, 2-5 stories per feature.
- Data model: only when archetype is `backend | data-pipeline | hybrid` and
  the feature touches persistent state. Lightweight: entity name + key
  fields. NOT full SQL DDL. NOT exhaustive validation rules.

### Sprint plan (3-12 sprints typical)
- Each sprint delivers ≥1 feature; covers ≥1 user-observable behaviour.
- Each sprint MUST have, in this exact bullet order:
  - `Delivers:` features list
  - `Depends on:` (none) or S{NN}[, S{NN}...] (only when there's a real
    dependency; parallelisable sprints declare `(none)`)
  - `User story:` Cohn pattern — `As a <role>, I can <action> so that
    <outcome>.`
  - `Success (user POV):` 3-5 sub-bullets each starting with `user` or
    `system`, in user language only — no technical tokens (endpoint
    paths, schema keys, `data-testid`, `ETag`, status codes)
  - `Smoke check:` one sentence with user-observable verb prefix
- Sprint that touches a single layer needs explicit `(pure-frontend)` /
  `(pure-backend)` / `(pure-lib)` / `(pure-cli)` / `(pure-data)` tag.
- These bullets are the **anchor source** for generator's
  verification_plan in /loop. Vague POV bullets → vague contract →
  over-interpretation. Granularity here directly determines /loop's
  output quality.

### Cross-cutting constraints (H3 whitelist — lint L10)
- Allowed H3 sub-sections (exhaustive): `### Non-goals`,
  `### Performance budget`, `### Design language`, `### Compliance`,
  `### Domain terms`. Any other H3 is a technical carve-out and
  rejected by L10.
- `### Non-goals`: explicit user-declared exclusions (no internal
  inferences). User said "we won't do X" → goes here.
- `### Performance budget`: user-declared performance requirement.
- `### Design language`: user-declared visual / UX direction.
- `### Compliance`: user-declared regulatory or policy constraint.
- `### Domain terms`: terminology mapping. Format each entry as
  `- **<term>** — <one-line definition>` with em-dash separator
  (continuation lines allowed with 2-space indent). Heading must be
  exactly `### Domain terms` (no parenthetical suffix). Terms here
  become permanent `CONTEXT.md` ## Language entries at /finalize.
- **Do NOT** create sections like `### Session-history phasing`,
  `### CONFORMANCE-K divergence`, `### Implementation staging`. These
  are technical carve-outs that belong in /loop contract negotiation,
  not in spec.md.

### Overall success criteria (3-7 entries)
- Behavioral, end-to-end, user-observable.
- At least one entry must walk a complete user flow (lint L06).
- Mechanical statements ("all tests pass", "lint clean") are NOT success
  criteria — they're floor expectations, not the goal.

## Common pitfalls

**Spec bloat.** A 30-page spec for one epic = the epic is too big. Split
into multiple epics that share CONTEXT.md vocabulary.

**Re-prescribing implementation.** "Use FastAPI's `Depends()` for auth" is
implementation. The contract negotiation in `/loop` is where this kind of
detail emerges.

**Inventing CONTEXT.md terms.** If CONTEXT.md says `User` but you write
`Account`, you've forked vocabulary. Use existing terms verbatim.

**Phase-named features.** "Backend setup" / "Phase 1: scaffolding" / "API
layer". Lint L02 rejects these. Vertical slice from day one.

**Sprint plan as horizontal phases.** Sprint 1 = backend, Sprint 2 =
frontend. This violates lint L05 (single-layer without pure-* tag) and is
the #1 anti-pattern in long-running agentic builds.
