# Deep Module Handbook — Planner Slice

How the planner applies deep-module principles when designing module
boundaries in `specs/_batch/feature-list.json`.

Read `references/foundation.md` first for shared definitions, scope,
red flags, and DDD calibration.

## §1 When the planner consults this slice

- Every time a feature decomposition introduces or significantly
  modifies a module
- Before writing a module's `business_rules` entry in
  `feature-list.json`
- Before deciding whether a design choice warrants an ADR (this slice
  defines the deep-module-specific ADR trigger)
- During self-verify when interpreting violations from `plan_lint.py`
  that touch module boundary hints

## §2 Design-time decision flow

For each module the planner is about to design:

```
Q1. Bounded-context check
    ├─ Which BC does this module belong to?
    ├─ Does it cross BC boundaries?
    │   ├─ Yes → plan an ACL; this triggers an ADR (see §4)
    │   └─ No → continue
    └─ Is the BC named in CONTEXT.md?
        ├─ No → open_question with resolution_kind: glossary
                (do not invent terms)
        └─ Yes → continue

Q2. Applicability classification (per foundation.md §3)
    ├─ Business logic / cross-system integration → apply deep module
    ├─ DTO / framework-shaped / hot path / one-shot → keep shallow,
    │   skip remaining steps
    └─ Grey zone → open_question with resolution_kind: feature_local

Q3. Information-hiding check
    ├─ Write one sentence: "this module hides <X>"
    │   ├─ Cannot write → boundary is wrong, return to Q1
    │   └─ Wrote → continue
    └─ X is a design decision likely to change?
        ├─ Yes → boundary justified
        └─ No (X is just "implementation detail") → re-examine

Q4. Public surface qualitative check
    ├─ Could a maintainer reconstruct the implementation from public
    │   signatures alone?
    │   ├─ Yes → 🚩 shallow signal (see foundation.md §1
    │   │       "Could a maintainer reconstruct...")
    │   └─ No → continue
    ├─ Does any signature need a sentence "first call X, then call Y"?
    │   ├─ Yes → 🚩 temporal-coupling flag
    │   └─ No → continue
    └─ Are exception types from the module's vocabulary, or do they
       leak lower-layer types?
        ├─ Leak → 🚩 exception-leak flag
        └─ Vocabulary aligned → continue

Q5. Strategy seam check
    ├─ Is a Strategy / DI seam being introduced?
    │   ├─ Yes → must name a real or imminent second implementation
    │   │   ├─ Cannot name → drop the seam (YAGNI)
    │   │   └─ Named → record in ADR or open_question
    │   └─ No → continue

Q6. Deletion test (foundation.md §5.5)
    ├─ If this module were removed, would complexity concentrate in
    │   ≥ 2 distinct callers?
    │   ├─ No → 🚩 fake-deep-pass-through flag
    │   └─ Yes → module earns existence, design accepted
```

Any 🚩 flag fires → translate to `open_question` per §3.

## §3 Red flag → open_question pattern

The planner does not auto-FAIL on a red flag. It writes an
`open_question` with a recommendation.

Format inside `feature.open_questions[]`:

```json
{
  "id": "F<n>-Q<n>",
  "kind": "feature_local",
  "question": "🚩 <flag-id>: <one-line description of what fired and where>",
  "recommendation": "<2-3 sentences: which option from the flag's 'If fires, recommend to user' list, plus rationale grounded in this feature's context>",
  "resolution": "<recommended answer + brief rationale; user reviews at /plan Phase 2 walk>"
}
```

The Phase 2 per-Q walk lets the user approve / edit / escalate; the
planner provides the starting point.

## §4 ADR trigger — deep-module-specific

The only deep-module-specific condition that triggers an ADR is
**establishing or modifying a bounded-context boundary**. Other
module decisions (pass-through removal, interface widening, etc.)
go to `open_questions` instead.

| Situation | ADR required? | Why |
|---|---|---|
| New bounded context introduced | **Yes** | Hard to reverse, surprising, real trade-off (BC choice constrains every later feature) |
| Existing bounded context boundary moved | **Yes** | Same |
| ACL planned across an existing BC boundary | No, unless the ACL itself encodes a non-obvious decision | ACL is a tactic that follows the BC decision |
| Module split / merge inside one BC | No | `open_question` with `resolution_kind: feature_local` |
| Strategy seam adopted | No | `open_question`; the second implementation is the trade-off |
| Deep vs shallow choice for a module | No | `open_question` if grey-zone; otherwise §3 applicability table answers it |

Apply the standard three-test gate
(`planner-handbook/references/adr-lifecycle.md`) on top of the BC
trigger. All four tests must pass to write an ADR.

## §5 Module spec — array, one entry per module in the slice

Every feature carries `spec.module_design` as an **array of per-module
entries**, validated by `.claude/schemas/feature-list.schema.json`
(`$defs/module_design` → array of `$defs/module_entry`). A vertical
slice typically contains multiple modules (UI page + API route + lib
utility); each gets its own deep-module evaluation, since they
genuinely have different applicability classes (a lib is
business-logic; a Next.js page is framework-shaped) and lying about
that to fit a single block is what motivated this array shape.

The union of `module_design[*].module_path` is the feature's write
boundary — the previous singleton `feature.module_path` field is
gone. Generator's "touch only" rule reads the union (see
generator.md principle 3).

```json
"module_design": [
  {
    "name": "<short label, e.g. 'lib/cursor.ts' or 'GET /api/monitor/failed'>",
    "module_path": "<file or dir, e.g. 'orchestration_web/lib/cursor.ts'>",
    "hides_decision": "<sentence ≥30 chars naming what THIS module conceals>",
    "bounded_context": "<ctx-name from CONTEXT.md>",
    "public_interface": ["<this module's signature 1>", "<signature 2>", ...],
    "boundary_type": "internal | acl-needed | framework-conformant",
    "applicability": "business-logic | cross-system-integration | dto | framework-shaped | hot-path | one-shot",
    "strategy_seam": { "present": false }
                   | { "present": true, "interface_name": "...", "second_impl": "..." },
    "design_notes": "<OPTIONAL prose — name red flags from foundation.md §5 only when one fired or came close in THIS module>"
  },
  { "name": "...", ... }
]
```

Granularity rule of thumb: split into one entry whenever two modules
would honestly take different `applicability` or different
`hides_decision`. A page + its API route + a shared lib is typically
3 entries. Two near-identical sibling routes that share a lib is
typically 1 entry for the lib + 1 for the routes (collapsed when
their interface and applicability are identical).

### Why the schema is structural, not a checklist

An earlier draft of this slice required `red_flags_considered` as a
6-key object — one boolean + rationale per flag from foundation.md
§5. We rolled it back. Three converging research signals (canon,
industry, internal critique) all said the same thing:

- **The canon is principle-based.** Parnas 1972 polemicizes against
  mechanical decomposition. Ousterhout's red flags are explicitly
  "signals to investigate, not pass/fail gates." Bloch on exception
  translation: "should not be overused." Seemann calls temporal
  coupling a *smell* (Fowler tradition: investigative cue, not
  defect). No primary author endorses binary scoring.
- **Industry doesn't enforce it via schema.** Microsoft Research's
  code-review corpus shows reviewers under structured prompts drift
  to cheap-to-verify fields (style/format) and away from
  architecture. Google eng-practices is principle-based. Pocock's
  `improve-codebase-architecture` skill uses vocabulary +
  heuristics, not required JSON keys. SonarQube has no
  shallow-module rule because module depth is semantically
  invisible to static analysis.
- **The 6-flag walk would have been theatre.** Six flags with wildly
  different mechanical-detectability (wrapper-around-stdlib is
  greppable; fake-deep-pass-through requires a counterfactual) would
  bake false symmetry into the artefact. Both planner and evaluator
  are LLMs; boilerplate-in / boilerplate-out is the dominant failure
  mode. A 10-char `minLength` filters nothing. The applicability
  opt-out is itself a loophole that recreates on-demand triggering
  with extra ceremony.

What schema CAN do reliably is force a one-sentence act of thinking
on the fields where the cognition is mechanical: a 30-char
`hides_decision`, an enum `applicability`, an enum `boundary_type`,
a structural `strategy_seam` (with named second impl). Those are
worth schema enforcement. Per-flag judgement isn't.

### Rules the planner respects (per entry)

- **`hides_decision` ≥ 30 chars.** Schema rejects shorter. Names a
  *decision likely to change* in THIS module — not "this module
  handles X." Evaluator falsifies the sentence within 1 minute
  (cross-check in evaluator-slice §1); a sentence the evaluator can
  falsify means the boundary is wrong.
- **Strategy seam YAGNI fence.** `present:true` requires both
  `interface_name` and `second_impl`. "In case we later need X" is
  not a valid `second_impl` — the second impl must be real or
  imminent. Planner self-verify rejects bare hypotheticals.
- **Applicability is audited per entry.** Labelling a lib `dto` or
  a business-logic module `framework-shaped` to escape design
  discussion is detected by evaluator's `applicability_honest`
  cross-check (evaluator-slice §1) — checked once per entry, so you
  cannot hide a deep lib inside a feature whose other entries are
  legitimately framework-shaped.
- **`public_interface[]` is per-module.** Don't catalogue the whole
  vertical slice into one entry. If `lib/cursor.ts` and
  `GET /api/monitor/failed` are both in the slice, they are TWO
  entries with TWO disjoint `public_interface[]` lists.
- **`module_path` is per-module.** A specific file or directory; the
  union across all entries defines the generator's write boundary
  (replaces the previous singleton `feature.module_path`).
- **`design_notes` is genuinely optional.** Use it when a flag from
  foundation.md §5 fired or came close in THIS module, when the
  deletion test (foundation.md §5.5) was non-trivial, or when an
  architectural tradeoff bears explanation. If none of those apply,
  omit. Empty prose is better than ceremonial prose.

When a red flag DOES fire and the planner cannot avoid it without
violating an AC, route to `open_questions[]` per §3 above — flagged
designs are not auto-FAIL, they are user-visible at /plan Phase 2.

## §6 Common Rationalizations (deep-module specific)

Supplements the planner's general rationalization table in
`planner.md`. Concerns specific to deep-module reasoning:

| Rationalization | Reality |
|---|---|
| "This helper is small enough to extract" | Extracting creates a shallow module; "small enough to extract" is the shallow trap. Keep as private method until the deletion test (§2 Q6) earns the extraction. |
| "Strategy seam in case future X" | YAGNI; no second implementation = pass-through seed. Open_question instead of ADR; promote to Strategy only when the second impl is named. |
| "DTO should encapsulate setters" | DTOs are foundation.md §3 "no" row; encapsulation makes them harder to read. Keep shallow. |
| "Cross-system integration: just call directly to save a layer" | Foreign vocabulary will leak into domain; ACL retrofit later costs more than ACL upfront. ACL is non-negotiable for cross-system. |
| "Bounded context should be split smaller for cleanliness" | Smaller BC = more ACLs = exploding translation cost. BC follows linguistic difference, not technical neatness. |
| "Add the depth_score number, just internally, as a sanity check" | No quantitative gate. The previous repo's `depth_score ≥ 5` had no rigorous source (Ousterhout gives no threshold). Use Q3 + Q4 + Q6 qualitative checks. |

## §7 What's NOT here

- General planner discipline (vertical-slice rule, three-script
  self-verify, ADR three-test gate) → `planner-handbook/`
- ADR file format and lifecycle →
  `planner-handbook/references/adr-lifecycle.md`
- Ousterhout/Parnas/Evans definitions → `foundation.md`
- Generator implementation rules → `generator-slice.md`
- Evaluator review checklist → `evaluator-slice.md`
