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

## §1 When the evaluator consults this slice

- Reviewing a module that the planner spec marked as deep
  (per `planner-slice.md` §5 inline format)
- Reviewing the boundary between two modules in different
  bounded contexts (ACL inspection)
- When the spec's `Module: <name>` block lists "red flags considered";
  evaluator must verify the listed flags actually didn't fire in the
  implementation

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

## §7 "Flags considered but not fired" log

For each module reviewed, the evaluator's output includes:

```
Module: <name>
Verdict: PASS | FAIL | DEFERRED
Flags fired:
  - 🚩 <flag-id> (recommendation: <one-line>)
Flags considered but not fired:
  - 🚩 <flag-id>
  - 🚩 <flag-id>
  - ...
Compliance: matches planner spec | drift: <diff>
```

The "Flags considered but not fired" line is the rot-detection
substrate. /finalize aggregates these per batch into a flag-fire
log (location TBD in T9); flags that never fire across many batches
become retirement candidates per foundation.md §5 retirement criteria.

This log is not yet automated — currently human-curated. T9
/finalize work decides whether to automate.

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
