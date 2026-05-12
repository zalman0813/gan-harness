# NEGOTIATE-phase review of C-S01-v1

Scope: deep-module sanity spot-check of the generator's proposed sprint
contract for S01 ("Parser, differ, applier wired into one CLI command").
Applies evaluator-slice §1.5 — C1 falsifiability, C4 entry-point budget,
C5 two-adapter rule, §3 applicability honesty, visible §5 red flags.
NEGOTIATE-flavoured only: no `module_design_verification`, no
`drift_from_contract`, no implementation speculation.

## Per-module spot-check

### 1. `config_diff/parser.py` — PASS

- **Applicability honesty (§3)** — declared `cross-system-integration /
  ACL for stdlib json + filesystem`. Consistent with what the module
  actually does (the only place that touches `json.load` + `Path.open`
  in the system). Honest at NEGOTIATE.
- **C1 falsifiability** — `hides_decision` sentence names a concrete,
  likely-to-change decision: how raw bytes-on-disk become
  `ParsedConfig` plus a normalized `ParseError`. Falsification attempt:
  "could the system instead expose `json.JSONDecodeError` /
  `UnicodeDecodeError` / `OSError` to callers and still be reasonable?"
  Yes, easily — so the hiding decision is non-trivial and the sentence
  is doing real work. PASS.
- **C4 entry-point budget** — 1 (`load(path) -> ParsedConfig`).
  Comfortably inside 1-3 budget. PASS.
- **C5 two-adapter rule** — generator proactively writes "No Strategy
  seam (one concrete impl; two-adapter rule per C5 not met for any
  alternate loader this sprint)." Correct call: no port introduced for
  a hypothetical second loader. PASS — and the explicit citation of C5
  reasoning is the discipline we want.
- **Red-flag scan** —
  - `exception-leak` (§5): single normalized `ParseError(path, reason)`
    explicitly covers all four lower-layer cases. Boundary translation
    is being done at NEGOTIATE-time, not punted to caller. Flag silent.
  - `wrapper-around-stdlib` (§5): considered. Wrapper adds genuine
    semantics — error-shape unification + ACL across stdlib JSON +
    filesystem — so it earns its existence. Flag silent.

### 2. `config_diff/differ.py` — PASS with one verification-plan
concern (see cross-cutting)

- **Applicability honesty (§3)** — declared `business-logic`. The
  JSON-path enumeration + comparison + canonical sort order is a real
  business algorithm (not framework-conforming, not a DTO). Honest.
- **C1 falsifiability** — `hides_decision` names a specific decision:
  "JSON-path enumeration + value-comparison algorithm + canonical sort
  order + added/removed/changed classification." Falsification attempt:
  "could differ instead return diffs in some non-deterministic order,
  or expose its tree-walk shape to callers?" Both are plausible
  alternatives — so the hidden decision is non-trivial. PASS.
- **C4 entry-point budget** — 1 (`diff(left, right) -> list[DiffEntry]`).
  PASS.
- **C5 two-adapter rule** — "No Strategy seam." Consistent with a
  single pure-function algorithm. PASS.
- **C7 (interface-as-test-surface)** — generator pre-commits at
  vp-02: "renaming an internal helper inside differ.py does not break
  any test." Excellent — this is the C7 sensor wired into the
  verification_plan, which is exactly the right place. PASS.
- **Red-flag scan** —
  - `temporal-coupling`: pure function, no ordering required on the
    caller. Silent.
  - `config-leak`: signature is two positional args, no options bag.
    Silent.

### 3. `config_diff/applier.py` — PASS

- **Applicability honesty (§3)** — declared `business-logic`. Path-walk
  + immutable update + conflict resolution are genuine domain rules.
  Honest.
- **C1 falsifiability** — names the hidden decisions: conflict
  resolution rules + the immutability guarantee (input tree not
  mutated). Plausible alternative: in-place mutation. Falsifiable.
  PASS.
- **C3 deletion test** — generator explicitly addresses C3:
  "deletion-test commitment: at least 2 distinct callers (CLI + applier
  unit tests) would re-grow the path-walk + immutable-update logic if
  applier were removed." Worth a NEGOTIATE-time note: "CLI + tests" as
  the two distinct callers is borderline — tests aren't a true production
  caller. The stronger reading is that without applier, the path-walk +
  immutability logic would have to be inlined into cli.py AND into any
  future "apply from a saved plan" feature. Still PASS at NEGOTIATE,
  but the C3 argument as currently written reads thin; consider
  rephrasing to either drop the "tests" caller or name a real second
  production caller (e.g. "dry-run preview command" if such exists in
  later sprints).
- **C4 entry-point budget** — 1 (`apply(target, plan) -> ParsedConfig`).
  PASS.
- **C5 two-adapter rule** — no seam. PASS.
- **Red-flag scan** —
  - `exception-leak`: single `ApplyError(entry, reason)` covering both
    path-no-longer-exists and type-conflict. Boundary translation done.
    Silent.

### 4. `config_diff/cli.py` — PASS

- **Applicability honesty (§3)** — declared `framework-shaped — typer
  command; opt-out of deep-module C1-C8 per foundation.md §3 row
  'Framework-mandated shape'`. This is honest and uses the exact §3
  opt-out language. The cli is genuinely typer-shaped (decorator-driven
  command registration) and should NOT be measured against C1-C8.
- **Pass-through verification (§5.5 deletion test)** — generator
  commits cli is a thin wiring layer composing parser.load + differ.diff
  + interactive prompt + applier.apply + atomic write. The earlier
  red-flag concern would be `fake-deep-pass-through`, but a cli command
  that genuinely orchestrates 4 distinct concerns + I/O is not a
  pass-through (multiple callees, real composition). Flag silent.
- **Confirmed boundary**: "this is the only place where stdin/stdout
  I/O happens" — that is a real, named anti-corruption boundary inside
  the codebase (UI I/O isolated). Consistent with the parser.py I/O
  ACL on the input side.

## Cross-cutting observations

### Bounded context

Generator declared: "the entire codebase is one BC (`config-diff`); no
external system other than stdlib + filesystem is crossed, so the only
ACL is parser.py at the json/filesystem boundary." Consistent with §2
(Pocock-calibrated DDD) — one BC is fine for a CLI tool of this size,
and the ACL is correctly placed at the only foreign-vocabulary boundary
(`json.JSONDecodeError` etc. → `ParseError`). PASS.

### verification_plan adequacy

- **vp-01 / vp-02 / vp-03** — unit tests per module, each asserting
  against the broad interface (invariants + error modes). vp-02
  explicitly carries the C7 interface-stability sensor. Good.
- **vp-04** — end-to-end CLI smoke (api kind), with explicit
  read-only-input SHA-256 assertion. Covers the spec.md S01 smoke
  check verbatim. Good.
- **vp-05** — diagnostic + reliability matrix (bad json, missing file,
  permission denied) with no-output-file assertion. Good.
- **vp-06** — matrix sensors: `secret:scan`,
  `import-acl:cli-imports-parser-differ-applier-only` (module ACL —
  prevents cli reaching into module internals), and the C7
  interface-stability rename probe. The import-ACL check is exactly
  the right shape for keeping cli framework-shaped while keeping the
  three business modules deep.

**One concern**: vp-03 (applier) covers the "input target not mutated"
invariant via post-call deep-equal snapshot. Good for the in-test case,
but the contract's done_looks_like names immutability as a guarantee.
Suggest the contract also stipulate that applier returns a fresh tree
even when the plan is empty (the current text says "empty plan returns
input unchanged (deep-equal but not identity if applier rebuilds)" —
the parenthetical hedges between two semantics). Pick one: either
"empty plan returns the same object identity" (cheap) or "always
returns a freshly-rebuilt tree" (uniform). Ambiguity here lands as
drift at VERIFY time.

### criterion_mapping coverage

All 4 spec.md criteria mapped to ≥1 verification step:

- Functionality → vp-04 (e2e smoke)
- Reliability → vp-03 (immutability), vp-04 (input-file SHA), vp-05
  (no output on failure)
- Diagnostics → vp-01 (ParseError shape), vp-05 (e2e bad-input)
- Composability → vp-04 (exit code 0 on success, grep-able lines),
  vp-06 (import-ACL keeps cli composable)

Coverage is honest: each criterion gets at least one behavioural step
(not just unit-test signal). No `vibes` mapping. PASS per
evaluator-handbook Check 3.

### Thresholds

`all` across test / api / matrix. No hedging (no `>=80%`, no `>=50%`).
PASS per evaluator-handbook Check 4.

### Mock honesty

Test-only steps (vp-01/02/03) target the public interface per module,
and vp-04/05 are real api-kind end-to-end runs that don't depend on
mocking. The contract therefore does not hide behind mockist drift.
PASS per evaluator-handbook Check 2.

## Verdict: REQUEST_CHANGES (minor)

Two minor items the generator should revise before we move to
`phase: agreed`. Neither is structural; both are wording fixes that
prevent drift at VERIFY time.

1. **Tighten applier.py C3 deletion-test rationale** — "CLI + applier
   unit tests" reads as a thin C3 argument because tests aren't a
   production caller. Either drop the "tests" caller and lean on
   the stronger version ("without applier, path-walk + immutability
   logic would inline into cli.py and into any future dry-run /
   preview / saved-plan caller"), or name a concrete second
   production caller currently in scope.

2. **Resolve the applier-empty-plan ambiguity in done_looks_like and
   vp-03** — the current text hedges between "deep-equal but not
   identity if applier rebuilds" and "input unchanged." Pick one
   semantic; commit to it in `done_looks_like`; assert it in vp-03.
   This is a NEGOTIATE-time fix, not a VERIFY-time finding.

Once these two are revised, I will accept the contract as-is. Module
boundaries, applicability labels, entry-point budgets, BC declaration,
verification_plan structure, criterion_mapping, and thresholds are all
in good shape — this is a well-formed deep-module-aware contract draft.
