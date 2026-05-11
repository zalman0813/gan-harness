---
name: adr-lifecycle
description: ADR proposed→accepted lifecycle (MADR + supersedes retroactive backfill). The three-test gate, frontmatter spec, body convention, and lifecycle scripts. Loaded by planner on demand when an architectural decision surfaces during /plan Phase 1.
---

# ADR Lifecycle

The planner creates ADRs as `status: proposed` during /plan Phase 1. /finalize promotes them to `accepted` and retroactively backfills `superseded_by` on any predecessors. Bodies are immutable from creation; only frontmatter `status` and `superseded_by` are ever mutated.

## Three-test gate (apply BEFORE writing any ADR)

All three must be true:

1. **Hard to reverse.** The cost of changing your mind later is meaningful — switching means migrations, rewrites, or sustained pain.
2. **Surprising without context.** A future engineer reading the code will wonder "why did they do it this way?" — the rationale isn't obvious from the code alone.
3. **Result of a real trade-off.** There were genuine alternatives and you picked one for specific reasons.

If any one fails → **do not write an ADR**. Route the concern instead:
- Feature-internal → `spec.business_rules[]` (dies with the feature)
- Needs human input but isn't architectural → `spec.open_questions[]` with `resolution_kind: feature_local` or `glossary`
- "Obvious" given context → no record needed; the code is the record

## What qualifies

- Architectural shape ("monorepo", "event-sourced write model")
- Integration patterns between contexts ("Ordering ↔ Billing via domain events, not synchronous HTTP")
- Technology choices that carry lock-in (DB, message bus, auth provider, deployment target — only ones that take a quarter to swap)
- Boundary and scope decisions ("Customer data owned by Customer context; others reference by ID only")
- Deliberate deviations from the obvious path ("Manual SQL instead of ORM because X")
- Constraints not visible in the code ("No AWS due to compliance", "Response times <200ms per partner contract")
- Rejected alternatives where rejection is non-obvious

## What does NOT qualify

- Library choice for a single feature (unless lock-in)
- Naming conventions, code style, folder layout
- Test strategy that's stack-skill default
- Minor performance trade-offs visible in code comments

## Frontmatter spec

```yaml
---
status: proposed              # proposed | accepted | superseded | deprecated
date: 2026-05-08              # ISO date the ADR was first written
batch: <batch-slug>           # which batch introduced this (provenance; never changed)
supersedes: [0030, 0015]      # explicit predecessors this ADR replaces; ids only (omit if none)
superseded_by: null           # filled retroactively when a future ADR supersedes this (omit at write time)
tags: [auth, session]         # for topic grouping in index.md (omit if none)
---
```

**Required**: `status`, `date`, `batch`. **Optional**: `supersedes`, `superseded_by`, `tags`. Omit entirely if not used; do not write empty arrays just to fill the slot.

## Body — minimal by default

```markdown
# NNNN. <Short title of the decision>

<1-3 sentences: what's the context, what we decided, and why.>
```

That's the default. The value is recording **that** a decision was made and **why** — not in filling out sections.

Optional sections, only when they add genuine value:
- `## Considered Options` — only when rejected alternatives are worth remembering
- `## Consequences` — only when non-obvious downstream effects need to be called out
- `## Context` — only when constraints aren't already implied by title + body

The body is **immutable from creation**. To revise, write a new ADR that supersedes it.

## Lifecycle

### 1. Created (planner during /plan Phase 1)

- Filename: `docs/adr/NNNN-<kebab-slug>.md` (NNNN = next free integer, zero-padded to 4)
- Frontmatter `status: proposed`, `date: <today>`, `batch: <current-slug>`
- Body filled (1-3 sentences default)
- Referenced from `feature-list.json[].decision_refs[]` so dependent features carry the link

### 2. Promoted (at /finalize)

`scripts/finalize_adr.py` runs:
1. For each proposed ADR in current batch → set `status: accepted`.
2. For each promoted ADR's `supersedes:` ids → open the predecessor → set frontmatter `superseded_by: <new_id>`, `status: superseded`. Body untouched.
3. Regen `docs/adr/index.md`.

### 3. Superseded (later batch)

When a later batch's planner writes a new ADR with `supersedes: [NNNN]`, the next /finalize retroactively flips the older ADR's frontmatter only. The body remains the original decision text.

### 4. Deprecated (rare, manual)

If a decision becomes irrelevant without being replaced, set `status: deprecated` manually. No retroactive backfill applies.

## Planner's responsibilities

1. Three-test gate first. Skip ADR if any test fails; route to business_rules or open_questions.
2. Check existing ADRs via `docs/adr/index.md` § Topic chains:
   - Existing accepted + new decision *extends* it → reference via `decision_refs[]`, no new ADR.
   - Existing accepted + new decision *replaces* it → write new ADR with `supersedes: [old_id]`.
   - No existing topic match → write new ADR fresh.
3. Always set `status: proposed` and `batch: <current-batch-slug>` at creation.
4. Reference the new ADR's path in `feature-list.json[].decision_refs[]` for affected features.
5. Default to 1-3 sentence body. Add Considered Options / Consequences only when they earn their place.

## What planner must NOT do

- Promote `proposed` → `accepted` itself — that's /finalize's deterministic script job.
- Edit a previously accepted ADR's body — write a superseding ADR instead.
- Backfill `superseded_by` directly — `finalize_adr.py` does it deterministically.
- Write an ADR that fails the three-test gate — those concerns go to business_rules or open_questions.
- Pad the body with optional sections to "look complete".
