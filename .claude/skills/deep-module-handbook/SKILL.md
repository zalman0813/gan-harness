---
name: deep-module-handbook
description: Approach handbook for deep-module design (Ousterhout APOSD; Pocock 2026) — the methodology that generator and evaluator apply at sprint contract negotiation, implementation, and verification time. In v3.8 module-level cognition happens during /loop's sprint contract negotiation between generator+evaluator, NOT at /init planner time (planner produces only high-level spec.md without module_design fields). Loaded by generator.md / evaluator.md frontmatter `skills:`. Use whenever generator is proposing/implementing a module-touching sprint or evaluator is reviewing contract drafts / running QA on commits. Covers information hiding (Parnas), anti-corruption layers (Evans), pass-through smell (Ousterhout), Pocock-calibrated DDD (Ubiquitous Language + Bounded Context + ADR yes; entities/aggregates no), applicability scope (when NOT to apply), the 8-item PASS criteria checklist C1-C8 (named hidden decision, 3-question self-test, deletion test, 1-3 entry-point budget, two-adapter rule for ports, broad-interface definition, interface-is-test-surface, 200-2000 LOC size sanity), 6 red flags with primary-source citations, and the two-adapter quantitative gate for Strategy/DI seams.
---

# Deep Module Handbook

Approach handbook for the deep-module design methodology. This is the
school of thought; the agent-specific application lives in each
consuming agent's slice.

This is an **approach handbook**. It does not define any single agent's
behavior; it defines a methodology that **generator** and **evaluator**
apply at /loop sprint contract negotiation, implementation, and
verification time.

> **Planner does NOT load this handbook.** In v3.8 the planner produces a
> high-level `spec.md` with no `module_design` fields — module-level
> cognition is a sprint-contract concern, not an epic concern. If a
> planner ever needs awareness of deep-module as an *architectural
> stance* (e.g. to write "adopt deep-module discipline" in spec.md's
> `## Cross-cutting constraints`), that's a one-sentence stance, not a
> reason to load this handbook.

## When the agent reaches each decision

| Decision point | Read |
|---|---|
| Always before any deep-module reasoning | [references/foundation.md](references/foundation.md) |
| Generator negotiating a sprint contract / implementing a module / deciding what to test | [references/generator-slice.md](references/generator-slice.md) |
| Evaluator reviewing a contract draft / verifying a committed sprint | [references/evaluator-slice.md](references/evaluator-slice.md) |

## Loading order

Always read `foundation.md` first — it establishes definitions, scope,
applicability, and the red-flag schema both slices reference. Then read
exactly your role's slice. **Do not load the other role's slice** —
that defeats progressive disclosure and leaks the wrong agent's
concerns into your context.

## What this skill IS

- Definitions of deep / shallow / leak / pass-through / ACL / **broad
  interface** (signatures + invariants + ordering + error modes —
  Pocock LANGUAGE.md) with primary-source citations
- Pocock-calibrated DDD: which DDD pieces this approach uses
  (Ubiquitous Language + Bounded Context + ADR) and which it does not
  (entities / value objects / aggregates / domain events)
- Applicability scope: when NOT to apply deep module (DTOs, framework
  conformance, perf hot paths, one-shot scripts)
- **PASS criteria** (foundation.md §3.5) — 8 positive checks an
  evaluator can cite when emitting PASS verdicts (named hidden
  decision, 3-question self-test, deletion test, entry-point budget,
  two-adapter rule, broad-interface, interface-as-test-surface, size
  sanity proxy 200-2000 LOC). Complement to the §5 red flags.
- Red flags with explicit Source / Pattern / Trigger / If-fires-recommend
  / Retirement-criteria fields — negative side of the PASS / FAIL
  vocabulary
- Per-role application slices: how generator and evaluator translate
  principles into their /loop-stage actions (NEGOTIATE → IMPLEMENT for
  generator; NEGOTIATE → VERIFY for evaluator)

## What this skill is NOT

- Each agent's full operating prompt (the `.claude/agents/<agent>.md` files
  themselves; this skill is a peer they load via frontmatter `skills:`)
- Stack-specific module conventions (those are stack skills)
- Workflow orchestration (this skill does not drive any slash command)
- A lint enforcement target. Deep-module heuristics are design-time
  doctrine — Ousterhout's red flags need human judgment, not regex.
  Quantitative proxies (mock count, import-edge presence) MAY be
  lint-enforced separately; qualitative depth assessment stays with
  the generator (proposal time) and evaluator (review time).
- A planner concern. v3.8 planner produces high-level spec.md only;
  module-level cognition is a /loop sprint-contract negotiation
  concern between generator and evaluator.

## Anti-patterns when consuming this skill

- **Loading the other role's slice** — defeats progressive disclosure;
  burns context budget; exposes you to the wrong agent's concerns.
  Generator reads `generator-slice.md` only; evaluator reads
  `evaluator-slice.md` only. Both read `foundation.md` first.
- **Planner loading this skill** — vestigial v1 wiring. v3.8 planner
  writes high-level spec.md only and does not design modules. If
  loaded by mistake, exit and rely on `planner-handbook` instead.
- **Treating red flags as auto-FAIL** — red flags are investigation
  triggers, not verdicts. They surface as contract-amendment proposals
  or findings in `design_review`; evaluator's threshold check decides.
- **Bypassing the source-citation requirement** — if you find yourself
  proposing a new red flag, it must cite a primary source (Ousterhout
  chapter, Parnas section, Fowler bliki, etc.) per
  `foundation.md` § Red flag schema. Folklore flags rot.

## Where the heavy thinking lives

This SKILL.md is a routing index. The substantive doctrine lives in
`references/`. Per-agent slices apply the doctrine in role-specific
ways without duplicating the foundation.
