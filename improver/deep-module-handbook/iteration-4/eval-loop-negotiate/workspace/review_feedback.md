# Review feedback — C-S01-v1 (sprint S01, round 1)

**Contract under review:** `C-S01-v1` at `specs/_epic/contracts.jsonl:1`
**Reviewer phase:** NEGOTIATE (per `deep-module-handbook/references/evaluator-slice.md` §1.5)
**Position:** **REQUEST_CHANGES**

---

## Position rationale (one sentence)

The contract is structurally sound and well-scoped, but two business-logic modules (`applier.py`, `selector.py`) volunteered C3 deletion-test reasoning that names a hypothetical / circular second caller — that's exactly the failure mode §1.5 ("'Tests' as the second caller is circular and fails C3 — push back") tells me to surface before agreeing.

---

## §1.5 checklist applied — per-module results

For each module the generator committed to in `done_looks_like[]`, I walked the §1.5 checklist. The §3.5 PASS criteria numbers (C1, C3, C4, C5, C7) and foundation §3 applicability rows are the vocabulary used below.

### 1. `src/config_diff/differ.py` (business-logic) — APPROVE-equivalent

- **C1 falsifiability**: PASS. `hides_decision` names a falsifiable claim — I can imagine an alternative impl that returns an unordered set or uses a non-canonical traversal order, so the sentence is non-trivially true.
- **C4 entry-point budget**: PASS. 1 entry point (`diff_configs`), well within the 1-3 budget.
- **C5 two-adapter rule**: PASS. `Strategy seam: none` explicitly declared; no hypothetical seam introduced.
- **§3 applicability honesty**: PASS. Business-logic label honest — recursive tree walk + diff classification is genuine domain logic, not data carrying.
- **C3 deletion test (volunteered)**: **PASS**. Named callers are `CLI command` AND `applier.py`. Both are real, distinct, non-test callers in the same sprint. Applier consuming DiffEntry records to know `kind` for application is a legitimate second caller.
- **§5 red flag scan**: silent.

### 2. `src/config_diff/applier.py` (business-logic) — REQUEST_CHANGES on C3

- **C1 falsifiability**: PASS. `hides_decision` is falsifiable (could imagine in-place mutation, or simpler last-write-wins without explicit overlap reasoning).
- **C4 entry-point budget**: PASS. 1 entry point (`apply_patch`).
- **C5 two-adapter rule**: PASS. `Strategy seam: none`.
- **§3 applicability honesty**: PASS. Genuine business-logic (immutable update + overlap reconciliation).
- **C3 deletion test (volunteered)**: **FAIL — push back.** Named callers are (a) "the CLI command" and (b) "any future programmatic consumer (e.g. a future library entry point exposing `apply_patch` for scripted promotion)". The second caller is **imminent-but-not-real**, the same shape as the §1.5 prohibited "in case we later need X" pattern and a sibling failure to the "'Tests' as the second caller" example. C3 requires ≥2 actual callers OR 1 + 1 named-imminent with a hard date. No hard date given.
- **§5 red flag scan**: silent.

**Request:** Either (a) name a second real caller that exists by end of S01 with a verification step that exercises it (e.g., a stable public-API entry point used by a future sprint with a date), or (b) drop the speculative second caller and rely on C1/C2/C4 alone — `applier.py` is plainly deep on those grounds; the weak C3 narrative was not load-bearing.

### 3. `src/config_diff/selector.py` (business-logic) — REQUEST_CHANGES on C3

- **C1 falsifiability**: PASS. `hides_decision` is falsifiable (could imagine a selector that accepts only single integers per line).
- **C4 entry-point budget**: PASS. 2 entry points (`render_choices`, `parse_selection`) — within 1-3.
- **C5 two-adapter rule**: PASS. `Strategy seam: none`.
- **§3 applicability honesty**: PASS.
- **C3 deletion test (volunteered)**: **FAIL — push back.** Named callers are (a) "the CLI loop" and (b) "any non-TTY test harness that drives selection programmatically". The second caller is **a test harness** — exactly the §1.5 prohibited pattern: "'Tests' as the second caller is circular and fails C3". A module's tests are not a real caller; that's the interface-as-test-surface (C7) relationship, not deletion-test (C3) evidence.
- **§5 red flag scan**: temporal-coupling considered (render_choices then parse_selection look ordered) — does not fire because the two functions are independent (no shared state, no mandatory call order; render_choices is for display, parse_selection is for input, either can be called without the other).

**Request:** Either (a) name a real second non-test caller (e.g., a future scripted-selection sprint), or (b) drop the "non-TTY test harness" clause from C3 and rely on C1/C2/C4 — selector is plainly deep on entry-point + hidden-decision grounds alone.

### 4. `src/config_diff/types.py` (dto opt-out) — APPROVE-equivalent

- **§3 applicability honesty**: PASS. Pure data container (dataclass + alias); `dto` opt-out per foundation §3 is honest. Appears as its own `done_looks_like[]` item (the §1.5 dishonest-opt-out guard is satisfied).

### 5. `src/config_diff/cli.py` (framework-shaped opt-out) — APPROVE-equivalent

- **§3 applicability honesty**: PASS. Typer entry point conforming to a CLI framework convention; the framework-shaped opt-out is honest. The cli composes 4 distinct concerns (JSON load, diff, selection drive, write) — not a pass-through. Appears as its own `done_looks_like[]` item.

---

## Other evaluator-handbook §1 checks (negotiation-phase)

- **Check 1 — Verification depth**: PASS. Every `done_looks_like` flow item maps to ≥1 verification step. `vp-04` (kind: test via CliRunner) covers the end-to-end smoke; `vp-04` + `vp-06` cover the read-only invariant; `vp-05` covers diagnostics.
- **Check 2 — Mock honesty**: PASS. `vp-04` is a real CLI integration via Typer's `CliRunner` against real example files. Module tests (`vp-01..vp-03`) exercise the public interface directly, no internal-collaborator mocking. No mock-heavy unit-only contracts.
- **Check 3 — Criterion coverage**: PASS. All 4 criteria mapped; each has ≥1 verification step.
- **Check 4 — Threshold realism**: PASS. `test_must_pass: all` + `matrix_must_pass: all` — strongest realistic thresholds.
- **Check 5 — Scope match**: PASS. `features_covered: ["F01"]` matches `spec.md` S01 plan.
- **C7 sensor presence (new §1.5 item)**: **PASS — positive evidence.** `vp-06` matrix contains the check
  `interface-stability:renaming-any-private-helper-in-differ/applier/selector-leaves-tests-vp-01..vp-03-green`,
  which is exactly the recommended `interface-stability:rename-internal-helper-…` sensor. The generator pre-committed to tests surviving internal refactor. This is the strongest possible C7 signal at NEGOTIATE time and significantly de-risks the IMPLEMENT phase.

---

## Summary of requested changes

| # | Module | Issue | Foundation citation | Fix options |
|---|---|---|---|---|
| 1 | `src/config_diff/applier.py` | C3 deletion-test names a hypothetical future caller ("future library entry point") with no hard date | foundation.md §3.5 C5/C3 + §5.5 (deletion test); evaluator-slice.md §1.5 prohibition | (a) name a real second caller present by S01 end + add verification step, OR (b) drop the speculative C3 clause; C1/C2/C4 carry the module |
| 2 | `src/config_diff/selector.py` | C3 deletion-test names "non-TTY test harness" — circular per §1.5 | evaluator-slice.md §1.5 ("'Tests' as the second caller is circular") | (a) name a real non-test second caller, OR (b) drop the test-harness clause; C1/C4 carry the module |

Neither change is structural — the contract scope, verification plan, criterion coverage, thresholds, and C7 sensor are all sound. After the two C3 clauses are revised (or dropped), my position will move to APPROVE without a new round.

---

## Position: REQUEST_CHANGES

Please revise the two C3 deletion-test narrative clauses in `done_looks_like[]` and re-propose. Same review round; this is a minor amendment, not a structural redraft.
