# Self-Verify Loop

The anti-rot guarantee for /plan Phase 1. Before declaring done, the planner runs three scripts; any FAIL forces a fix-and-retry round (max 3). All PASS exits Phase 1, hand to Phase 2 per-Q checkpoint walk.

## The three scripts

| Script | What it checks | Diagnostic when FAIL |
|---|---|---|
| `plan_validator.py` | JSON Schema 2020-12 against `feature-list.schema.json` + DAG cycles + missing depends_on + P1-cannot-depend-on-lower-priority | structural problem: schema violation, dependency cycle, broken refs. Note: schema requires `open_question.resolution` to be a non-empty string — null / missing fails here. |
| `lift_capabilities.py` | semantic well-formedness: duplicate IDs (feature/AC/Q), `decision_refs[]` resolve to existing files, `eval_anchors` / `must_not` uniqueness | semantic problem: cross-reference or invariant the schema can't express |
| `plan_lint.py` | design discipline: phase-named features (L10a), UI-touching features without `l5_smoke_path` (L10b) | design problem: horizontal phasing or evaluator can't smoke-test |

All three are pure-stdlib python3, **PASS/FAIL only** (no WARN, no STRICT mode, no TODO). They emit JSON to stdout.

## Loop discipline

```
round = 0
while round < 3:
    write feature-list.json (every open_question carries a non-empty
        resolution = planner's recommendation; user reviews at Phase 2 walk)
    (and any new docs/adr/NNNN-*.md whose three-test gate passed)
    plan_validator.py    → PASS / FAIL
    lift_capabilities.py → PASS / FAIL
    plan_lint.py         → PASS / FAIL

    if all PASS:
        exit (Phase 1 done, hand to Phase 2 per-Q checkpoint walk)
    else:
        read violations
        fix the source design (NOT patch around the check)
        round += 1

if round == 3 and any FAIL:
    abort with diagnostic — design is fundamentally wrong, escalate to user
```

## Why three scripts, not one

Three concerns, three diagnostic categories:

- `plan_validator.py` — "the file's structure is wrong"
- `lift_capabilities.py` — "the file's semantics are wrong (cross-references, dupes)"
- `plan_lint.py` — "the design violates harness discipline"

Splitting them lets the planner read targeted diagnostics and fix accordingly. A combined output would obscure which kind of fix is needed.

## What's deliberately NOT lint-enforced

- **Deep-module depth** — doctrine in [deep-module.md](deep-module.md). The planner applies depth thinking during design; we don't mechanically score modules at lint time because heuristics fail edge cases (and the schema doesn't carry a `module` block yet).
- **Module docstring promise** — generator + active stack skill responsibility. Lint can't tell whether the generator will actually write the docstring; trust the contract.
- **Forbidden top-level fields** (`risks`, `cross_r_risks`, `tech_debt`, etc.) — caught by JSON Schema's `additionalProperties: false` at the validator level. No separate lint rule needed.

These choices keep lint focused on rules that are mechanically unambiguous AND either consumer-blocking or design-discipline. Everything else is doctrine the planner reads at the right decision point.

## Anti-patterns the planner must avoid

- **Patching around a check** — fix the source design, not the symptom
- **Skipping a script** — all three must PASS; one PASS is not enough
- **Multiple rounds with the same fix** — if the same violation fires twice, escalate (the design is fundamentally wrong)
