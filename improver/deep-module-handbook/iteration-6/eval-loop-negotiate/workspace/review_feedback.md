# Review — C-S01-v1 (sprint S01, round 1)

**Verdict:** REQUEST_CHANGES

One substantive item on `applier.py`'s volunteered C3 deletion-test
reasoning. Everything else is APPROVE-grade — contract is well-shaped,
opt-outs are honest, C7 sensor is present, all four criteria have
verification coverage.

---

## evaluator-handbook six-check walk

### Check 1 — Verification depth (PASS)

Every `done_looks_like[]` item has a supporting `verification_plan[]`
step:

- diff-print + ordering + path-keying → vp-01 (unit, lexicographic
  ordering asserted) + vp-03 (CLI smoke against expected-diff.txt) +
  vp-06 (manual end-to-end)
- numeric selection acceptance + bad-token rejection → vp-03
  (CliRunner with stdin) + vp-04 (bad-selection-token case)
- patched-file byte-identity + input read-only → vp-03 + vp-06 (last
  step asserts `examples/{a,b}.json` byte-identical to git-tracked)
- malformed/unreadable inputs → vp-04
- exit-code + grep-able stdout → vp-03 + vp-06

CLI-touching sprint, so the expectation is a real-process step rather
than a `playwright`/`api` step — vp-03 (CliRunner driving the real
typer entrypoint) + vp-06 (operator manual smoke) cover that. Not
unit-test-only.

### Check 2 — Mock honesty (PASS)

No mock-heavy steps. vp-01 and vp-02 are pure-function unit tests
against `differ.compute_diff` / `applier.apply_patch` (real inputs,
real outputs — Classicist, no internal mocking). vp-03 drives the
real CLI via `typer.CliRunner` against `tmp_path` fixtures. vp-04
exercises real error paths. vp-06 is operator-driven. No fixture
stands in for an internal collaborator.

### Check 3 — Criterion coverage (PASS)

All four spec.md criteria present as keys with ≥1 step each:

- Functionality → vp-03, vp-06
- Reliability → vp-02, vp-03, vp-04
- Diagnostics → vp-04
- Composability → vp-03, vp-06

Diagnostics has only one mapped step (vp-04), but that step is
purpose-built for the criterion (malformed JSON, missing file, bad
token — three distinct cases inside one `kind: test`). Acceptable;
not a REQUEST_CHANGES item.

### Check 4 — Threshold realism (PASS)

`test_must_pass: all` and `matrix_must_pass: all`. No hedging.
Defaults are aggressive as the handbook prescribes.

### Check 5 — Scope match (PASS)

`features_covered: ["F01"]` matches the only feature in spec.md, which
S01 is committed to delivering end-to-end (the smoke check in
spec.md `### S01` is the same end-to-end flow vp-06 exercises).

### Check 6 — Deep-module spot-check (REQUEST_CHANGES — see below)

Delegated to deep-module-handbook evaluator-slice §1.5. Findings
inline in the next section.

---

## deep-module evaluator-slice §1.5 NEGOTIATE checklist

The contract enumerates four modules. I walk each separately because
two are opt-outs and two are `business-logic` subject to C1-C8.

### `src/config_diff/diff_model.py` — applicability `dto` (PASS)

Opt-out honestly declared and visible as its own `done_looks_like[]`
item per §1.5 ("Opt-out modules … MUST still appear as their own
`done_looks_like[]` item so you can spot a dishonest opt-out"). The
declared role — `DiffEntry` / `PatchPlan` dataclasses with no
behavior — matches foundation.md §3 "Pure data container" row. No
business rules smuggled in. No further checks needed (C1-C8 do not
apply per §3.5 "Apply only when §3 puts the module in an apply-deep
row").

### `src/config_diff/differ.py` — applicability `business-logic` (PASS)

- **C1 falsifiability:** `hides_decision` reads "how a tree-shaped
  JSON value pair is linearised into an ordered, JSON-path-keyed
  sequence of added/removed/changed entries with stable ordering
  across runs". I can falsify it in <1 minute — imagined alternatives
  include character-level diff, unordered output, or value-typed-but-
  not-path-keyed output. The sentence makes a non-trivial claim
  about a decision likely to change (the linearisation strategy).
  C1 passes.
- **C4 entry-point budget:** 1 (`compute_diff`). Well inside 1-3.
- **C5 two-adapter rule:** "Strategy seam: none (single algorithm;
  YAGNI per Pocock two-adapter rule)". Honest. No phantom seam
  introduced.
- **C6 broad interface:** invariants (JSON-parsed shape, not bytes),
  ordering (lexicographic), error modes (`DifferError` only, no
  stdlib propagation) all named in the item. PASS.
- **§3 applicability honesty:** business-logic match — this is the
  diff algorithm, primary deep-module territory.
- **§5 red flags:** none. No exception-leak (custom `DifferError`),
  no config-leak (two positional params), no pass-through (one entry
  point doing real work).
- **C7 sensor:** vp-05 includes
  `interface-stability:rename-internal-helper-in-differ-tests-still-pass`.
  Positive evidence.

### `src/config_diff/applier.py` — applicability `business-logic` (REQUEST_CHANGES on C3 only)

- **C1 falsifiability:** "how a selected subset of DiffEntry items
  is folded back into the left tree to produce a new tree, without
  mutating the input and preserving key order of unchanged subtrees".
  Falsifiable — imagined alternatives include in-place mutation,
  key-order-loss, or all-or-nothing application. PASS.
- **C4 entry-point budget:** 1 (`apply_patch`). PASS.
- **C5 two-adapter rule:** "Strategy seam: none". Honest.
- **C6 broad interface:** invariants (left never mutated, deep copy
  returned), ordering (left for unchanged keys, right for new keys),
  error modes (`ApplierError(path, reason)` on missing path).
  Complete. PASS.
- **§3 applicability honesty:** business-logic — matches.
- **§5 red flags:** none.
- **C7 sensor:** vp-05 includes
  `interface-stability:rename-internal-helper-in-applier-tests-still-pass`.
  Positive.

**However: C3 deletion test, REQUEST_CHANGES.** The generator
volunteered a C3 claim and named two callers: (1) `cli.py` and
(2) "any future programmatic caller (e.g. an apply-without-prompt
mode)". Per evaluator-slice §1.5 C3 spot-check (Hypothetical
failure mode):

> "future programmatic consumer / downstream epic might use this'
> without a hard date fails the same test by the C5 two-adapter
> rule … one named-but-not-real implementation is YAGNI. The second
> caller must exist now, or be imminent with a concrete date. Push
> back."

The first caller (cli.py) is real and present in this sprint. The
second is a hypothetical "future" caller with no hard date — same
shape as the C5 hypothetical-seam failure mode applied to callers.

Note this does NOT mean applier.py is shallow — C1+C2+C4+C6 already
establish depth (the path-walk + immutable-copy logic is non-trivial
and centralised). The fix is to bring the C3 claim in line with
reality, three options:

  (a) Drop the volunteered C3 claim entirely and rest the depth
      argument on C1+C2+C4+C6 (still PASS-grade — C3 is optional at
      NEGOTIATE per §1.5 "If the generator did NOT volunteer C3,
      that's acceptable at NEGOTIATE").
  (b) Replace the hypothetical second caller with a second REAL
      caller present in S01 (I don't see one — the contract has only
      cli.py touching applier — so (a) or (c) is likelier honest).
  (c) Commit "apply-without-prompt mode" as an imminent feature with
      a hard date and a feature ID, accepting that the date becomes
      a tracked obligation.

Recommend (a) — smallest amendment, keeps the contract honest.

### `src/config_diff/cli.py` — applicability `framework-shaped` (PASS)

Opt-out honestly declared (typer command shape; foundation.md §3
row "Framework-mandated shape (CLI command)"). Item explicitly says
"No business logic beyond glue", which is the right contract for a
framework-shaped opt-out — the differ/applier modules carry the
logic, cli is wiring + I/O shaping. Visible as its own
`done_looks_like[]` item per §1.5 opt-out-visibility rule.

---

## Summary of requested amendments

1. **applier.py C3 deletion-test second caller** — replace the
   hypothetical "future programmatic caller (e.g. an apply-without-
   prompt mode)" with one of: (a) drop the C3 claim and rest on
   C1+C2+C4+C6, (b) name a second real caller present in S01, or
   (c) supply a hard date for the apply-without-prompt mode. Cite:
   evaluator-slice §1.5 C3 spot-check (Hypothetical failure mode);
   foundation.md §4 cross-cutting tension #3 (two-adapter rule
   applied to callers).

No other concerns. Once the C3 wording lands, the contract reaches
APPROVE and can transition to `phase: agreed`.
