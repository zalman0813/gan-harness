# Deep Module Handbook — Generator Slice

How the generator applies deep-module principles when implementing
modules and their tests.

Read `references/foundation.md` first for shared definitions, scope,
red flags, and DDD calibration.

**Scope reminder:** this slice covers only the deep-module-specific
generator behaviors. The generator's general behavior (e.g.,
strategic-decide refine-vs-pivot, anti-oscillation, when to call
`propose_contract` vs `propose_contract_amendment`) lives inline in
`.claude/agents/generator.md`.

## §1 When the generator consults this slice

The generator engages this slice in **two distinct /loop phases**:

1. **NEGOTIATE phase** (proposing a sprint contract to evaluator,
   appended to `contracts.jsonl` with `phase: agreed`). See §1.5.
2. **IMPLEMENT phase** (writing modules + tests after contract is
   agreed). See §2.

Both phases share `foundation.md`'s vocabulary (§1 definitions, §3.5
PASS criteria C1-C8, §5 red flags). They differ in the artefact you
write into: NEGOTIATE writes `done_looks_like[]` narrative + the
contract itself; IMPLEMENT writes code, tests, and (if needed) a
`propose_contract_amendment` if implementation reveals the agreed
contract is wrong.

## §1.5 NEGOTIATE phase — module-level commitments in the sprint contract

In v3.8 there is no separate `module_design` schema field. Module
boundaries and depth commitments live inside the sprint contract's
narrative — primarily `done_looks_like[]` and `verification_plan[]`.
For each module this sprint will touch (new or modified), commit in
the contract narrative to:

| What to write | PASS criterion | Where it lands in the contract |
|---|---|---|
| The module's `hides_decision` (one sentence ≥30 chars naming what design decision it owns; Parnas) | C1 | `done_looks_like[]` item — use the canonical embedding (see "Per-module done_looks_like item shape" below) |
| Applicability classification (business-logic / cross-system-integration / dto / framework-shaped / hot-path / one-shot — foundation.md §3) | (gate) | Same canonical item. Opt-out classes (`dto` / `framework-shaped` / `hot-path` / `one-shot`) STILL need their own `done_looks_like[]` item naming the module + applicability + one-line role; they only skip the C1-C8 row below |
| Public-interface entry-point count (≤ 1-3 unless Unix-style genuine multi-use) | C4 | Same canonical item — append `Entry-point budget: N (`fn1`, `fn2`, ...)` |
| Strategy / DI seam discipline — only commit to a port if ≥2 actual implementations exist OR one + one named imminent with date (Pocock two-adapter rule) | C5 | Same canonical item — append `Strategy seam: <none / interface_name with second_impl name>` |
| Broad-interface commitments — declare invariants, ordering constraints, and named error modes the module will document in its docstring | C6 | Same canonical item — append `Broad interface: invariants=… ordering=… error_modes=…`. The docstring at IMPLEMENT time mirrors this verbatim. |
| Bounded-context check — name the BC each module belongs to; if it crosses a BC, name the ACL | — | Same canonical item (or separate item if BC spans multiple modules); ACL is a structural deliverable |
| `criterion_mapping` key naming (whole-contract concern, not per-module) | — | Keys MUST be the literal criterion names from `spec.md`'s `## Evaluation criteria` headings, case-sensitive. Do NOT lowercase or rename them. Evaluator parses by exact match for the 4-of-4 archetype-criterion coverage check; rename = misroute. |
| Deletion-test pre-commitment (OPTIONAL — for modules at risk of pass-through smell, e.g. wrapper-shaped or one-method libs) | C3 | If you volunteer C3 reasoning at NEGOTIATE, name the ≥2 distinct callers that would regrow the complexity. Each caller must be **real and present in this sprint or imminent with a hard date**. Two failure modes the evaluator will push back on (mirrors evaluator-slice §1.5): (a) **Circular** — "tests" as the second caller is invalid; tests ride on the real caller graph, they're not callers in the deletion-test sense. (b) **Hypothetical** — "future programmatic consumer" / "downstream epic might use this" / "future API caller" without a hard date fails by the C5 two-adapter rule (foundation.md §4 cross-cutting tension #3). If the second caller doesn't actually exist this sprint, either drop C3 (leave it for VERIFY) or name an imminent caller with a concrete date. If you don't volunteer C3 here, evaluator will check it at VERIFY against the actual git diff. |
| Interface-as-test-surface sensor (RECOMMENDED for non-opt-out modules) | C7 | `verification_plan[]` step of `kind: matrix` (the canonical kind for binary-outcome sensors). Use `checks: ["interface-stability:rename-internal-helper-in-<module>-tests-still-pass"]`. **`<module>` placeholder convention**: use the bare module name (no extension, no path), matching how the module is referred to in the `MODULE` canonical-embedding line (e.g. `differ`, `applier`, `cursor` — NOT `differ.py` / `config_diff/differ.py` / `differ.diff`). The check string is the human-readable assertion; the sensor implementation is the matrix runner's job. Don't use `kind: test` — that's for actual test-suite invocations, not meta-assertions about whether tests survive refactors. |

### Per-module done_looks_like item shape (canonical embedding)

Each module the sprint touches gets ONE `done_looks_like[]` item with
this shape, so the evaluator can parse without ambiguity:

```
MODULE <path> (applicability: <enum>[; opt-out of C1-C8])
  hides_decision: '<sentence ≥30 chars>'.
  Entry-point budget: <N> (`<fn1>`, `<fn2>`, ...).
  Strategy seam: <none | interface_name + named second impl>.
  Broad interface: invariants=<…>; ordering=<…>; error_modes=<…>.
  Bounded context: <ctx-name>[; ACL at <boundary>].
  [Deletion test (optional): removing this module would force the path-walk + immutable-update logic to regrow in <caller-A> and <caller-B>.]
```

For opt-out modules (`dto` / `framework-shaped` / `hot-path` /
`one-shot`), the shape collapses to:

```
MODULE <path> (applicability: <opt-out-enum> — opt-out of C1-C8 per foundation.md §3 row '<reason>')
  Role: <one-line description of what wiring/data this module is>.
```

These don't need C1-C8 commitments because the §3 row says deep-module
discipline doesn't apply. But they MUST still appear so evaluator
knows you considered them.

### Deferring decisions at NEGOTIATE

If a deep-module question can't be resolved at NEGOTIATE time, say so
explicitly in the canonical item — `Deletion test: TBD at IMPLEMENT;
revisit via propose_contract_amendment if depth uncertain`. The
evaluator either accepts the deferral or pushes back during contract
review.

If a red flag from foundation.md §5 fires *during contract drafting*
(you can see e.g. an exception-leak pattern already implicit in the
proposed boundary), surface it in the canonical item with a proposed
mitigation — that's what NEGOTIATE is for.

## §2 IMPLEMENT phase — implementation order (strict)

1. **Public signatures + docstring** first.
   - The docstring's first line states what design decision the
     module hides (Parnas check, foundation.md §1; PASS criterion C1)
   - The docstring also declares the **broad interface** (foundation.md
     §1 + §3.5 C6): any invariants the caller must respect, any
     ordering constraints (init-before-X, etc.), and the named error
     modes the caller must handle. If callers must learn anything to
     use the module correctly, it goes in the docstring — implicit
     contract is no contract.
   - No implementation written yet
2. **Self-review** the public signatures against:
   - The agreed sprint contract's `done_looks_like[]` narrative (do
     the actual signatures match what was committed at NEGOTIATE?)
   - foundation.md §1 leaky-abstraction check (caller doesn't need to
     know internal facts)
   - foundation.md §3.5 C4 entry-point budget (≤ 1-3 public entry
     points, unless this is a genuine multi-use module like Unix's
     file API)
   - foundation.md §5 temporal-coupling flag (no required call order)
3. **Tests against the public signatures.** See §4. Tests target the
   interface, not internals.
4. **Implementation body.** The body can be complex (that's the
   point of depth).
5. **Pass-through self-check** (foundation.md §5
   `fake-deep-pass-through` flag). For each public method written,
   ask: "If I removed this method, would callers only need to rename
   their call to an inner method (no other change)?" If yes → either
   delete (pass-through) or confirm as ACL (translation work
   justifies it).

If step 5 fires and is not an ACL, do NOT silently inline. Either:
- the agreed contract's `done_looks_like[]` committed to this method
  as a real boundary — in which case `propose_contract_amendment`
  before deleting (the evaluator agreed to that interface; you can't
  unilaterally remove it); OR
- the contract is silent on this method — inline it and note the
  cleanup in your commit message.

## §3 Information hiding rules

These are constraints, not red flags — generator follows them
without negotiation.

- **Return interface types, not concrete classes.** Callers see the
  abstraction, not the implementation choice.
- **Do not expose third-party types in public signatures.** A
  third-party type in the public surface triggers ACL need (per
  foundation.md §1 ACL definition). If the agreed contract's
  `done_looks_like[]` commits to such a leak (e.g. "returns
  sqlalchemy.Row"), `propose_contract_amendment` before
  implementing — that was an interface-design mistake at NEGOTIATE
  time and silently honouring it locks in the leak.
- **Internal helper methods stay private.** Never make a private
  method public for "ease of testing" — extract to a new module
  with its own public interface instead (see §4 and §5 below).
- **No public mutation methods on conceptually-immutable values.**
  If a value is mutating, say so in the docstring; if it is not,
  return new instances instead of mutating.

## §4 Test layer rules

(Implements foundation.md §3.5 C7 — interface = test surface.)

- **Test the public interface.** Each test invokes a public method
  and asserts on observable result (return value, raised exception,
  or externally-observable side effect).
- **Tests survive internal refactor.** Renaming an internal helper
  must not break any test. If renaming breaks a test, that test was
  testing implementation, not interface — rewrite the test or extract
  the helper to its own module with its own public interface.
- **Use real internal collaborators.** Per foundation.md §4
  cross-cutting tension #2 (Mockist vs Classicist), this methodology
  is Classicist: internal collaborators inside the module are real,
  not mocked.
- **Mock only process boundaries.** Network, filesystem, subprocess,
  external API, LLM call. Mocking these isolates tests from
  environment; mocking your own domain types freezes internal
  collaboration and defeats deep-module value.
- **Mock budget red flag.** If a single test's mock setup feels like
  it encodes the module's internal collaboration graph, you have
  crossed into Mockist territory — back off. If you cannot reduce
  mocks without losing meaningful coverage, the boundary is wrong:
  `propose_contract_amendment` to revisit either the module boundary
  or the `verification_plan` test target.

## §5 Pass-through self-check

After writing the implementation, walk every public method and
apply the foundation.md §5 `fake-deep-pass-through` trigger:

> "If I removed this method, would callers only need to rename their
> call to an inner method (no other change)?"

- **Yes**, and the method does not perform translation across a
  foreign vocabulary boundary → it's a pass-through. Either delete
  (callers call the inner method directly) or merge with the inner
  method.
- **Yes**, but the method translates a foreign type to a domain type
  → it's an ACL method. Keep, but verify the ACL is in the planner's
  spec (per foundation.md §1 ACL definition).
- **No** (removal would force callers to handle internal complexity)
  → the method earns its existence.

If unsure (the answer is "maybe"), do not silently keep or silently
delete. Either commit to the rationale in your commit message AND in
the next contract negotiation round, or `propose_contract_amendment`
to clarify the boundary.

## §6 Common Rationalizations (deep-module specific)

Supplements the generator agent's general rationalizations table inline
in `.claude/agents/generator.md`.

| Rationalization | Reality |
|---|---|
| "private method got complex, just test it directly" | Tests then couple to implementation; refactor breaks tests. Extract to a new module with public interface; test that. |
| "mock this collaborator to isolate" | Isolation = test the imagined collaboration, not the real one. Use real object; mock only process boundaries. |
| "extract this helper, it's used twice in this file" | Two private uses earn a private method, not a new module. Extraction passes the deletion test only when ≥ 2 *distinct* callers across modules concentrate complexity (foundation.md §5.5 deletion test). |
| "add an optional parameter for flexibility" | Public surface widens; foundation.md §5 `config-leak` flag. Overload, separate method, or refuse. |
| "external exception just propagates upward" | Foreign vocabulary leaks; foundation.md §5 `exception-leak` flag. Catch + re-raise as domain exception with `cause=` chain (Bloch Effective Java Item 73). |

## §7 What's NOT here

- Generator's general ambiguity-handling discipline (strategic-decide
  refine-vs-pivot, when to call `propose_contract_amendment`,
  anti-oscillation, vertical-slice self-check) → inline in
  `.claude/agents/generator.md`.
- Stack-specific test runner / barrel / module conventions → active
  stack skill's `references/`.
- AC interpretation (what to implement) → spec's
  `acceptance_criteria` and stack skill.
- Evaluator's review checklist → `evaluator-slice.md`.
