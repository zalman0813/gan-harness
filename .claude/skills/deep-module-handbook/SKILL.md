---
name: deep-module-handbook
description: Approach handbook for deep-module design (Ousterhout) — the methodology that planner uses when designing module boundaries in feature-list.json, generator uses when implementing modules and writing their tests, and evaluator uses when reviewing whether a module's interface, boundaries, performance, and security meet the depth principle. Loaded by planner.md / generator.md / evaluator.md frontmatter `skills:`. Use whenever an agent is about to design, implement, test, or review module boundaries or interfaces. Covers information hiding (Parnas), anti-corruption layers (Evans), pass-through smell (Ousterhout), Pocock-calibrated DDD (Ubiquitous Language + Bounded Context + ADR yes; entities/aggregates no), red flags with primary-source citations, and applicability scope (when NOT to apply deep module).
---

# Deep Module Handbook

Approach handbook for the deep-module design methodology. This is the
school of thought; the agent-specific application lives in each
consuming agent's slice.

This is an **approach handbook**. It does not define any single agent's
behavior; it defines a methodology that planner / generator / evaluator
each apply at their stage.

## When the agent reaches each decision

| Decision point | Read |
|---|---|
| Always before any deep-module reasoning | [references/foundation.md](references/foundation.md) |
| Designing module boundaries / interface vs implementation split | [references/planner-slice.md](references/planner-slice.md) |
| Implementing a module / deciding what to test | [references/generator-slice.md](references/generator-slice.md) |
| Reviewing a module / verdicting PASS / FAIL / DEFERRED | [references/evaluator-slice.md](references/evaluator-slice.md) |

## Loading order

Always read `foundation.md` first — it establishes definitions, scope,
applicability, and the red-flag schema all slices reference. Then read
exactly your role's slice. **Do not load other roles' slices** — that
defeats progressive disclosure and leaks the wrong agent's concerns
into your context.

## What this skill IS

- Definitions of deep / shallow / leak / pass-through / ACL with
  primary-source citations
- Pocock-calibrated DDD: which DDD pieces this approach uses
  (Ubiquitous Language + Bounded Context + ADR) and which it does not
  (entities / value objects / aggregates / domain events)
- Applicability scope: when NOT to apply deep module (DTOs, framework
  conformance, perf hot paths, one-shot scripts)
- Red flags with explicit Source / Pattern / Trigger / If-fires-recommend
  / Retirement-criteria fields
- Per-role application slices: how each agent translates principles
  into their stage's actions

## What this skill is NOT

- Each agent's full handbook (those are agent handbooks: `planner-handbook`,
  future `generator-handbook`, future `evaluator-handbook`)
- Stack-specific module conventions (those are stack skills)
- Workflow orchestration (this skill does not drive any slash command)
- A lint enforcement target. Deep-module heuristics are design-time
  doctrine — Ousterhout's red flags need human judgment, not regex.
  Quantitative proxies (mock count, import-edge presence) MAY be
  lint-enforced separately; qualitative depth assessment stays with
  the planner / evaluator.

## Anti-patterns when consuming this skill

- **Loading all slices upfront** — defeats progressive disclosure;
  burns context budget; exposes you to the wrong agent's concerns.
  Read only `foundation.md` + your role's slice.
- **Treating red flags as auto-FAIL** — red flags are investigation
  triggers, not verdicts. They produce open_questions with
  recommendations; the user judges.
- **Bypassing the source-citation requirement** — if you find yourself
  proposing a new red flag, it must cite a primary source (Ousterhout
  chapter, Parnas section, Fowler bliki, etc.) per
  `foundation.md` § Red flag schema. Folklore flags rot.

## Where the heavy thinking lives

This SKILL.md is a routing index. The substantive doctrine lives in
`references/`. Per-agent slices apply the doctrine in role-specific
ways without duplicating the foundation.
