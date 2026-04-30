---
name: planner-handbook
description: Doctrine the gan-harness planner agent operates by — deep-module theory (Ousterhout/Pocock + depth_score heuristic, applied during design, not lint-enforced), vertical-slice rule (Horthy + anti-horizontal), three-script self-verify discipline (plan_validator + lift_capabilities + plan_lint, all PASS/FAIL), and ADR proposed→accepted lifecycle (MADR + supersedes retroactive backfill). Loaded by the planner subagent at startup via frontmatter `skills:`. Make sure to use this whenever designing vertical-slice features, deciding module boundaries, evaluating depth, writing/reviewing feature-list.json, or proposing ADRs.
---

# Planner Handbook

The planner agent's operating doctrine. This is the theory and discipline the planner applies in Phase 2 of `/plan`. Each reference is loaded on demand when the planner reaches the relevant decision point.

## When the planner consults each reference

| Decision point in planner's work | Read |
|---|---|
| Deciding module boundaries / interface vs implementation split | [references/deep-module.md](references/deep-module.md) |
| Decomposing batch into features / checking each feature is end-to-end | [references/vertical-slice.md](references/vertical-slice.md) |
| Running the three-script trio after writing feature-list.json / interpreting lint failures | [references/self-verify-loop.md](references/self-verify-loop.md) |
| Identifying architectural decisions / writing new docs/adr/NNNN-*.md | [references/adr-lifecycle.md](references/adr-lifecycle.md) |

## Loading order

The planner reads `vertical-slice.md` and `deep-module.md` **before designing** (these shape the design). It reads `self-verify-loop.md` **before running the trio** (to interpret violations). It reads `adr-lifecycle.md` **only when** an architectural decision surfaces.

Avoid loading all four upfront — that defeats progressive disclosure and burns context budget.

## What's NOT here

- Phase orchestration (when to spawn fact-finder, when to checkpoint) — that's `plan-workflow/SKILL.md`'s job
- Stack-specific idioms (barrel patterns, test-runner commands) — those live in the active stack skill's references
- Schema details — those live in `.claude/schemas/feature-list.schema.json`
