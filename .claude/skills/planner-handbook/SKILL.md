---
name: planner-handbook
description: Methodology handbook for the planner agent — grill protocol, archetype selection, ADR three-test gate application, fact-finder dispatch, spec.md authoring patterns. Auto-loaded by .claude/agents/planner.md. Use whenever the planner is producing or revising a spec.
disable-model-invocation: false
---

# planner-handbook

The planner agent's identity and principles live in `.claude/agents/planner.md`.
This handbook holds the **methodology**: grill protocol, archetype templates,
ADR three-test gate examples, and authoring heuristics.

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
   - Brownfield = modifies existing codebase → fact-finder dispatch needed.
   - Greenfield = builds new app from zero → no fact-finder.
   - This affects the "References" section + whether you spawn fact-finder
     before drafting.

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

## Fact-finder dispatch (brownfield only)

When the epic touches existing code, dispatch fact-finder subagents
**before** drafting spec.md so research informs the draft.

### Pattern

1. Sketch 3-8 questions that, if answered, would let you draft the spec
   without further investigation. Examples:
   - "What is the current shape of the User model? Fields, types, FK?"
   - "Is there an existing auth flow we should integrate with, or is this a
     parallel auth path?"
   - "Which test runners are configured in the current repo?"
2. Spawn fact-finder subagents in parallel, one per question, with explicit
   blindfold (each fact-finder doesn't see your spec draft or other
   questions). Each writes to `specs/_epic/_research/<query-id>.md`.
3. Wait for all to return. Read findings.
4. Draft spec.md, citing findings under `## References`.

### Anti-patterns
- Asking fact-finder to recommend design ("how should we do auth?"). They
  document facts; design is your job.
- Embedding goal-language in the question ("we want to add SSO, find what
  we need"). Pure facts: "What auth modules currently exist?"

## ADR three-test gate

A design choice deserves an ADR only when ALL THREE hold:

1. **Hard to reverse** — flipping the decision later requires touching ≥3
   modules or breaks an external contract. Library choice, persistence
   format, network protocol qualify; variable naming or function
   organisation does not.
2. **Surprising** — relative to defaults / consensus / user expectation. If
   a senior engineer would default to the same choice without thinking,
   it's not ADR-worthy.
3. **Real trade-off** — there's a documented opposing option with concrete
   pros. "We picked PostgreSQL because everyone uses it" fails this gate
   (consensus); "We picked PostgreSQL over SQLite because we expect
   multi-writer load" passes (real trade-off).

### Examples

ADR-worthy:
- Choosing event sourcing over CRUD for the order domain
- Switching from REST to gRPC for the inter-service API
- Adopting hexagonal architecture across the new module

NOT ADR-worthy:
- Naming the module `users` vs `user_management`
- Using FastAPI (the user already said it's the stack)
- Adding a logger (basic ops hygiene)

### Process
- Apply gate. If yes: write `docs/adr/NNNN-<slug>.md` with
  `status: proposed`, MADR format. Refer to `adr-lifecycle` skill for
  schema.
- Cite the ADR in spec.md `## References`.
- Default count for typical epic: 0-1 proposed ADRs. ≥3 ADRs from /init is
  a smell — the spec is becoming an architecture document.

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
- `Smoke check:` one sentence with user-observable verb prefix.
- `Depends on:` for sequencing only when there's a real dependency. Avoid
  artificial sequencing — parallelisable sprints should declare `(none)`.
- Sprint that touches a single layer needs explicit `(pure-frontend)` /
  `(pure-backend)` / `(pure-lib)` / `(pure-cli)` / `(pure-data)` tag.

### Cross-cutting constraints
- Sub-sections allowed: `### Performance budget`, `### Design language`,
  `### Non-goals`, `### Compliance` (when applicable).
- This is where ordinary (non-ADR) decisions live: "use UTC for all
  timestamps", "prefer functional components", "max bundle size 500KB".
- If the epic introduces new domain vocabulary, list it under
  `### Domain terms` (heading exactly that — no parenthetical suffix
  like `(draft)` or `(will merge at /finalize)`; /finalize's
  `merge_domain_terms.py` parser matches the heading literally, and
  spec_lint.py L08 rejects variants). Format every entry as
  `- **<term>** — <one-line definition>` with em-dash separator
  (continuation lines allowed with 2-space indent). Terms here become
  permanent `CONTEXT.md` ## Language entries at /finalize.

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
