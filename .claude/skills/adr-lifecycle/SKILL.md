---
name: adr-lifecycle
description: ADR proposed→accepted lifecycle (MADR + supersedes retroactive backfill). The three-test gate, frontmatter spec, body convention, and lifecycle scripts. Loaded by generator during /loop sprint implementation — generator is the sole ADR author in v3.8. Planner does NOT author ADRs (planner produces a high-level spec without architectural decisions). Evaluator reads ADRs for VERIFY context and may emit `missing_adr` standards-axis findings, but does not author. `block_pretool.py` enforces this: planner and evaluator are denied writes to `docs/adr/*`.
---

# ADR Lifecycle

**Single-author authorship (generator-only)**: in v3.8, ADRs are authored only by the generator (during /loop IMPLEMENT, when an architectural decision passes the three-test gate). Planner does NOT author ADRs — planner produces a high-level spec without architectural decisions, so the spec stays immutable through /loop. Evaluator surfaces gaps via `missing_adr` standards-axis findings but does not author. `block_pretool.py` enforces this: writes to `docs/adr/*` are denied for planner / evaluator / codebase-fact-finder; only generator (and untyped MAIN-session writes for /finalize promotion) are allowed. /finalize promotes all `proposed` ADRs to `accepted`.

ADRs are always created as `status: proposed`. /finalize promotes them to `accepted` and retroactively backfills `superseded_by` on any predecessors. Bodies are immutable from creation; only frontmatter `status` and `superseded_by` are ever mutated.

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

The frontmatter shape below matches the existing
`docs/adr/0001-v3.8-redesign.md` (the seed ADR). Keep the same shape on
every new ADR so the index regen + retroactive supersede script stay
deterministic.

```yaml
---
id: ADR-NNNN                  # zero-padded 4 digits, matches filename prefix
title: <one-line decision>    # human-readable; appears in index.md
status: proposed              # proposed | accepted | superseded | deprecated
proposed_date: 2026-05-08     # ISO date when the ADR was first written
accepted_date: null           # filled at /finalize on promotion (omit at write time)
supersedes: []                # explicit predecessor ids (e.g., ["ADR-0030"]); empty list if none
superseded_by: null           # filled retroactively when a future ADR supersedes this (omit at write time)
authors:                       # who authored this ADR — generator-only in v3.8
  - generator-S{NN}-R{IR}      # for /loop-time decisions (generator agent at specific sprint+round)
  # OR
  - maintainer                 # for human-authored ADRs (seed ADRs, retros)
tags: [auth, session]         # for topic grouping in index.md (omit if none)
epic_slug: <slug>             # which epic introduced this — provenance; never changed. May be omitted on maintainer-authored seed ADRs.
---
```

**Required**: `id`, `title`, `status`, `proposed_date`, `supersedes`, `superseded_by`, `authors`. **Optional**: `accepted_date` (filled by /finalize), `tags`, `epic_slug` (omit on maintainer ADRs).

`authors` is a list to allow co-authorship (rare; e.g., generator drafts, planner extends in a subsequent /init). Single-author ADRs are the common case — write a single-item list.

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

### 1. Created (generator during /loop IMPLEMENT only)

Single authoring entry point in v3.8:

- **Generator at /loop sprint IMPLEMENT**: every architectural decision
  surfaces here, whether spec-level (would have been planner's call in
  prior versions) or impl-time (lazy/eager, sync/async, error model,
  cache placement, etc.). Generator writes the ADR file in the same
  commit as the implementation. `authors: [generator-S{NN}-R{IR}]`.
- `block_pretool.py` denies ADR writes from planner / evaluator /
  codebase-fact-finder.

Generator applies the three-test gate before writing.

- Filename: `docs/adr/NNNN-<kebab-slug>.md` (NNNN = next free integer, zero-padded to 4 — author reads `docs/adr/index.md` or `ls docs/adr/` first to find the next free id)
- Frontmatter: `status: proposed`, `proposed_date: <today>`, `authors: [<role>]`, `epic_slug: <slug>`
- Body filled (1-3 sentences default)
- Referenced from `spec.md` `## References` (planner-authored) OR the sprint commit body's `- ADR-NNNN: ...` bullet (generator-authored)

### 2. Promoted (at /finalize)

`scripts/finalize_adr.py` runs:
1. For each `status: proposed` ADR with `epic_slug` matching the current epic → set `status: accepted`, fill `accepted_date: <today>`.
2. For each promoted ADR's `supersedes:` ids → open the predecessor → set frontmatter `superseded_by: <new_id>`, `status: superseded`. Body untouched.
3. Regen `docs/adr/index.md`.

Promotion is author-agnostic — same script handles planner-authored and generator-authored proposed ADRs the same way.

### 3. Superseded (later epic)

When a later epic's planner OR generator writes a new ADR with `supersedes: [ADR-NNNN]`, the next /finalize retroactively flips the older ADR's frontmatter only. The body remains the original decision text.

### 4. Deprecated (rare, manual)

If a decision becomes irrelevant without being replaced, set `status: deprecated` manually. No retroactive backfill applies.

## Author responsibilities (planner + generator)

1. **Three-test gate first.** Skip ADR if any test fails; route to spec-level Non-goals (planner) or just don't write one (generator).
2. **Check existing ADRs** via `docs/adr/index.md`:
   - Existing accepted + new decision *extends* it → reference the existing ADR id; no new ADR.
   - Existing accepted + new decision *replaces* it → write new ADR with `supersedes: [ADR-NNNN]`.
   - No existing topic match → write new ADR fresh.
3. Always set `status: proposed`, `proposed_date: <today>`, and `authors: [<role>]` at creation.
4. Default to 1-3 sentence body. Add Considered Options / Consequences only when they earn their place.

## What ADR authors must NOT do (both planner and generator)

- **Promote `proposed` → `accepted` themselves** — that's /finalize's deterministic script job.
- **Edit a previously accepted ADR's body** — write a superseding ADR instead.
- **Backfill `superseded_by` directly** — `finalize_adr.py` does it deterministically.
- **Write an ADR that fails the three-test gate** — those concerns go to spec Non-goals (planner) or the commit body (generator).
- **Pad the body with optional sections to "look complete"**.

## Evaluator's role (read-only)

Evaluator does NOT author ADRs. During VERIFY mode it may:
- Read `docs/adr/` + `docs/adr/index.md` as verification context.
- Emit `standards_axis.findings[].source: "missing_adr"` when the diff shows an undocumented decision that passes the three-test gate.

Authorship of the flagged ADR is the next round's generator job. See `.claude/agents/evaluator.md` (Mode 2 VERIFY — the Missing-ADR paragraph) for the detection procedure.
