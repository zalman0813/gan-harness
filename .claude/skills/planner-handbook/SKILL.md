---
name: planner-handbook
description: Doctrine the gan-harness planner agent operates by — vertical-slice rule (Horthy + anti-horizontal), three-script self-verify discipline (plan_validator + lift_capabilities + plan_lint, all PASS/FAIL), and ADR proposed→accepted lifecycle (MADR + supersedes retroactive backfill). For deep-module design methodology (Ousterhout/Pocock), see the separate `deep-module-handbook` approach skill which planner also auto-loads via frontmatter `skills:`. Loaded by the planner subagent at startup via frontmatter `skills:`. Make sure to use this whenever designing vertical-slice features, planning batch decomposition, writing/reviewing feature-list.json, or proposing ADRs.
---

# Planner Handbook

The planner agent's operating doctrine. This is the theory and discipline the planner applies in Phase 2 of `/plan`. Each reference is loaded on demand when the planner reaches the relevant decision point.

## When the planner consults each reference

| Decision point in planner's work | Read |
|---|---|
| Deciding module boundaries / interface vs implementation split | [`deep-module-handbook` skill](../deep-module-handbook/SKILL.md) (foundation.md + planner-slice.md) |
| Decomposing batch into features / checking each feature is end-to-end | [references/vertical-slice.md](references/vertical-slice.md) |
| Running the three-script trio after writing feature-list.json / interpreting lint failures | [references/self-verify-loop.md](references/self-verify-loop.md) |
| Identifying architectural decisions / writing new docs/adr/NNNN-*.md | [references/adr-lifecycle.md](references/adr-lifecycle.md) |

## Loading order

The planner reads `vertical-slice.md` and the `deep-module-handbook` skill's `foundation.md` + `planner-slice.md` **before designing** (these shape the design). It reads `self-verify-loop.md` **before running the trio** (to interpret violations). It reads `adr-lifecycle.md` **only when** an architectural decision surfaces.

Avoid loading all references upfront — that defeats progressive disclosure and burns context budget.

## What's NOT here

- Phase orchestration (when to spawn fact-finder, when to checkpoint) — that's `plan-workflow/SKILL.md`'s job
- Stack-specific idioms (barrel patterns, test-runner commands) — those live in the active stack skill's references
- Schema details — those live in `.claude/schemas/feature-list.schema.json`
- Deep-module doctrine — moved to its own approach handbook (`deep-module-handbook` skill) so `generator` and `evaluator` agents can also consume it.
