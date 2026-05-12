# Deep Module Handbook — Evaluator Slice

How the evaluator applies deep-module principles when reviewing a
module's interface, boundaries, performance, and security against
the deep-module methodology.

Read `references/foundation.md` first for shared definitions, scope,
red flags, and DDD calibration.

**Scope reminder:** this slice covers only the deep-module-specific
evaluator behaviors. The evaluator's general behavior (QA
independence from generator's reasoning, AC-as-contract,
eval_anchors discipline) lives inline in `.claude/agents/evaluator.md`.

## §1 When the evaluator consults this slice — two /loop phases

The evaluator engages this slice in **two distinct /loop phases**,
both writing into `contracts.jsonl` (no separate eval JSON file in
v3.8):

1. **NEGOTIATE phase** — reviewing the generator's proposed sprint
   contract draft (`phase: agreed` candidate) for deep-module sanity
   BEFORE implementation begins. See §1.5.
2. **VERIFY phase** — auditing the committed sprint against
   verification_plan + transcript-as-evidence. See §1.6.

In v3.8 there is no `spec.module_design` schema field — module
identity and depth commitments live in the sprint contract's
`done_looks_like[]` and `verification_plan[]` narrative (filled in
by generator at NEGOTIATE per `generator-slice.md` §1.5). The
evaluator audits those narrative items against this handbook's
vocabulary at both phases.

The five-axis material in §2-§5 below is **vocabulary**, not a
mandatory walk — cite an axis or red-flag name when it actually
informs the verdict; do not enumerate all five for every module.

## §1.5 NEGOTIATE phase — reviewing a contract draft for deep-module sanity

Before signing off on the proposed contract (allowing it to
transition to `phase: agreed`), spot-check the generator's
module-level commitments in `done_looks_like[]`. The generator
follows a canonical per-module item shape (see
`generator-slice.md` §1.5 "Per-module done_looks_like item shape")
so you can parse each module's commitments mechanically.

For each module item, walk this checklist:

- **C1 falsifiability** — read the module's `hides_decision`
  sentence. Can you falsify it in <1 minute from your understanding
  of the sprint scope? If yes, the sentence is ceremony — push
  back. Sentences like "owns user data" / "handles config" are
  unfalsifiable; sentences like "owns how raw JSON bytes become
  a ParsedConfig tree plus a normalized ParseError" are
  falsifiable (you can imagine code that doesn't do that).
- **C4 entry-point budget** — does the proposed public surface
  enumerate ≤ 1-3 entry points per module, or is the generator
  committing to a bag-of-getters? If the latter, push back. Unix-
  style genuine multi-use (5 calls like `open/read/write/close/lseek`)
  is acceptable but should be self-justified.
- **C5 two-adapter rule** — if a Strategy seam is proposed, are
  ≥2 actual implementations named (or 1 + 1 imminent with date)?
  If only one, push back: collapse the seam. Generic phrases like
  "in case we later need X" are insufficient.
- **§3 applicability honesty** — is the declared applicability
  (business-logic / framework-shaped / etc.) consistent with what
  the sprint actually builds? A "framework-shaped" label on what
  is actually a state-machine library is dishonest at NEGOTIATE
  time and harder to fix at VERIFY. Opt-out modules
  (`dto` / `framework-shaped` / `hot-path` / `one-shot`) MUST still
  appear as their own `done_looks_like[]` item so you can spot a
  dishonest opt-out.
- **§5 red flags visible from the contract alone** — if e.g. the
  done_looks_like commits to "returns sqlalchemy.Row" (exception-
  leak / leaky-abstraction in advance), flag it now; the boundary
  was set wrong at proposal time.
- **C3 deletion test (only if generator volunteered it)** — if
  the generator pre-committed C3 reasoning for a module (naming
  ≥2 callers that would regrow complexity), spot-check those
  callers are **real and distinct**. Two failure modes to watch:
  - **Circular**: "tests" as the second caller is invalid — tests
    are not callers in the deletion-test sense; they ride on the
    real caller graph. Push back.
  - **Hypothetical**: "future programmatic consumer" / "downstream
    epic might use this" without a hard date fails the same test
    by the C5 two-adapter rule (foundation.md §4 cross-cutting
    tension #3 — one named-but-not-real implementation is YAGNI).
    The second caller must exist now, or be imminent with a
    concrete date. Push back.

  If the generator did NOT volunteer C3, that's acceptable at
  NEGOTIATE; you'll check it at VERIFY against the actual git diff.
- **C7 interface-as-test-surface sensor (recommended)** — does
  `verification_plan[]` contain a step of kind `matrix`/`test`
  with a check like `interface-stability:rename-internal-helper-…`?
  Its presence is positive evidence that the generator commits to
  tests surviving internal refactor. Its absence is a soft push-
  back item for non-opt-out modules; the evaluator can request it
  be added or accept its absence with a recorded rationale.

### Where to write the review feedback

This slice is content-shape only — it does NOT prescribe the file
path or storage location for NEGOTIATE feedback. The workflow harness
(`harness-loop` skill + your invoking command) decides whether to
write the feedback to `specs/_epic/_pending/S{NN}-review-v{N}.yaml`,
inline as another `contracts.jsonl` entry with `phase: review`, or
to a caller-supplied path. Use the path your invoking context tells
you to use; if silent, default to `_pending/S{NN}-review-v{N}.md`.

### NEGOTIATE feedback severity vocabulary

NEGOTIATE is a review-and-revise loop, not a verdict. Use one of
three positions in your review feedback:

- **APPROVE** — no concerns; the contract is ready for
  `phase: agreed`. Generator proceeds to IMPLEMENT.
- **REQUEST_CHANGES** — specific items to revise before agreeing.
  List each item with a foundation.md citation (PASS criterion
  number, red flag name, or §3 applicability row). Generator
  either accepts the revision and amends OR pushes back with
  rationale; loop continues until APPROVE or REJECT.
- **REJECT** — the contract is fundamentally misshapen (wrong
  bounded context, fake-deep-decorator-stack across multiple
  modules, etc.) and a small amendment won't fix it. Recommend
  the generator redraft from scratch with specific guidance on
  what's structurally wrong. Use sparingly — most issues are
  REQUEST_CHANGES.

The evaluator does not unilaterally `phase: agreed` the contract;
it surfaces its position and the generator either revises (new
draft, same round if minor; new round if structural) or
counter-proposes. The contract reaches `phase: agreed` only when
the evaluator's position is APPROVE.

## §1.6 VERIFY phase — three cross-checks per module + design_review

### The three cross-checks (per module touched by the sprint)

Run these once per module the sprint touched (read out of the
agreed contract's `done_looks_like[]` narrative + the actual
git diff).

1. **Hides-decision falsifiability.** Read the module's
   `hides_decision` sentence from the agreed contract's
   `done_looks_like[]`. Try to falsify it within 1 minute by
   reading the impl in the git diff: is the sentence non-trivially
   true? A plausible-sounding but unfalsifiable sentence (e.g.
   "this module handles user data") is a discipline failure — the
   generator wrote ceremony at NEGOTIATE, not a design claim, and
   you missed it. Emit `hides_decision_falsifiable_within_one_minute:
   true → FAIL`; `false → PASS`.
2. **Applicability honesty.** Verify the module's actual nature
   matches the applicability declared at NEGOTIATE
   (`business-logic` / `cross-system-integration` / `dto` /
   `framework-shaped` / `hot-path` / `one-shot`). The opt-out rows
   exist for genuine cases; a lib labelled `dto` that contains
   genuine business rules is a NEGOTIATE-time lie that this VERIFY
   step catches. Emit `applicability_honest: false → FAIL`.
3. **Boundary-type honesty.** If the contract committed to
   `boundary_type: acl-needed`, an ACL must exist in the impl at
   the named boundary. If `internal`, no cross-BC translation
   should be necessary. Emit `boundary_type_honest` per module.

### The narrative review (per module)

Write a paragraph (`design_review` field — see §7 for the contract-
entry shape) reasoning about THIS module's depth, leak, and any red
flags that fire. Two vocabularies available, both from foundation.md:

- **PASS vocabulary** — foundation.md §3.5 success criteria
  C1-C8 (hides-decision named, 3-question self-test, deletion test,
  entry-point budget, two-adapter rule, broad-interface, interface-
  is-test-surface, size sanity). Cite the criterion # when the
  module clearly satisfies it; this is positive evidence for PASS.
- **FAIL vocabulary** — foundation.md §5 red flags
  (fake-deep-pass-through, fake-deep-decorator-stack, config-leak,
  exception-leak, temporal-coupling, wrapper-around-stdlib). Cite
  the flag name when it fired or came close.

Use whichever is honest evidence for this specific module — often
one is silent (e.g., a clearly-deep cursor-signing lib gets two
PASS criteria cited, no red-flag mentions). Do not enumerate all
criteria or all flags; equally-confident-looking citations for
items you actually analysed and items you pattern-matched on
produce false symmetry.

### Historical note

Earlier drafts (v1 era) had a per-flag JSON output and a feature-
singleton shape; both were rolled back as bureaucratic theatre.
v3.8 collapses module-level cognition into contract.jsonl narrative
+ a per-module-array under the evaluator's `findings[]` field
(see §7). The current shape lets honest cognition land per module
without forcing structural symmetry where none exists.

## §2 Five-axis review checklist

For each module in scope, evaluator walks all five axes. For each
axis, the evaluator emits one of three signals:

- **PASS** — axis satisfied
- **FAIL** — axis violated; emit FAIL verdict on the feature
- **DEFERRED** — evaluator cannot decide with confidence; emit
  DEFERRED verdict on the feature; surface as open_question for
  /finalize user review

DEFERRED is a third valid evaluator signal alongside PASS and FAIL;
in v3.8 the evaluator surfaces DEFERRED items as findings the
operator decides at /finalize time. The evaluator does not
unilaterally block downstream sprints — operator monitors and may
abort the loop based on the DEFERRED count.

| Axis | Check | PASS signal (foundation §3.5) | FAIL signal | DEFERRED signal |
|---|---|---|---|---|
| **A. Depth** | Could a maintainer reconstruct the implementation from public signatures alone? | C1 + C2 pass + C8 size band reasonable | Yes — module is shallow | Cannot tell without reading caller code |
| **B. Leak** | List implementation facts the caller must know to use the module correctly | C6 broad-interface complete (signature + invariants + ordering + error modes documented) | Any leak fact found that is not documented as accepted in the contract | Contract is silent on whether a borderline fact is intentional |
| **C. Pass-through** | For each public method, does the deletion test fire (foundation.md §5.5)? | C3 deletion test passes (≥2 callers regrow complexity if removed) | Any pass-through that is not an ACL method | Method might be ACL but ACL not declared at NEGOTIATE |
| **D. Boundary translation** | At each module boundary: are external exceptions caught and re-raised as domain exceptions with cause chained? At each BC boundary: does an ACL exist? | exception-leak flag silent; ACL present where BC crossed | External exception type leaks through public surface OR ACL missing where BC is crossed | Contract does not specify exception strategy at this boundary |
| **E. Mock budget** | In each test, does the mock setup encode the module's internal collaboration graph (Mockist drift)? | **C7 interface = test surface** passes — tests survive internal helper rename | Test mocks beyond what's needed for process boundaries; test would still pass with real internal objects | Mock count is borderline; cannot tell without trying |

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

The performance axis applies only when the agreed sprint contract
marks the module as performance-sensitive (e.g., applicability
`hot-path` in NEGOTIATE narrative, or referenced by a perf-related
ADR or spec.md `## Cross-cutting constraints` entry). Otherwise
these are observations, not FAIL signals.

## §4 Security review angle

Information hiding and security are aligned, but specific checks:

- **Secret leakage in signature**: public method requires the caller
  to pass a secret in the signature (e.g., `fetch(api_key=...)`).
  The secret then lives in every callsite. FAIL.
- **Insecure default**: interface accepts user input but does not
  default-escape (e.g., `render(html)` defaults to trusting the
  input). FAIL.
- **Sanitization at the wrong layer**: the agreed contract says
  input must be sanitized at the module boundary; the module pushes
  sanitization to caller. FAIL.
- **Sensitive info in chained exception**: per Bloch, exception
  translation chains the original — but if the original message
  contains schema names, table names, internal IDs, the chain
  leaks internals. FAIL on the wrap step, not the catch.

## §5 Verdict path

```
Walk axes A-E per module. For each:
  ├─ PASS → continue
  ├─ FAIL → record finding in this module's design_review;
  │         contributes to sprint-level FAIL signal
  └─ DEFERRED → record finding; contributes to DEFERRED signal

After all axes per module:
  ├─ Any FAIL? → module contributes FAIL to sprint verdict
  ├─ Any DEFERRED (no FAIL)? → module contributes DEFERRED;
  │   note in design_review for operator review at /finalize
  └─ All PASS → module contributes PASS

Sprint-level rollup (per evaluator-handbook):
  - All modules PASS → consider this slice toward sprint PASS
  - Any module FAIL → contributes FAIL toward sprint verdict;
    final verdict combines with other criterion_mapping signals
  - DEFERRED modules surface as DEFERRED in the sprint's overall
    rollup; operator decides whether to keep running /loop or stop
```

## §6 Compliance check (impl vs agreed contract)

Beyond the five axes, the evaluator verifies that the implementation
adheres to the agreed sprint contract's `done_looks_like[]`:

- Public interface signatures match what the contract committed to
  at NEGOTIATE
- Boundary type (internal / acl-needed / framework-conformant)
  matches what NEGOTIATE specified
- Module count + identity matches the contract — generator did not
  silently add or rename modules outside the agreed scope

If the implementation drifted from a previously-agreed contract
item without an accepted `propose_contract_amendment` → FAIL (the
contract was the agreement; the implementation cannot unilaterally
move it). Evaluator references the original `done_looks_like[]`
item verbatim in the finding.

## §7 Output shape — `module_design_verification` array inside the contract.jsonl evaluator entry

In v3.8 the evaluator writes verdicts into `contracts.jsonl` as
append-only entries (one per round, `phase: completed` when the
sprint is verified). Within that entry's `findings[]` array, include
a `module_design_verification` field shaped as an **array** with one
entry per module the sprint touched (read from the agreed
contract's `done_looks_like[]` narrative + the actual git diff).

Empty / missing array when the sprint did touch modules is a
doctrine violation in the same severity class as silent-skip L5 —
it means you didn't engage the handbook. For sprints that touched
zero modules (rare; pure config / docs / data changes), explicitly
emit `"module_design_verification": []` with a one-line rationale
in the surrounding `design_review` narrative ("sprint did not
touch any module-shaped artefact").

Each per-module entry is deliberately small: 3 booleans + 1
narrative + 1 list. Larger structures (per-flag JSON, per-axis JSON)
were rolled back as bureaucratic theatre — see § Historical note.

```json
"module_design_verification": [
  {
    "module_name": "lib/cursor.ts",
    "hides_decision_falsifiable_within_one_minute": false,
    "applicability_honest": true,
    "boundary_type_honest": true,
    "design_review": "Genuinely deep: signCursor / verifyCursor surface hides HMAC keying, scope-binding (s='failed' vs s='blocked'), and rotation index. Deletion test PASS — without this lib, every cursor consumer would re-derive HMAC inline. No red flag from foundation.md §5 fires.",
    "drift_from_contract": []
  },
  {
    "module_name": "GET /api/monitor/failed",
    "hides_decision_falsifiable_within_one_minute": false,
    "applicability_honest": true,
    "boundary_type_honest": true,
    "design_review": "Framework-shaped Next.js route handler, honestly labelled. Hides whether failed-row retrieval rides GSI 5 with stage filter or per-stage parallel query — confirmed: the implementation uses GSI 5 single-query, callers see a flat result. No leak of partition-key vocabulary into the response shape.",
    "drift_from_contract": []
  },
  {
    "module_name": "failed page",
    "hides_decision_falsifiable_within_one_minute": false,
    "applicability_honest": true,
    "boundary_type_honest": true,
    "design_review": "Server-component composer; framework-shaped applicability is honest. No business logic embedded; data fetching delegated to the API route, rendering delegated to <FailedTable>. Pass-through smell does not fire because the page composes 4 distinct concerns (filter parsing, fetch, table, retry-confirm modal) — earns its existence per foundation.md §5.5 deletion test.",
    "drift_from_contract": []
  }
]
```

Field meanings (per entry):

- **`module_name`** — short label identifying the module
  (file path, route, library name). Stable across rounds so
  /finalize aggregation can group findings by module identity.
- **`hides_decision_falsifiable_within_one_minute`** — boolean.
  The §1.6 cross-check for THIS module. `true` = you DID falsify
  the generator's NEGOTIATE-time `hides_decision` sentence by
  reading the impl (bunk claim); contributes FAIL. `false` =
  sentence survived falsification; contributes PASS.
- **`applicability_honest`** — boolean. Did THIS module's actual
  nature match the applicability declared at NEGOTIATE? `false` → FAIL.
- **`boundary_type_honest`** — boolean. ACL exists where the
  contract committed to `boundary_type: acl-needed`; no cross-BC
  translation smuggled into `internal`. `false` → FAIL.
- **`design_review`** — narrative paragraph for THIS module. Cite
  PASS criteria C1-C8 (foundation §3.5) when satisfied; cite red
  flag names from foundation §5 when fired. Do NOT enumerate all
  criteria or all flags per entry — false symmetry.
- **`drift_from_contract`** — list of one-line strings naming each
  `done_looks_like[i]` item from the agreed contract this module's
  impl violated. Empty list is fine.

Aggregation: ANY entry with any of the 3 booleans signalling FAIL
(or `hides_decision_falsifiable_within_one_minute: true`) →
sprint verdict contributes FAIL with the failing entries'
rationales surfaced in their `drift_from_contract[]` and
`design_review`. All entries clean + all drift empty → this slice
contributes PASS to the sprint verdict (other criterion_mapping
checks still apply independently).

### Rot detection

Rot detection happens at /finalize time: it greps `design_review`
strings across the epic's `contracts.jsonl` evaluator entries,
counts how often each foundation.md §5 flag name appears in which
`module_name` contexts, and flags candidates for retirement per
the retirement
criteria there. Less precise than the per-flag boolean approach,
but the precision was illusory anyway (boilerplate booleans don't
measure rot).

## §8 Common Rationalizations (deep-module specific)

| Rationalization | Reality |
|---|---|
| "Tests pass, that's enough — emit PASS" | Mockist tests can pass on a shallow / leaky module. Walk all five axes regardless of test outcome. |
| "depth_ratio is just a heuristic, don't fail on it" | There is no `depth_ratio` number — the depth axis itself is qualitative (foundation.md §1 check + §3.5 C1-C7). Ousterhout DOES endorse class size 200-2000 LOC as a sanity proxy (§3.5 C8) — that is "look here first", not a verdict. FAIL only when a qualitative check clearly fires (a red flag fires, or a §3.5 criterion clearly fails); a 30-LOC module passing C1-C7 is not a FAIL just because it's outside the LOC band. |
| "Caller convenience is more important than interface narrowness" | Caller convenience is built on every maintainer's cost. Foundation.md §1 cognitive-load check: how many distinct concepts must the caller hold to call this correctly? |
| "Pass-through earns its keep — it makes the structure clearer" | Then it should pass the deletion test (foundation.md §5.5): removing it concentrates complexity in ≥ 2 callers. If not, FAIL. |
| "External exception is OK because the caller can read the message" | Foreign vocabulary leaked. Wrap or FAIL. |
| "Mock count is high but tests are clean" | Clean tests on tightly-coupled implementation = false safety net. Mockist drift; FAIL or DEFERRED based on confidence. |

## §9 What's NOT here

- General evaluator discipline (review_contract for NEGOTIATE,
  transcript-as-evidence, criterion_mapping rollup, threshold check)
  → inline in `.claude/agents/evaluator.md` + `evaluator-handbook`
  skill.
- Stack-specific test runner / lint commands → active stack skill's
  `## Commands` table.
- Verification levels (L1 / L2 / L5) → spec's evaluation criteria +
  per-sprint contract `verification_plan[]`.
- Generator implementation rules → `generator-slice.md`.
- ADR triggers (planner concern) → `adr-lifecycle` skill loaded by
  planner.md.
