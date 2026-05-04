---
name: evaluator-handbook
description: Doctrine the gan-harness evaluator agent operates by — adversarial probe categories (boundary / concurrency / idempotency / orphan), few-shot calibration examples to align verdict severity, and verdict discipline (PASS / FAIL / DEFERRED only, no PARTIAL hedge). For deep-module design review when judging interface depth, see the separate `deep-module-handbook` approach skill which evaluator also auto-loads via frontmatter `skills:`. Loaded by the evaluator subagent at startup. Make sure to use this whenever grading an implementation against acceptance criteria, deciding a verdict, or selecting which adversarial probes to run.
---

# Evaluator Handbook

The evaluator agent's operating doctrine. Each reference is loaded on
demand when the evaluator reaches the relevant decision point.

## When the evaluator consults each reference

| Decision point | Read |
|---|---|
| Picking which adversarial probe(s) to run for an AC | [references/adversarial-probes.md](references/adversarial-probes.md) |
| Calibrating PASS vs FAIL on a borderline case | [references/calibration-examples.md](references/calibration-examples.md) |
| Tempted to write PARTIAL / WARN / "I'm not sure" / DEFERRED-as-hedge | [references/verdict-discipline.md](references/verdict-discipline.md) |
| Reviewing whether a module's interface meets the depth principle | [`deep-module-handbook` skill](../deep-module-handbook/SKILL.md) (foundation.md + the slice file evaluator-handbook will eventually own) |

## Loading order

Read `verdict-discipline.md` and `adversarial-probes.md` once at the top
of every evaluation, before grading. They're short. `calibration-examples.md`
is reference material — read it when a specific case feels borderline.

`deep-module-handbook` is read only when you have a structural call-out
worth making (e.g. you noticed the implementation pushed too much
complexity outward into the AC's expected behaviour).

## What's NOT here

- The eval JSON schema field-by-field — that's in
  `.claude/agents/evaluator.md` § Output. The schema mirrors Anthropic's
  `skill-creator/agents/grader.md` field names; do not rename them.
- L1/L2/L5 commands — those come from `feature.test_contract` and the
  active stack skill's references
- Mechanical AC-coverage checks — those are the `ac_coverage` SubagentStop
  hook's domain. When you spawn, the gate has already PASSed (FAIL would
  have skipped your spawn entirely). Read the gate evidence at
  `_traces/{F}-R{N}-ac_coverage.gate.json` if you want the detail; do NOT
  re-run the check.
- The "no runtime sprint contract" decision rationale — that lives in
  the relevant ADR under `docs/adr/`. Briefly: the contract is the AC
  list locked at /plan, not a generator↔evaluator runtime negotiation.
