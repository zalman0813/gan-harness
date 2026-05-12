# NEGOTIATE review — C-S01-v1

- **Contract**: C-S01-v1 (sprint S01, phase: agreed candidate)
- **Reviewer**: evaluator
- **Verdict**: **APPROVE**
- **Skill basis**: `deep-module-handbook` (foundation.md §3.5 + §5; evaluator-slice.md §1.5)

## Summary

Generator's S01 contract draft is well-shaped against evaluator-slice.md §1.5. Four modules (`differ`, `applier`, `parser`, `cli`) are declared with applicability honesty, falsifiable hides_decision sentences, sane entry-point budgets, no speculative seams, and a C7 interface-as-test-surface sensor in `vp-05`. The `cli` opt-out is explicit (framework-shaped per foundation.md §3) and still appears as its own `done_looks_like[]` item per §1.5's dishonest-opt-out check. Proceed to IMPLEMENT.

## Per-module audit (§1.5 checklist)

### differ.py (business-logic)

- **C1 falsifiability** — PASS. `hides_decision` names a concrete decision likely to change (traversal order, equality semantics for floats/None, container vs leaf threshold). I cannot falsify it in <1 minute from the spec alone — it is a real design claim, not ceremony.
- **C4 entry-point budget** — PASS. One entry point (`diff_trees`), well inside the 1–3 budget.
- **C5 two-adapter rule** — PASS. Generator explicitly rules out a `DifferStrategy` port citing the two-adapter rule. Honest collapse to direct dependency.
- **§3 applicability honesty** — PASS. `business-logic` is consistent with what S01 actually builds (the core diff algorithm).
- **§5 red flags visible from contract** — None fire. No `sqlalchemy.Row`-style exception leak; `error_modes` commits to `DifferError` (domain) only.
- **C3 deletion test (volunteered)** — PASS. Generator names **two distinct non-test callers**: (a) `applier` (kind alignment for patch plan), (b) CLI renderer (printing diff lines). Both are real, in-scope for S01, not hypothetical, not "tests". Patched-bullet hypothetical-caller variant (no "future programmatic consumer without hard date") does not apply.
- **C7 interface-as-test-surface sensor** — PASS. `vp-05` matrix check `interface-stability:rename-internal-helper-in-differ-tests-still-pass` is present.

### applier.py (business-logic)

- **C1 falsifiability** — PASS. Names conflict policy (strict vs last-write-wins) as the decision likely to change. Falsifiable.
- **C4 entry-point budget** — PASS. One entry point (`apply_patch`).
- **C5 two-adapter rule** — PASS. Generator explicitly rules out a `ConflictPolicy` Strategy seam (second policy is hypothetical → two-adapter rule fails → keep direct). Correct application of the rule.
- **§3 applicability honesty** — PASS.
- **§5 red flags** — None fire.
- **C3 deletion test (volunteered)** — PASS with one minor caveat. Generator names (a) CLI (writing patched file) and (b) "any future audit-log emitter". The audit-log emitter caller is **softly hypothetical** in the §1.5 patched-bullet sense — it has no hard date and is not in S01's scope. However, caller (a) (CLI) is real and the deletion-test only requires ≥2 callers to be **future-reasonable**; the more-conservative reading would prefer two real callers today. **Not a REQUEST_CHANGES** because: (i) C3 is "optional if generator volunteered it" — generator may rescind without penalty; (ii) the CLI caller alone establishes non-trivial regrowth (immutable-copy + conflict-check would inline into the CLI write path, which is itself complex enough that the deletion-test intuition holds even discounting the hypothetical). Recorded as a **hint** to revisit at VERIFY.
- **C7 sensor** — PASS. `vp-05` covers applier.

### parser.py (cross-system-integration)

- **C1 falsifiability** — PASS. `hides_decision` names error-message format, source-location precision, future JSON5 support as the decisions likely to change. Falsifiable.
- **C4 entry-point budget** — PASS. One entry point (`load_config`).
- **C5 two-adapter rule** — N/A (no Strategy seam proposed).
- **§3 applicability honesty** — PASS. `cross-system-integration` is correct given the module wraps stdlib `json` + `OSError` at the filesystem boundary; foundation.md §3 also flags this row as the one that **requires ACL**, which the contract honors (`error_modes` says "wraps OSError + json.JSONDecodeError, never leaks foreign exception types").
- **§5 red flags** — None fire. `exception-leak` would have fired if the contract committed to letting `json.JSONDecodeError` cross the public surface; it explicitly does not.
- **C3** — not volunteered; acceptable per §1.5 (defer to VERIFY against git diff).
- **C7 sensor** — PASS. `vp-05` covers parser.

### cli.py (framework-shaped, opt-out)

- **§3 applicability honesty** — PASS. Opt-out is explicitly cited against foundation.md §3 row "Framework-mandated shape (CLI command)". The contract item exists as its own `done_looks_like[]` entry so a dishonest opt-out would be spottable — exactly what §1.5 demands.
- C1–C8 do not apply per foundation.md §3.5 ("Apply only when §3 puts the module in an 'apply deep module' row").
- **§5 red flags** — None fire on the labelled role (translate domain exceptions → stderr + exit codes; wire parser→differ→prompt→applier→write).

## Cross-cutting NEGOTIATE checks (evaluator-handbook)

- **Check 1 verification depth** — PASS. Every `done_looks_like[]` behavioral item maps to at least one `vp-NN`; module items map to `vp-04` (interface counts + docstring assertions) and `vp-05` (C7 sensor). `vp-06` (manual) complements `vp-01` (scripted) for the interactive prompt flow.
- **Check 2 mock honesty** — PASS. `verification_plan[]` includes `kind: test` AND `kind: matrix` AND `kind: manual`. No process-boundary mocking is hinted at; tests appear to operate on real stdlib + real filesystem (via `tmp_path` per spec.md cross-cutting). The C7 sensor in `vp-05` is a strong anti-mockist signal.
- **Check 3 criterion coverage** — PASS. All four criteria (Functionality, Reliability, Diagnostics, Composability) appear as keys in `criterion_mapping`; each maps to ≥1 verification step.
- **Check 4 threshold realism** — PASS. `all` for test_must_pass and matrix_must_pass; `>=100%` per criterion. No hedging.
- **Check 5 scope match** — PASS. `features_covered: ["F01"]` matches the sole feature S01 delivers per spec.md.

## Hints (non-blocking; revisit at VERIFY)

1. **applier C3 second caller is softly hypothetical.** The "future audit-log emitter" lacks a hard date. Generator may rescind C3 entirely at VERIFY (the CLI caller alone justifies the module via cognitive-load + ordering invariants), or replace it with a real second caller if one materializes. Not blocking at NEGOTIATE because C3 is optional and the CLI caller is itself non-trivial.
2. **`vp-06` (manual) is operator-time only.** Make sure VERIFY runs `vp-01` (scripted simulation) before `vp-06`; do not let the manual step silently substitute for the scripted byte-equality assertion.

## Position

**APPROVE.** Generator may transition C-S01-v1 to `phase: agreed` and proceed to IMPLEMENT.
