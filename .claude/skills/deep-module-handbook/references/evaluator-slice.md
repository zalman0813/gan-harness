# Deep Module Handbook — Evaluator Slice

How the evaluator applies deep-module principles when reviewing a
module's interface, boundaries, performance, and security against
the deep-module methodology.

Read `references/foundation.md` first for shared definitions, scope,
red flags, and DDD calibration.

**Scope reminder:** this slice covers only the deep-module-specific
evaluator behaviors. The evaluator's general behavior (QA
independence from generator's reasoning, AC-as-contract,
eval_anchors discipline) lives in the future `evaluator-handbook`
skill (T8).

## §1 When the evaluator consults this slice — every grading round

`spec.module_design` is a required schema field (see
`planner-slice.md` §5 and `.claude/schemas/feature-list.schema.json`
`$defs/module_design`). Every feature carries one. Therefore:

**The evaluator engages this slice every round, for every feature.**
The previous on-demand behavior was a doctrine loophole — planners
under-declared, evaluators didn't trigger, deep-module review never
happened. Schema closes that loop, but deliberately by mandating
*structural anchors*, not by enumerating per-flag booleans (see
planner-slice §5 "Why the schema is structural, not a checklist").

What the evaluator MUST do: write a `module_design_review`
narrative paragraph (see §7 for the eval JSON shape) plus three
falsifiability cross-checks. The five-axis material in §2-§5 below
is **vocabulary**, not a mandatory walk — cite an axis or red-flag
name when it actually informs the verdict; do not enumerate all
five for every feature.

### The three cross-checks

1. **Hides-decision falsifiability.** Read the planner's
   `hides_decision` sentence. Try to falsify it within 1 minute by
   reading the impl: is the sentence non-trivially true? A
   plausible-sounding but unfalsifiable sentence (e.g. "this
   module handles user data") is a discipline failure — the planner
   wrote ceremony, not a design claim. Emit
   `hides_decision_falsifiable_within_one_minute: true → FAIL` (the
   sentence was bunk); `false → PASS` (the claim survives a
   1-minute attempt to disprove).
2. **Applicability honesty.** If `applicability` is one of the
   opt-out rows (`dto`, `framework-shaped`, `hot-path`,
   `one-shot`), verify the module's actual nature matches. A module
   labelled `dto` that contains genuine business rules is a planner
   lie. Emit `applicability_honest: false → FAIL`. Genuine DTOs and
   true Next.js page renders pass.
3. **Boundary-type honesty.** If `boundary_type: acl-needed`, an
   ACL must exist in the impl at the named boundary. If
   `internal`, no cross-BC translation should be necessary. Emit
   `boundary_type_honest`.

### The narrative review

Write a paragraph (`design_review` in eval JSON §7) reasoning
about depth, leak, and any red flags that fire. Cite flag names
from foundation.md §5 (fake-deep-pass-through,
fake-deep-decorator-stack, config-leak, exception-leak,
temporal-coupling, wrapper-around-stdlib) only when they fired or
came close — do not enumerate all six; that produces equally
confident-looking evidence for flags you actually analysed and
flags you pattern-matched on (false symmetry).

### What used to be here

An earlier draft required a per-flag JSON output (`red_flags{}`
with 6 keys, each `{planner_declared, evaluator_finds, verdict,
evidence}`). It was rolled back — research convergence (canon,
industry, hostile critique) judged it bureaucratic theatre.
Boilerplate-in / boilerplate-out is the dominant failure mode for
two LLMs reading a structured checklist. The narrative `design_review`
puts the cognition where it actually lives: prose informed by
named vocabulary.

## §2 Five-axis review checklist

For each module in scope, evaluator walks all five axes. For each
axis, the evaluator emits one of three signals:

- **PASS** — axis satisfied
- **FAIL** — axis violated; emit FAIL verdict on the feature
- **DEFERRED** — evaluator cannot decide with confidence; emit
  DEFERRED verdict on the feature; surface as open_question for
  /finalize user review

DEFERRED is a third valid verdict alongside PASS and FAIL;
downstream features in the DAG that depend on a DEFERRED feature
are skipped (`status: blocked-by-ancestor`).

| Axis | Check | FAIL signal | DEFERRED signal |
|---|---|---|---|
| **A. Depth** | Could a maintainer reconstruct the implementation from public signatures alone? | Yes — module is shallow | Cannot tell without reading caller code |
| **B. Leak** | List implementation facts the caller must know to use the module correctly | Any leak fact found that is not documented as accepted in the spec | Spec is silent on whether a borderline fact is intentional |
| **C. Pass-through** | For each public method, does the deletion test fire (foundation.md §5.5)? | Any pass-through that is not an ACL method | Method might be ACL but ACL not declared in planner spec |
| **D. Boundary translation** | At each module boundary: are external exceptions caught and re-raised as domain exceptions with cause chained? At each BC boundary: does an ACL exist? | External exception type leaks through public surface OR ACL missing where BC is crossed | Spec does not specify exception strategy at this boundary |
| **E. Mock budget** | In each test, does the mock setup encode the module's internal collaboration graph (Mockist drift)? | Test mocks beyond what's needed for process boundaries; test would still pass with real internal objects | Mock count is borderline; cannot tell without trying |

## §3 Performance review angle

Deep-module hides implementation, but the *interface shape* can
force performance pathologies even without seeing the body:

- **Forced N+1**: interface offers `get_one(id)` but no
  `get_many(ids)` variant — callers must loop. FAIL if the spec
  marked the module as a hot-path consumer.
- **Hidden synchronization point**: interface offers `save()`
  without documenting whether it flushes synchronously or only
  enqueues. Caller cannot reason about durability or latency. FAIL.
- **No cache invalidation hook**: interface returns cacheable values
  but offers no `invalidate(key)` — caller cannot recover from
  staleness. FAIL if cache is in scope.
- **Eager-load-only**: interface returns full collections instead
  of iterators, with no opt-in for streaming. FAIL if data shape
  can be large.

The performance axis applies only when the planner's spec marks
the module as performance-sensitive (e.g., `hot_path: true` or
referenced by a perf-related ADR). Otherwise these are observations,
not FAIL signals.

## §4 Security review angle

Information hiding and security are aligned, but specific checks:

- **Secret leakage in signature**: public method requires the caller
  to pass a secret in the signature (e.g., `fetch(api_key=...)`).
  The secret then lives in every callsite. FAIL.
- **Insecure default**: interface accepts user input but does not
  default-escape (e.g., `render(html)` defaults to trusting the
  input). FAIL.
- **Sanitization at the wrong layer**: spec says input must be
  sanitized; the module pushes sanitization to caller. FAIL.
- **Sensitive info in chained exception**: per Bloch, exception
  translation chains the original — but if the original message
  contains schema names, table names, internal IDs, the chain
  leaks internals. FAIL on the wrap step, not the catch.

## §5 Verdict path

```
Walk axes A-E. For each:
  ├─ PASS → continue
  ├─ FAIL → emit feature verdict FAIL with violation list; stop
  │   (downstream still tries to run; BLOCKED-by-ancestor only on DEFERRED)
  └─ DEFERRED → record axis-specific question, continue

After all axes:
  ├─ Any FAIL? → final verdict FAIL
  ├─ Any DEFERRED (no FAIL)? → final verdict DEFERRED
  │   ├─ Append open_question per axis with raised_by: evaluator
  │   ├─ Mark feature.status: deferred
  │   └─ DAG downstream of this feature → skipped (BLOCKED-by-ancestor)
  └─ All PASS → final verdict PASS
```

## §6 Compliance check (impl vs spec)

Beyond the five axes, the evaluator verifies that the implementation
adheres to the planner's `Module: <name>` spec block:

- Public interface signatures match what the spec listed
- Boundary type (internal / acl-needed / framework-conformant)
  matches what was implemented
- The "Red flags considered, none fired" claim from the spec is
  actually true after impl

If a previously-resolved open_question from /plan Phase 2 walk was
violated by the implementation → FAIL (the contract was decided;
the implementation drifted). Evaluator references the original
open_question id in the violation list.

## §7 Eval JSON output — `module_design_verification` block

The evaluator's eval JSON (`specs/_batch/_evals/F{NN}-R{N}.json`)
MUST include a top-level `module_design_verification` field. Empty
or missing block is a doctrine violation in the same severity class
as silent-skip L5 — it means you didn't engage. The block is
deliberately small: 3 booleans + 1 narrative + 1 list. Larger
structures (per-flag JSON, per-axis JSON) were rolled back as
bureaucratic theatre — see §1 "What used to be here".

```json
"module_design_verification": {
  "hides_decision_falsifiable_within_one_minute": false,
  "applicability_honest": true,
  "boundary_type_honest": true,
  "design_review": "Module is genuinely deep at the panel layer: KpiStrip's public surface is { filter, onSelect } and hides DynamoDB partition layout, bucket math, and Server-Component fetch keying — confirmed by deletion test (removing this concentrates aggregation into 5 panel components, foundation.md §5.5 PASS). One concern under foundation.md §5 wrapper-around-stdlib: lib/dynamodb-client.ts wraps DynamoDBClient with a single retry policy and no other added semantics; close to firing but the retry encodes a project-specific backoff schedule (200ms / 1s / 5s) so it earns its existence. No fake-deep-pass-through, no exception-leak (errors caught at api/route.ts boundary and re-raised as DomainError with cause chain), no temporal-coupling (no init/start ordering on public surface).",
  "drift_from_spec": []
}
```

Field meanings:

- **`hides_decision_falsifiable_within_one_minute`** — boolean. The
  §1 cross-check. `true` means you DID falsify the planner's
  one-sentence claim within 1 minute reading the impl (the claim
  was bunk); contributes FAIL. `false` means the sentence survived
  the falsification attempt; contributes PASS.
- **`applicability_honest`** — boolean. Did the module's actual
  nature match the declared `applicability` enum? `false` → FAIL.
- **`boundary_type_honest`** — boolean. ACL exists where
  `boundary_type: acl-needed` claimed; no cross-BC translation
  smuggled into `internal`. `false` → FAIL.
- **`design_review`** — narrative paragraph. Cite flag names from
  foundation.md §5 only when relevant. Cite five-axis names from
  §2 only when relevant. Do NOT enumerate all six flags or all
  five axes — false symmetry. The cognition lives in the prose;
  schema enforces only that the prose exists.
- **`drift_from_spec`** — list of one-line strings, one per
  declared `module_design` field that the impl violated. Empty list
  is fine.

Aggregation: any of the 3 booleans `false` (or
`hides_decision_falsifiable_within_one_minute: true`) → feature
verdict FAIL with rationale in `drift_from_spec[]` and explanation
in `design_review`. All booleans clean + drift empty → this slice
contributes PASS to feature verdict (other AC + L5 checks still
apply independently).

### Rot detection

The previous design extracted "flags considered but not fired"
counts from per-flag JSON — that path is gone. Rot detection
shifts to /finalize: it greps `design_review` strings across the
batch's eval JSONs, counts how often each foundation.md §5 flag
name appears, and flags candidates for retirement per the
retirement criteria there. Less precise than the per-flag boolean
approach, but the precision was illusory anyway (boilerplate
booleans don't measure rot).

## §8 Common Rationalizations (deep-module specific)

| Rationalization | Reality |
|---|---|
| "Tests pass, that's enough — emit PASS" | Mockist tests can pass on a shallow / leaky module. Walk all five axes regardless of test outcome. |
| "depth_ratio is just a heuristic, don't fail on it" | There is no depth_ratio number. The depth axis is qualitative (foundation.md §1 check). FAIL only when the qualitative test clearly fires. |
| "Caller convenience is more important than interface narrowness" | Caller convenience is built on every maintainer's cost. Foundation.md §1 cognitive-load check: how many distinct concepts must the caller hold to call this correctly? |
| "Pass-through earns its keep — it makes the structure clearer" | Then it should pass the deletion test (foundation.md §5.5): removing it concentrates complexity in ≥ 2 callers. If not, FAIL. |
| "External exception is OK because the caller can read the message" | Foreign vocabulary leaked. Wrap or FAIL. |
| "Mock count is high but tests are clean" | Clean tests on tightly-coupled implementation = false safety net. Mockist drift; FAIL or DEFERRED based on confidence. |

## §9 What's NOT here

- General evaluator discipline (QA independence from generator's
  reasoning; AC-as-contract; eval_anchors / test_contract handling)
  → future `evaluator-handbook` skill (T8). For now embedded in
  `.claude/agents/evaluator.md` body when that agent is created.
- Stack-specific test runner / lint commands → active stack skill's
  `references/`.
- Layer 1-5 testing methodology (compile / unit / smoke etc.) →
  evaluator-handbook + spec's `test_contract`.
- Generator implementation rules → `generator-slice.md`.
- Planner ADR triggers → `planner-slice.md`.
