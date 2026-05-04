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

## §5 Module spec inline format

When writing a feature's `business_rules` for a module, use the
inline format below (free-text inside `business_rules` — schema is
not extended):

```
**Module: <name>**
- Hides decision: <one sentence>
- Bounded context: <ctx-name from CONTEXT.md, or open_question if unnamed>
- Public interface (signatures only): <list>
- Boundary type: internal | acl-needed | framework-conformant
- Applicability: <one of foundation.md §3 rows>
- Strategy seam: none | <interface-name> (reason: <named second impl>)
- Red flags considered, none fired: yes | no (if no, list which fired and reference open_question id)
```

The "red flags considered, none fired" line forces the planner to
walk the foundation.md §5 list once per module — the equivalent of
the evaluator's "Flags considered but not fired" log (see
`evaluator-slice.md`).

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
