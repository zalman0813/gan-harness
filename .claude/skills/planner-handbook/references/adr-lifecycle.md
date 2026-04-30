# ADR Lifecycle — proposed → accepted

The planner creates ADRs as `status: proposed` during /plan Phase 1. /finalize promotes them to `accepted` and retroactively backfills `superseded_by` on any predecessors. Bodies are immutable from creation; only frontmatter `status` and `superseded_by` are ever mutated.

## When to offer an ADR (three-test gate)

Before writing any ADR, all three of these must be true:

1. **Hard to reverse.** The cost of changing your mind later is meaningful — switching a decision means migrations, rewrites, or sustained pain.
2. **Surprising without context.** A future engineer reading the code will wonder "why did they do it this way?" — the rationale isn't obvious from the code alone.
3. **Result of a real trade-off.** There were genuine alternatives and you picked one for specific reasons.

If any one fails, **do not write an ADR**. Route the concern instead:

- The decision is feature-internal → `spec.business_rules[]` (dies with the feature)
- The decision needs human input but isn't architectural → `spec.open_questions[]` with `resolution_kind: feature_local` or `glossary`
- The decision is "obvious" given context → no record needed; the code is the record

This gate prevents `docs/adr/` from filling with noise that's actually feature-local rules or premature abstractions.

### What qualifies (concrete categories)

- **Architectural shape.** "We're using a monorepo." "The write model is event-sourced; the read model is projected into Postgres."
- **Integration patterns between contexts.** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus, auth provider, deployment target. Not every library — only the ones that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by Customer context; other contexts reference by ID only." Explicit no-s are as valuable as yes-s.
- **Deliberate deviations from the obvious path.** "Manual SQL instead of an ORM because X." Stops the next engineer from "fixing" something deliberate.
- **Constraints not visible in the code.** "Cannot use AWS due to compliance." "Response times must be under 200ms (partner contract)."
- **Rejected alternatives where rejection is non-obvious.** Considered GraphQL, picked REST for subtle reasons → record it, or someone will suggest GraphQL again in six months.

### What does NOT qualify

- Library choice for a single feature (unless lock-in)
- Naming conventions, code style
- Test strategy that's stack-skill default
- Folder layout
- Minor performance trade-offs visible in code comments

## Frontmatter spec

```yaml
---
status: proposed              # proposed | accepted | superseded | deprecated
date: 2026-05-01              # ISO date the ADR was first written
batch: <batch-slug>           # which batch introduced this (provenance; never changed)
supersedes: [0030, 0015]      # explicit predecessors this ADR replaces; ids only (omit if none)
superseded_by: null           # filled retroactively when a future ADR supersedes this (omit at write time)
tags: [auth, session]         # for topic grouping in index.md (omit if none)
---
```

**Required**: `status`, `date`, `batch`.
**Optional**: `supersedes`, `superseded_by`, `tags`. Omit entirely if not used; do not write empty arrays just to fill the slot.

## Body — minimal by default

```markdown
# NNNN. <Short title of the decision>

<1-3 sentences: what's the context, what we decided, and why.>
```

That's the default. The value is recording **that** a decision was made and **why** — not in filling out sections. Most ADRs need nothing more.

### Optional sections

Only include these when they add genuine value. Most ADRs do not need them.

- `## Considered Options` — only when the rejected alternatives are worth remembering (so they're not re-proposed later)
- `## Consequences` — only when non-obvious downstream effects need to be called out
- `## Context` — only when the constraints aren't already implied by the title and one-paragraph body

The body is **immutable from creation**. To revise, write a new ADR that supersedes it.

## Lifecycle

### 1. Created (planner during /plan Phase 1)

- Filename: `docs/adr/NNNN-<kebab-slug>.md` (NNNN = next free integer, zero-padded to 4)
- Frontmatter `status: proposed`, `date: <today>`, `batch: <current-slug>`
- Body filled (1-3 sentences default)
- Referenced from `feature-list.json[].decision_refs[]` so dependent features carry the link

### 2. Promoted (at /finalize)

`scripts/finalize_adr.py` runs:

```
for adr in docs/adr/NNNN-*.md where status == proposed and batch == current_batch:
    set status = accepted

for adr_new in just-promoted:
    for old_id in adr_new.supersedes:
        open docs/adr/{old_id}-*.md
        set frontmatter.superseded_by = adr_new.id   # ONLY allowed body-adjacent mutation
        set frontmatter.status = superseded
        # body untouched

regen docs/adr/index.md
```

### 3. Superseded (later batch)

When a later batch's planner writes a new ADR with `supersedes: [NNNN]`, the next `/finalize` retroactively flips the older ADR's frontmatter only. The body remains the original decision text. Future readers see the chain via the frontmatter graph.

### 4. Deprecated (rare, manual)

If a decision becomes irrelevant without being replaced (e.g., the feature was removed), set `status: deprecated` manually. No retroactive backfill applies.

## Index.md (auto-regenerated by /finalize)

`scripts/finalize_adr.py` rebuilds `docs/adr/index.md` after every batch. It partitions ADRs by status, renders topic chains via `tags`, and renders supersedes pointers. Deterministic — same ADR set → same index.md. No LLM involvement.

## Planner's responsibilities

When the planner identifies a candidate decision in /plan Phase 1:

1. **Three-test gate first.** If any of {hard-to-reverse, surprising-without-context, real-trade-off} fails, do not write an ADR. Route the concern to business_rules or open_questions.
2. **Check existing ADRs** via `docs/adr/index.md` § Topic chains:
   - Existing accepted ADR + new decision *extends* it → reference via `decision_refs[]`, no new ADR
   - Existing accepted ADR + new decision *replaces* it → write new ADR with `supersedes: [old_id]`
   - No existing topic match → write new ADR fresh
3. **Always set** `status: proposed` and `batch: <current-batch-slug>` at creation.
4. **Reference** the new ADR's path in `feature-list.json[].decision_refs[]` for affected features.
5. **Default to 1-3 sentence body.** Add Considered Options / Consequences only when they earn their place.

## What the planner must NOT do

- Promote `proposed` → `accepted` itself — that's /finalize's job (deterministic script).
- Edit a previously accepted ADR's body — write a superseding ADR instead.
- Backfill `superseded_by` directly — `finalize_adr.py` does it deterministically.
- Write an ADR that fails the three-test gate — those concerns go to business_rules or open_questions.
- Pad the body with optional sections to "look complete" — minimal body is the default; sections are added only when valuable.

## Sources

- MADR 4.0 — https://adr.github.io/madr/
- Michael Nygard, *Documenting Architecture Decisions* (2011) — origin of ADR practice
- Pocock skills, ADR-FORMAT.md — three-test gate + minimalist body convention
